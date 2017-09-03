import argparse
import shutil
import zipfile
from pathlib import Path
from urllib.parse import unquote

import errno
import requests
import os
import os.path
# from os.path import join as Join
import sys
import json
import logging
import time

'''
Author(s): TOLoneWolf

This contains the core functions of the downloader to separate it from the input interface types CLI and/or GUI.
'''

# --- Logger Settings
LOG_FILE = "pdm_log.log"

# --- Settings
PROGRAM_NAME = 'Curse Pack Download Manager'
PROGRAM_VERSION_NUMBER = '0.0.0.1'
PROGRAM_VERSION_BUILD = 'Alpha'

CACHE_PATH = "curse_download_cache"
MODPACK_ZIP_CACHE = os.path.join(CACHE_PATH, "modpacks_cache")
MOD_CACHE = os.path.join(CACHE_PATH, "mods_cache")
INSTANCE_SETTINGS_FOLDER = "pdm_instance"
CONFIG_FILE = "pdm_settings.json"
INSTALLED_INSTANCE_FILE = "pdm_installed_instances.json"
# program_settings should get new values on load.
program_settings = {
            "self_update_check": True,
            "on_start_check_instance_updates": True,
            "self_update_check_url": "https://raw.githubusercontent.com/TOLoneWolf/cursePackDownloadManager/master/.github/current_version.txt",
            "update_url": "https://raw.githubusercontent.com/TOLoneWolf/cursePackDownloadManager/releases",
            "installed_instances": INSTALLED_INSTANCE_FILE
        }
sess = requests.session()
sess.headers.update({
    'User-Agent': requests.utils.default_user_agent() +
    ' ' + PROGRAM_NAME + '/' + PROGRAM_VERSION_NUMBER + '-' + PROGRAM_VERSION_BUILD})

# --- Parse in arguments.
parser = argparse.ArgumentParser(description="Download Curse modpack mods")
parser.add_argument("--manifest", help="manifest.json file from unzipped pack")
parser.add_argument("--debug", dest="debug", action="store_true", help="Run in debugger mode.")
parser.add_argument("--verbose", action="store_true", help="Outputs standard operation messages to console.")
args, unknown = parser.parse_known_args()

if args.debug:
    log_level = "DEBUG"
elif args.verbose:
    log_level = "INFO"
else:
    log_level = "WARNING"  # Default.

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

# # --- Test logger levels.
# log.critical("critical")  # numeric value 50
# log.error("error")  # numeric value 40
# log.warning("warning")  # numeric value 30
# log.info("info")  # numeric value 20
# log.debug("debug")  # numeric value 10
# # ---


def load_json_file(src_file):
    with open(src_file, 'r') as file:
        return json.load(file)


def save_json_file(json_configs, dst_file):
    with open(dst_file, 'w') as file:
        json.dump(json_configs, file, indent=4, sort_keys=True)


def move_overwrite_dir(src, dest, ignore=None):
    def _recursive_overwrite(src, dest, ignore=None):
        if os.path.isdir(src):
            if not os.path.isdir(dest):
                os.makedirs(dest)
            files = os.listdir(src)
            if ignore is not None:
                ignored = ignore(src, files)
            else:
                ignored = set()
            for f in files:
                if f not in ignored:
                    _recursive_overwrite(os.path.join(src, f),
                                        os.path.join(dest, f),
                                        ignore)
        else:
            shutil.copyfile(src, dest)
    _recursive_overwrite(src, dest, ignore)
    shutil.rmtree(src)


def create_dir_if_not_exist(path):
    log.debug("create_dir_if_not_exist: " + str(path))
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise


def init_pdm_settings():
    # TODO: Finish default configs, and laoding them.
    global program_settings
    if not os.path.exists(CONFIG_FILE):
        config_defaults = {
            "self_update_check": True,
            "on_start_check_instance_updates": True,
            "self_update_check_url": "https://raw.githubusercontent.com/TOLoneWolf/cursePackDownloadManager/master/.github/current_version.txt",
            "update_url": "https://raw.githubusercontent.com/TOLoneWolf/cursePackDownloadManager/releases",
            "installed_instances": INSTALLED_INSTANCE_FILE
        }
        save_json_file(config_defaults, CONFIG_FILE)
        log.debug("Default Program Config Created.")
    if os.path.exists(CONFIG_FILE):
        program_settings = load_json_file(CONFIG_FILE)
        pass


def get_human_readable(size, precision=2, requestz=-1):
    size = float(size)
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    suffix_index = 0
    if requestz == -1:
        while size > 1024.0 and suffix_index < 4:
            suffix_index += 1  # increment the index of the suffix
            size /= 1024.0  # apply the division
    else:
        if requestz > 4:
            requestz = 4
        i = 0
        while i < requestz:
            suffix_index += 1  # increment the index of the suffix
            size /= 1024.0  # apply the division
            i += 1

    return str(round(size, precision)) + suffixes[suffix_index]


def instance_update_check(cd_manager):
    if os.path.exists(INSTALLED_INSTANCE_FILE):
        pack_instance_list = load_json_file(INSTALLED_INSTANCE_FILE)["instances"]
        log.debug(str(INSTALLED_INSTANCE_FILE))
        log.debug(str(pack_instance_list))

        for instance_config in pack_instance_list:
            instance_config = instance_config["location"]

            if os.path.exists(instance_config):  # If config file exist.
                instance_settings = load_json_file(instance_config)
                if not instance_settings["instance_settings"]["update_check"]:
                    continue
                request_results = cd_manager.get_modpack_version_list(instance_settings["instance_settings"]["project_name"])
                # results <- [pack_source, project_id, project_name, bare_pack_version_list]
                log.debug(
                    "Local Version: " + str(instance_settings["instance_settings"]["version_id"]) +
                    "\nRemote Version: " + str(request_results[3][0][1]))
                if int(request_results[3][0][1]) == int(instance_settings["instance_settings"]["version_id"]):
                    print("Same Version")
                elif int(request_results[3][0][1]) > int(instance_settings["instance_settings"]["version_id"]):
                    print("New Version Found")
                    if instance_settings["instance_settings"]["update_automatic"]:
                        dst_dir = os.path.dirname(os.path.dirname(instance_config))
                        dst_folder_name = os.path.basename(os.path.dirname(instance_config))
                        src_zip = cd_manager.download_modpack_zip(request_results[0], request_results[1],
                                                                  request_results[2],
                                                                  request_results[3][0][1])

                        # TODO: copy old manifest to safety for use in update comparision.
                        cd_manager.unpack_modpack_zip(src_zip, dst_folder_name, (dst_dir + "\\"))
                        cd_manager.download_mods(os.path.join(dst_dir, dst_folder_name))
                        instance_settings["instance_settings"]["version_id"] = request_results[3][0][1]  # update version id.
                        save_json_file(instance_settings, instance_config)
                else:
                    print("idk how but you got a newer version then is available?")
            else:
                # TODO handle bad instance paths and remove them?.
                print("instance not found at this path:")
                print(instance_config)
                pass
    else:
        # TODO: Make one at program start if doesn't exist.
        log.error("No pdm_installed_instances.json found.")


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
        dst_dir = os.path.join(directory, filename)
    log.debug("unzip\npath to zip: " + str(path_to_zip_file) + " dst_dir: " + str(dst_dir))
    with zipfile.ZipFile(path_to_zip_file, "r") as zip_ref:
        zip_ref.extractall(dst_dir)


# def make_zipfile(output_filename, source_dir):
#     relative_root = os.path.abspath(Path(source_dir, os.pardir))
#     with zipfile.ZipFile(output_filename, "w", zipfile.ZIP_DEFLATED) as zipFile:
#         for root, dirs, files in os.walk(source_dir):
#             # add directory (needed for empty dirs)
#             zipFile.write(root, os.path.relpath(root, relative_root))
#             for file in files:
#                 filename = os.path.join(root, file)
#                 if os.path.isfile(filename):  # regular files only
#                     arc_name = os.path.join(os.path.relpath(root, relative_root), file)
#                     zipFile.write(filename, arc_name)


def copy_instance(existing_instance_dir, new_copy_dir, sym_links=True):
    """
    :param existing_instance_dir: source directory string.
    :param new_copy_dir: destination directory string.
    :param sym_links: copies sym_link paths.
    :return:
    """
    log.debug("copy_instance\nsrc=" + str(existing_instance_dir) + " " + "dst=" + str(new_copy_dir))
    shutil.copytree(src=existing_instance_dir, dst=new_copy_dir, symlinks=sym_links)


class CurseDownloader:
    def __init__(self):
        self.master_thread_running = True
        self.is_done = False
        self.file_size = 0
        self.current_file_size = 0
        self.total_progress = 0
        self.current_progress = 0
        self.return_arg = ''  # if threaded this is the response.

    def reset_download_status(self):
        self.is_done = False
        self.file_size = 0
        self.current_file_size = 0
        self.total_progress = 0
        self.current_progress = 0
        self.return_arg = ''

    def get_modpack_version_list(self, project_identifier):
        """
        :param project_identifier: curseforge project name or numeric id.
        :return: [project_id, project_name, version_list[0=type,1=id,2=title]] or [] if None.\n

        Example URL's to search.\n
        :ex: https://minecraft.curseforge.com/projects/project-ozone-2-reloaded/files
        :ex: https://www.feed-the-beast.com/projects/ftb-beyond/files
        """

        log.debug("get_modpack_version_list")
        if type(project_identifier) is str:
            project_identifier = project_identifier.strip().replace(" ", "-").lower()
            if project_identifier == "":
                return []
        else:
            return []

        log.debug("https://minecraft.curseforge.com/projects/" + project_identifier + "/files")
        sess_response = sess.get(
            "https://minecraft.curseforge.com/projects/" + project_identifier + "/files")
        pack_source = "curseforge"
        log.debug("status code: %d" % sess_response.status_code)

        if sess_response.status_code == 404:
            log.debug("https://www.feed-the-beast.com/projects/" + project_identifier + "/files")
            sess_response = sess.get(
                "https://www.feed-the-beast.com/projects/" + project_identifier + "/files")
            pack_source = "ftb"
            log.debug("status code: %d" % sess_response.status_code)

        if sess_response.status_code == 200:
            project_name = sess_response.url.split("/")[-2:-1][0]  # strip down to project name.
            content_list = str(sess_response.content)
            content_list = content_list.split("\\r\\n")
            combine_lines = False
            content_version_list = []
            build_version_element = []
            bare_pack_version_list = []  # bare_pack_version_list[<VersionType>, <FileID>, <VersionTitle>]
            mod_pack_url_true = False
            for line in content_list:
                line = line.strip()
                if mod_pack_url_true:  # Have we seen if it's modpack, before we look for versions in the next lines?
                    if line == "":  # Skip empty lines sooner.
                        pass
                    elif line == '<tr class="project-file-list-item">':
                        combine_lines = True
                    elif line == "</tr>":
                        if combine_lines:
                            content_version_list.append(build_version_element)
                            build_version_element = []
                            combine_lines = False
                    if not line == "":
                        if combine_lines:
                            build_version_element.append(line)
                else:
                    if line == '<a href="/modpacks">Modpacks</a>':
                        mod_pack_url_true = True

            if mod_pack_url_true:
                # log.debug(str(len('<a class="overflow-tip twitch-link" href="/projects//files/')))  # len: 59
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

                return [pack_source, project_id, project_name, bare_pack_version_list]
        return []

    def download_modpack_zip(self, pack_source, project_id, project_name, file_id):
        """
        Downloads a specific modpack.zip and returns the file path to it in the cache directory.
        :param pack_source: which site it comes from ['curseforge','ftb']
        :param project_id: the numberic id for the modpack project '242493'
        :param project_name: The text id/url name 'what-ever-my-name'
        :param file_id: The id for the specific version requested. '2287097'
        :return: MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id + "/" + file_name
        """
        self.reset_download_status()
        log.info(
            "download_modpack_zip\n" +
            "project_name: " + project_name + " file_id: " + file_id)
        #  Check cache for file first.
        dep_cache_dir = os.path.join(MODPACK_ZIP_CACHE, project_id, file_id)
        if os.path.isdir(dep_cache_dir):
            cache_file = [files for files in os.scandir(dep_cache_dir)]  # Create list with files from directory.
            if len(cache_file) >= 1:  # if there is at least one file.
                file_name = os.path.basename(os.path.normpath(cache_file[0]))  # copy name of first file to var.
                log.debug(os.path.join(MODPACK_ZIP_CACHE, project_id, file_id, file_name))
                self.is_done = True
                self.return_arg = os.path.join(MODPACK_ZIP_CACHE, project_id, file_id, file_name)
                return self.return_arg

        if pack_source == "curseforge":
            request_file_response = sess.get(
                "https://minecraft.curseforge.com/projects/{0}/files/{1}/download".format(
                    project_name, file_id), stream=True)
        elif pack_source == "ftb":
            request_file_response = sess.get(
                "https://www.feed-the-beast.com/projects/{0}/files/{1}/download".format(
                    project_name, file_id), stream=True)
        else:
            self.is_done = True
            self.return_arg = ''
            return self.return_arg  # Error detecting pack source url.

        log.debug(str(request_file_response.url))
        if request_file_response.status_code == 200:
            file_url = request_file_response.url
            file_name = unquote(file_url.name).split('?')[0]
            self.file_size = int(request_file_response.headers.get('content-length', 0))
            if self.file_size:
                print(str(file_name + " (DL: " + get_human_readable(self.file_size) + ")"))
            else:
                print(str(file_name + " (DL: " + "size: ?" + ")"))
            with open(CACHE_PATH + '/modpack.zip.temp', 'wb') as f:
                for chunk in request_file_response.iter_content(1024):
                    self.current_file_size += len(chunk)
                    f.write(chunk)
                    if self.master_thread_running is False:
                        sys.exit()

            create_dir_if_not_exist(MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id)
            shutil.move(CACHE_PATH + '/modpack.zip.temp',
                        MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id + "/" + file_name)
        else:
            self.is_done = True
            self.return_arg = ''
            return self.return_arg

        self.is_done = True
        self.return_arg = MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id + "/" + file_name
        return self.return_arg

    def unpack_modpack_zip(self, src_dir, dst_folder_name, dst_dir):
        # FIXME: unpack.
        print(src_dir, dst_dir+dst_folder_name)
        unzip(src_dir, dst_dir+dst_folder_name)
        # TODO: create instance settings.
        pass

    def download_mods(self, instance_dir):
        """
        :param instance_dir: The minecraft directory that contains the curse manifest.json file.
        :return: True on success, False on failure.
        """
        self.reset_download_status()
        manifest_path = os.path.abspath(os.path.join(instance_dir, "manifest.json"))
        log.debug(str(manifest_path))
        manifest_json = load_json_file(manifest_path)

        if 'manifestType' not in manifest_json or not manifest_json['manifestType'] == 'minecraftModpack':
            log.error('Manifest missing manifestType key entry.')
            self.is_done = True
            return False
        elif 'manifestVersion' not in manifest_json or not manifest_json['manifestVersion'] == 1:
            log.error('Manifest missing manifestVersion key entry.')
            self.is_done = True
            return False
        elif 'overrides' not in manifest_json:
            log.error('Manifest missing overrides key entry.')
            self.is_done = True
            return False
        elif 'files' not in manifest_json:
            log.error('Manifest missing files key entries.')
            self.is_done = True
            return False

        override_path = Path(instance_dir, manifest_json['overrides'])
        minecraft_path = Path(instance_dir, "minecraft")
        mods_path = Path(minecraft_path, "mods")

        if override_path.exists():
            log.info("shutil.move: " + str(override_path) + str(minecraft_path))
            move_overwrite_dir(str(override_path), str(minecraft_path))
        if not minecraft_path.exists():
            log.debug("mkdir: " + str(minecraft_path))
            minecraft_path.mkdir()
        if not mods_path.exists():
            log.debug("mkdir: " + str(mods_path))
            mods_path.mkdir()

        self.total_progress = len(manifest_json['files'])

        log.info("Cached files are stored here:\n {0}\n".format(os.path.abspath(CACHE_PATH)))
        log.info("{0} files to download".format(self.total_progress))
        print("Cached files are stored here:\n {0}\n".format(os.path.abspath(CACHE_PATH)))
        print("{0} files to download".format(self.total_progress))

        self.current_progress = 1
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
                    print("[%d/%d] %s (in cache)" % (self.current_progress, self.total_progress, target_file.name))

                    self.current_progress += 1

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
                    print(str("[%d/%d] " + "Trying to resolve using alternate requesting.") % (self.current_progress, self.total_progress))

                    # If curse website fails to provide correct url try Dries API list.
                    # get the json from Dries:
                    metabase = "https://cursemeta.dries007.net"
                    metaurl = "%s/%s/%s.json" % (metabase, dependency['projectID'], dependency['fileID'])
                    r = sess.get(metaurl)
                    r.raise_for_status()
                    main_json = r.json()
                    if "code" in main_json:
                        print(str("[%d/%d] " + "ERROR FILE MISSING FROM SOURCE") % (self.current_progress, self.total_progress))
                        # TODO: READD: erred_mod_downloads.append(metaurl.url)
                        self.current_progress += 1
                        continue
                    fileurl = main_json["DownloadURL"]
                    file_name = main_json["FileNameOnDisk"]
                    requested_file_sess = sess.get(fileurl, stream=True)

                self.file_size = int(requested_file_sess.headers.get('content-length', 0))
                if self.file_size:
                    print(
                        str("[{0}/{1}] " + file_name + " (DL: " + get_human_readable(self.file_size) + ")").format(
                            self.current_progress, self.total_progress))
                else:
                    print(str("[%d/%d] " + "MISSING FILE SIZE") % (self.current_progress, self.total_progress))
                    self.file_size = 100

                if self.master_thread_running is False:
                    log.error("Main Thread Dead, Joining it in the after life.")
                    sys.exit()
                self.current_file_size = 0
                with open(str(Path(CACHE_PATH) / file_name), 'wb') as file_data:
                    for chunk in requested_file_sess.iter_content(chunk_size=1024):
                        self.current_file_size += len(chunk)
                        file_data.write(chunk)
                        if self.master_thread_running is False:
                            file_data.close()
                            os.remove(str(Path(CACHE_PATH) / file_name))
                            log.error("Main Thread Dead, Joining it in the after life.")
                            sys.exit()

                # Try to add file to cache.
                if not dep_cache_dir.exists():
                    log.debug("dep_cache.mkdir: " + str(dep_cache_dir))
                    dep_cache_dir.mkdir(parents=True)

                log.debug("shutil.move: src: " + os.path.join(CACHE_PATH, file_name) +
                          " dst: " + os.path.join(dep_cache_dir, file_name))

                shutil.move(os.path.join(CACHE_PATH, file_name),
                            os.path.join(dep_cache_dir, file_name))

                log.debug("shutil.copyfile: src: " + str(dep_cache_dir / file_name) +
                          " dst: " + str(dep_cache_dir / file_name))

                shutil.copyfile(str(dep_cache_dir / file_name),
                                str(mods_path / file_name))  # Rename from temp to correct file name.

                self.current_progress += 1
                log.debug("self.current_progress: " + str(self.current_progress))
                print("self.current_progress: " + str(self.current_progress))

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

                # Catch any threaded exceptions, mark the thread as finished and the re-raise the exception.
                # this allows calling thread to detect the thread has finished processing and can continue doing "stuff".
            except Exception as e:
                self.is_done = True
                raise e
        log.info("Finished Processing All Mods Listed In Manifest.")
        print("Finished Download Process")
        sess.close()
        self.is_done = True  # End of thread workload.
        return True


def initialize_program_environment():
    log.debug("Curse PDM: Checking/Initializing program environment")
    init_pdm_settings()
    create_dir_if_not_exist(MODPACK_ZIP_CACHE)
    create_dir_if_not_exist(MOD_CACHE)
    # TODO: Program settings file. create if non-existing.
    # TODO: Add other steps that should be check at startup time.


# if __name__ == '__main__':
#     pass

