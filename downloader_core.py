import shutil
import zipfile
from pathlib import Path
from urllib.parse import unquote

import errno
import requests
import os


'''
Author(s): TOLoneWolf
License: in license.txt

This contains the core functions of the downloader to separate it from the input interface types CLI and/or GUI.
'''


PROGRAM_NAME = 'Curse Pack Download Manager'
PROGRAM_VERSION_NUMBER = '0.0.0.1'
PROGRAM_VERSION_BUILD = 'Alpha'

CACHE_PATH = "curse_download_cache"
MODPACK_ZIP_CACHE = CACHE_PATH + "/" + "modpacks_cache"
MOD_CACHE = CACHE_PATH + "/" + "mods_cache"


def unzip(path_to_zip_file, dst_dir=None):
    """
    :param path_to_zip_file: location of file.zip to extract from.
    :param dst_dir: string. destination location for extraction.
    """
    # If only the zip file was referenced use the directory it is in as the extract location
    if dst_dir is None:
        file_path_norm = os.path.normpath(path_to_zip_file)
        filename_and_ext = os.path.basename(file_path_norm)
        directory = os.path.dirname(file_path_norm)
        filename, extension = os.path.splitext(filename_and_ext)
        # extension = extension[1:]
        dst_dir = os.path.normpath(directory + "\\" + filename)
        # print("directory: " + directory_to_extract_to)
        # print("Filename: " + filename)
        # print("extension: " + extension)

    # https://stackoverflow.com/questions/3451111/unzipping-files-in-python
    # https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile
    # zip_ref = zipfile.ZipFile(path_to_zip_file, 'r')
    # zip_ref.extractall(directory_to_extract_to)
    # zip_ref.close()
    with zipfile.ZipFile(path_to_zip_file, "r") as zip_ref:
        zip_ref.extractall(dst_dir)


def make_zipfile(output_filename, source_dir):
    relative_root = os.path.abspath(os.path.join(source_dir, os.pardir))
    with zipfile.ZipFile(output_filename, "w", zipfile.ZIP_DEFLATED) as zipFile:
        for root, dirs, files in os.walk(source_dir):
            # add directory (needed for empty dirs)
            zipFile.write(root, os.path.relpath(root, relative_root))
            for file in files:
                filename = os.path.join(root, file)
                if os.path.isfile(filename):  # regular files only
                    arc_name = os.path.join(os.path.relpath(root, relative_root), file)
                    zipFile.write(filename, arc_name)


def copy_instance(existing_instance_dir, new_copy_dir):
    """
    :param existing_instance_dir: source directory string.
    :param new_copy_dir: destination directory string.
    """
    shutil.copytree(src=existing_instance_dir, dst=new_copy_dir, symlinks=True)


class CurseDownloader:
    def __init__(self):
        self.isDone = False
        self.sess = requests.Session()
        self.fileSize = None
        self.currentProgress = 0
        self.totalProgress = 0
        self.totalFinalVal = 0

    # FIXME This might no longer be needed thanks to the retrieve_pack_version_lists method below.
    def download_curse_pack_url(self, url=None):
        if url is None:
            raise SyntaxError('The url argument was missing or empty.')
        # https://mods.curse.com/modpacks/minecraft
        # https://mods.curse.com/modpacks/minecraft/256183-ftb-presents-skyfactory-3
        # https://www.feed-the-beast.com/projects/ftb-presents-skyfactory-3/files/latest
        latest = self.sess.get("https://minecraft.curseforge.com/projects/" + str(url) + "/files/latest")
        if latest.status_code == 200:
            print(latest.url)
        else:
            print("Error: No Mod Pack Found At Provided Project Name/ID.")
            print(latest.url)

    # view-source:https://minecraft.curseforge.com/projects/project-ozone-2-reloaded/files
    def retrieve_pack_version_lists(self, project_identifier, req_session=None):
        """
        :param project_identifier: curseforge project name or numeric id.
        :param req_session: requests.session() to use to request the url content.
        :return: List[project_id, project_name, version_list[0=type,1=id,2=title]]
        """
        if project_identifier is None:
            return None
        if type(project_identifier) is str:
            # project_identifier: get user input, remove left and right white space,
            #  replace any remaining internal spaces with dash/negative char,
            #  convert any uppercase letters to lower, and finally store it in var.
            project_identifier = project_identifier.strip().replace(" ", "-").lower()
            if project_identifier == "":
                return None

        if req_session is None:  # No session provided so create one and close it after request is finished with it.
            req_session = requests.session()
            # req_session = self.sess
        sess_response = req_session.get(
            "https://minecraft.curseforge.com/projects/" + project_identifier + "/files")
        if req_session is None:
            req_session.close()

        # print("status code: %d" % sess_response.status_code)
        if sess_response.status_code == 200:
            # print(len('https://minecraft.curseforge.com/projects/'), len('/files')) # should be: 42 6
            project_name = sess_response.url[42:-6]
            content_list = str(sess_response.content)
            content_list = content_list.split("\\r\\n")
            combine = False
            content_version_list = []
            build_version_element = []
            # bare_pack_version_list[<VersionType>, <FileID>, <VersionTitle>]
            bare_pack_version_list = []
            mod_pack_url_true = False
            for line in content_list:
                line = line.strip()
                if line == "":
                    continue  # Skips empty lines of text from the html returned.
                elif line == '<a href="/modpacks">Modpacks</a>':
                    mod_pack_url_true = True
                    continue
                elif line == '<tr class="project-file-list-item">':
                    combine = True
                elif line == "</tr>":
                    if combine:
                        build_version_element.append(line)
                        content_version_list.append(build_version_element)
                        build_version_element = []
                        combine = False
                if combine:
                    build_version_element.append(line)

            if mod_pack_url_true:
                # print(len('<a class="overflow-tip twitch-link" href="/projects//files/'))  # len: 59
                fileid_start_pos = len(project_name) + 59
                project_id = content_version_list[0][9][9:15]
                for listElement in content_version_list:
                    if listElement[2] == '<div class="release-phase tip" title="Release"></div>':
                        bare_pack_version_list.append(
                            ['R', listElement[7][fileid_start_pos:-1], listElement[9][28:-4].split(">", 1)[1]])
                    elif listElement[2] == '<div class="beta-phase tip" title="Beta"></div>':
                        bare_pack_version_list.append(
                            ['B', listElement[7][fileid_start_pos:-1], listElement[9][28:-4].split(">", 1)[1]])
                    elif listElement[2] == '<div class="alpha-phase tip" title="Alpha"></div>':
                        bare_pack_version_list.append(
                            ['A', listElement[7][fileid_start_pos:-1], listElement[9][28:-4].split(">", 1)[1]])

                return [project_id, project_name, bare_pack_version_list]
            else:
                return None

    def download_modpack_zip(self, project_name, project_id, file_id, session_id=None):
        print(project_name, file_id)
        if session_id is None:
            sess = requests.session()
            close_sess = True
        else:
            sess = session_id
            close_sess = True

        #  Check cache for file first.
        dep_cache_dir = Path(MODPACK_ZIP_CACHE + "/" + str(project_id) + "/" + str(file_id))
        if dep_cache_dir.is_dir():
            cache_file = [files for files in dep_cache_dir.iterdir()]  # Create list with files from directory.
            if len(cache_file) >= 1:  # if there is at least one file.
                cache_file = cache_file[0]  # copy name of first file to var.
                print(cache_file)
                return  # File exists skip download phase.

        # TODO: Download modpack.zip
        request_file_response = sess.get(
            "https://minecraft.curseforge.com/projects/{0}/files/{1}/download".format(
                project_name, file_id), stream=True)
        print(request_file_response.url)
        if request_file_response.status_code == 200:
            file_url = Path(request_file_response.url)
            file_name = unquote(file_url.name).split('?')[0]
            print(file_name)
            total_size = int(request_file_response.headers.get('content-length', 0))
            self.fileSize = total_size
            with open(CACHE_PATH + '/modpack.zip.temp', 'wb') as f:
                for chunk in request_file_response.iter_content(1024):
                    self.currentProgress += len(chunk)
                    f.write(chunk)

            make_sure_path_exists(MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id)
            shutil.move(CACHE_PATH + '/modpack.zip.temp',
                        MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id + "/" + file_name)
        else:
            print("request pack.zip error.")
        if close_sess:
            sess.close()
        print("FD Done.")

    # TODO Redo the downloader into this function to make it callable to both console and GUI
    def download_mods(self, project_id="242001", file_id="2349268"):
        try:
            # TODO Fix ProjectID to actual ID
            project_response = self.sess.get("https://minecraft.curseforge.com/projects/%s" % project_id, stream=True)
            project_response.url = project_response.url.replace('?cookieTest=1', '')
            # TODO Fix ProjectID to actual ID, Fix fileID to actual file ID
            requested_file_response = self.sess.get("%s/files/%s/download" %
                                                    (project_response.url, file_id), stream=True)
            print(requested_file_response.url)
            if requested_file_response.status_code == 200:
                total_size = int(requested_file_response.headers.get('content-length', 0))
                if total_size is None:  # unknown content size
                    print("I don't know the size :(")
                self.fileSize = total_size
                with open('test.jar', 'wb') as f:
                    for chunk in requested_file_response.iter_content(1024):
                        self.currentProgress += len(chunk)
                        f.write(chunk)
            file_url = Path(requested_file_response.url)
            file_name = unquote(file_url.name).split('?')[0]
            if (requested_file_response.status_code == 404) or (file_name == "download"):
                print("")
            self.isDone = True
            # Catch any threaded exceptions, mark the thread as finished and the re-raise the exception.
            # this allows calling thread to detect the thread has finished processing and can continue doing "stuff".
        except Exception as e:
            self.isDone = True
            raise e


def make_sure_path_exists(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise


def initialize_program_environment():
    print("Curse PDM: Checking/Initializing program environment\n")
    make_sure_path_exists(MODPACK_ZIP_CACHE)
    make_sure_path_exists(MOD_CACHE)
    # TODO: Program settings file. create if non-existing.
    # TODO: Add other steps that should be check at startup time.
    pass
