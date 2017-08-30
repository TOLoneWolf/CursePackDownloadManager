import argparse
import shutil
import zipfile
from pathlib import Path
from urllib.parse import unquote

import errno
import requests
import os
import os.path
import sys
import json
import logging
import time

parser = argparse.ArgumentParser(description="Download Curse modpack mods")
parser.add_argument("--manifest", help="manifest.json file from unzipped pack")
parser.add_argument("--debug", dest="debug", action="store_true", help="Run in debugger mode.")
args, unknown = parser.parse_known_args()

if args.debug:
    log_level = "DEBUG"

else:
    log_level = "WARNING"

# --- Logger Settings
LOG_FILE = "curseforgePDM.log"

# --- Logger
logFormatter = logging.Formatter("%(asctime)s[%(threadName)-12.12s][%(levelname)-5.5s][ln:%(lineno)d]%(message)s")
log = logging.getLogger()
log.setLevel(log_level)

fileHandler = logging.FileHandler(LOG_FILE)
fileHandler.setFormatter(logFormatter)
log.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
log.addHandler(consoleHandler)

log.critical("critical")  # numeric value 50
log.error("error")  # numeric value 40
log.warning("warning")  # numeric value 30
log.info("info")  # numeric value 20
log.debug("debug")  # numeric value 10
# --- Logger

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
    log.debug("unzip\npath to zip: " + str(path_to_zip_file) + " dst_dir: " + str(dst_dir))
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


def copy_instance(existing_instance_dir, new_copy_dir, sym_links=True):
    """
    :param existing_instance_dir: source directory string.
    :param new_copy_dir: destination directory string.
    :param sys_links: copies sym_link paths.
    """
    log.debug("copy_instance\nsrc=" + existing_instance_dir + " " + "dst=" + new_copy_dir)
    shutil.copytree(src=existing_instance_dir, dst=new_copy_dir, symlinks=sym_links)


def get_human_readable(size, precision=2, requestz=-1):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    suffix_index = 0
    if requestz == -1:
        while size > 1024 and suffix_index < 4:
            suffix_index += 1  # increment the index of the suffix
            size /= 1024.0  # apply the division
    elif (requestz >= 1 or requestz == 4):
        i = 0
        while i < requestz:
            suffix_index += 1  # increment the index of the suffix
            size /= 1024.0  # apply the division
            i += 1

    return "%s%s" % (str("{:.3g}".format(round(size, precision))), suffixes[suffix_index])


class CurseDownloader:
    def __init__(self):
        self.sess = requests.Session()
        self.master_thread_running = True
        self.isDone = False
        self.fileSize = None
        self.current_progress = 0
        self.current_progress_finish = 0
        self.total_progress = 0
        self.total_progress_finish = 0

    def reset_download_status(self):
        """
        :Resets all download status vars:
        :self.isDone: = False
        :self.fileSize: = None
        :self.current_progress: = 0
        :self.current_progress_finish: = 0
        :self.total_progress: = 0
        :self.total_progress_finish: = 0
        :return: None
        """
        self.isDone = False
        self.fileSize = None
        self.current_progress = 0
        self.current_progress_finish = 0
        self.total_progress = 0
        self.total_progress_finish = 0

    # FIXME: This might no longer be needed thanks to the retrieve_pack_version_lists method below.
    # def download_curse_pack_url(self, url=None):
    #     if url is None:
    #         raise SyntaxError('The url argument was missing or empty.')
    #     # https://mods.curse.com/modpacks/minecraft
    #     # https://mods.curse.com/modpacks/minecraft/256183-ftb-presents-skyfactory-3
    #     # https://www.feed-the-beast.com/projects/ftb-presents-skyfactory-3/files/latest
    #     latest = self.sess.get("https://minecraft.curseforge.com/projects/" + str(url) + "/files/latest")
    #     if latest.status_code == 200:
    #         log.debug(latest.url)
    #     else:
    #         log.debug("Error: No Mod Pack Found At Provided Project Name/ID.")
    #         log.debug(latest.url)

    # view-source:https://minecraft.curseforge.com/projects/project-ozone-2-reloaded/files
    def retrieve_pack_version_lists(self, project_identifier):
        """
        :param project_identifier: curseforge project name or numeric id.
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

        sess_response = self.sess.get(
            "https://minecraft.curseforge.com/projects/" + project_identifier + "/files")

        log.debug("status code: %d" % sess_response.status_code)
        if sess_response.status_code == 200:
            # log.debug(len('https://minecraft.curseforge.com/projects/'), len('/files')) # should be: 42 6
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
                return []

    def download_modpack_zip(self, project_name, project_id, file_id, session_id=None):
        self.reset_download_status()
        log.info("download_modpack_zip\n" + "project_name: " + project_name + " file_id: " + file_id)
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
                file_name = os.path.basename(os.path.normpath(cache_file[0] ))  # copy name of first file to var.
                return MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id + "/" + file_name

        # TODO: Download modpack.zip
        request_file_response = sess.get(
            "https://minecraft.curseforge.com/projects/{0}/files/{1}/download".format(
                project_name, file_id), stream=True)
        log.debug(request_file_response.url)
        if request_file_response.status_code == 200:
            file_url = Path(request_file_response.url)
            file_name = unquote(file_url.name).split('?')[0]
            total_size = int(request_file_response.headers.get('content-length', 0))
            print(str(file_name + " (DL: " + get_human_readable(total_size) + ")"))
            self.fileSize = total_size
            with open(CACHE_PATH + '/modpack.zip.temp', 'wb') as f:
                for chunk in request_file_response.iter_content(1024):
                    self.current_progress += len(chunk)
                    f.write(chunk)
                    if self.master_thread_running is False:
                        sys.exit()

            create_dir_if_not_exist(MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id)
            shutil.move(CACHE_PATH + '/modpack.zip.temp',
                        MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id + "/" + file_name)
        else:
            return None
        if close_sess:
            sess.close()
        self.fileSize = 0
        self.isDone = True
        return MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id + "/" + file_name

    def unpack_modpack_zip(self, src_dir, dst_folder_name, dst_dir):
        # TODO: unpack.
        # FIXME: unpack.
        unzip(src_dir, dst_dir+dst_folder_name)
        pass

    # TODO Redo the downloader into this function to make it callable to both console and GUI
    def download_mods(self, working_dir):
        self.reset_download_status()
        # project_id = "242001"
        # file_id = "2349268"
        # working_dir = "D:/Users/User/Downloads/Minecraft/#-cursePackManifests/test/"
        manifest_path = Path(os.path.normpath(os.path.join(working_dir, "manifest.json")))
        manifest_text = manifest_path.open().read()
        manifest_text = manifest_text.replace('\r', '').replace('\n', '')
        manifest_json = json.loads(manifest_text)
        try:
            if not "minecraftModpack" == manifest_json['manifestType']:
                log.info('Manifest Error. manifestType is not "minecraftModpack"')
                print('Manifest Error. manifestType is not "minecraftModpack"')
                return None
        except KeyError as e:
            log.warning("manifestType: I got a KeyError - reason %s Manifest Error." % str(e))
            log.warning("manifest: " + str(manifest_path))
            print('I got a KeyError - reason %s' % str(e))
            print("Manifest Error. Make sure you selected a valid pack manifest.json")
            self.isDone = True
            return None

        try:
            override_path = Path(working_dir, manifest_json['overrides'])
            minecraft_path = Path(working_dir, "minecraft")
            mods_path = minecraft_path / "mods"
        except KeyError as e:
            log.warning('overrides: I got a KeyError - reason %s' % str(e))
            log.warning("manifest: " + str(manifest_path))
            print('I got a KeyError - reason %s' % str(e))
            print("Manifest Error. Make sure you selected a valid pack manifest.json")
            self.isDone = True
            return None

        if override_path.exists():
            if not minecraft_path.exists():
                log.info("shutil.move: " + str(override_path) + str(minecraft_path))
                shutil.move(str(override_path), str(minecraft_path))
        if not minecraft_path.exists():
            log.debug("mkdir: " + str(minecraft_path))
            minecraft_path.mkdir()
        if not mods_path.exists():
            log.debug("mkdir: " + str(mods_path))
            mods_path.mkdir()

        current_files_dl = 1
        try:
            total_files_dl = len(manifest_json['files'])
            if total_files_dl == 0:
                print("No Mods")
        except KeyError as e:
            log.warning('files: I got a KeyError - reason %s' % str(e))
            print('I got a KeyError - reason %s' % str(e))
            print("Manifest Error. Make sure you selected a valid pack manifest.json")
            self.isDone = True
            return None

        log.info("Cached files are stored here:\n %s\n" % os.path.abspath(CACHE_PATH))
        print("Cached files are stored here:\n %s\n" % os.path.abspath(CACHE_PATH))
        print("%d files to download" % total_files_dl)

        self.total_progress_finish = total_files_dl
        self.total_progress = current_files_dl

        # FIXME: REMOVE THIS TEMP SESSION MANAGER
        sess = requests.session()
        for dependency in manifest_json['files']:
            if self.master_thread_running is False:
                log.error("Main Thread Dead, Joining it in the after life.")
                sys.exit()
            dep_cache_dir = Path(str(MOD_CACHE) + "/" + str(dependency['projectID']) + "/" + str(dependency['fileID']))
            if dep_cache_dir.is_dir():
                # File is cached
                dep_files = [f for f in dep_cache_dir.iterdir()]
                if len(dep_files) >= 1:
                    dep_file = dep_files[0]
                    target_file = minecraft_path / "mods" / dep_file.name
                    shutil.copyfile(str(dep_file), str(target_file))
                    print("[%d/%d] %s (cached)" % (current_files_dl, total_files_dl, target_file.name))

                    current_files_dl += 1
                    self.total_progress = current_files_dl

                    # Cache access is successful,
                    # Don't download the file
                    continue

            # File is not cached and needs to be downloaded
            try:
                project_response = sess.get(
                    "http://minecraft.curseforge.com/projects/{0}".format(
                        dependency['projectID']), stream=True)
                file_response = sess.get(
                    "{0}/files/{1}/download".format(
                        project_response.url, dependency['fileID']), stream=True)
                requested_file_sess = sess.get(file_response.url, stream=True)

                remote_url = Path(requested_file_sess.url)
                file_name = unquote(remote_url.name).split('?')[0]  # If query data strip it and return just the file name.

                log.debug(str(requested_file_sess.status_code))
                log.debug(str(requested_file_sess.headers['content-type']))

                if (requested_file_sess.status_code == 404) or (file_name == "download"):
                    print(str("[%d/%d] " + "Trying to resolve using alternate requesting.") % (current_files_dl, total_files_dl))

                    # If curse website fails to provide correct url try Dries API list.
                    # get the json from Dries:
                    metabase = "https://cursemeta.dries007.net"
                    metaurl = "%s/%s/%s.json" % (metabase, dependency['projectID'], dependency['fileID'])
                    r = sess.get(metaurl)
                    r.raise_for_status()
                    main_json = r.json()
                    if "code" in main_json:
                        print(str("[%d/%d] " + "ERROR FILE MISSING FROM SOURCE") % (current_files_dl, total_files_dl))
                        # TODO: READD: erred_mod_downloads.append(metaurl.url)
                        current_files_dl += 1
                        continue
                    fileurl = main_json["DownloadURL"]
                    file_name = main_json["FileNameOnDisk"]
                    requested_file_sess = sess.get(fileurl, stream=True)

                try:
                    # TODO: check if no content-length and skip setting.
                    full_file_size = int(requested_file_sess.headers.get('content-length'))
                    log.debug(str(requested_file_sess.headers['content-length']))
                except TypeError:
                    print(str("[%d/%d] " + "MISSING FILE SIZE") % (current_files_dl, total_files_dl))
                    full_file_size = 100

                print(str("[{0}/{1}] " + file_name + " (DL: " + get_human_readable(full_file_size) + ")").format(
                    current_files_dl, total_files_dl))
                with open(str(Path(CACHE_PATH) / file_name), 'wb') as file_data:
                    for chunk in requested_file_sess.iter_content(chunk_size=1024):
                        self.current_progress += len(chunk)
                        file_data.write(chunk)
                        if self.master_thread_running is False:
                            log.error("Main Thread Dead, Joining it in the after life.")
                            sys.exit()
                    self.current_progress = 0

                # Try to add file to cache.
                if not dep_cache_dir.exists():
                    log.debug("dep_cache.mkdir: " + dep_cache_dir)
                    dep_cache_dir.mkdir(parents=True)

                log.debug("shutil.move: src: " + str(Path(CACHE_PATH) / file_name) +
                          " dst: " + str(dep_cache_dir / file_name))

                shutil.move(str(Path(CACHE_PATH) / file_name),
                            str(dep_cache_dir / file_name))

                log.debug("shutil.copyfile: src: " + str(dep_cache_dir / file_name) +
                          " dst: " + str(dep_cache_dir / file_name))

                shutil.copyfile(str(dep_cache_dir / file_name),
                                str(mods_path / file_name))  # Rename from temp to correct file name.

                current_files_dl += 1
                self.total_progress = current_files_dl
                log.debug("current_files_dl: " + current_files_dl)

                # TODO: ADD: ERRED MOD DOWNLOADS DISPLAY
                # if len(erred_mod_downloads) is not 0:
                #     print("\n!! WARNING !!\nThe following mod downloads failed.")
                #     for index in erred_mod_downloads:
                #         print("- " + index)
                #     # Create log of failed download links to pack manifest directory for user to inspect manually.
                #     log_file = open(str(target_dir_path / "cursePackDownloaderModErrors.log"), 'w')
                #     log_file.write("\n".join(str(elem) for elem in erred_mod_downloads))
                #     log_file.close()
                #     print("See log in manifest directory for list.\n!! WARNING !!\n")
                #     erred_mod_downloads.clear()

                self.isDone = True
                # Catch any threaded exceptions, mark the thread as finished and the re-raise the exception.
                # this allows calling thread to detect the thread has finished processing and can continue doing "stuff".
            except Exception as e:
                self.isDone = True
                raise e
        self.isDone = True
        log.info("Finished Processing All Mods Listed In Manifest.")
        print("Unpacking Complete")
        sess.close()


def create_dir_if_not_exist(path):
    log.debug("create_dir_if_not_exist: " + path)
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise


def initialize_program_environment():
    log.debug("Curse PDM: Checking/Initializing program environment")
    create_dir_if_not_exist(MODPACK_ZIP_CACHE)
    create_dir_if_not_exist(MOD_CACHE)
    # TODO: Program settings file. create if non-existing.
    # TODO: Add other steps that should be check at startup time.
    pass
