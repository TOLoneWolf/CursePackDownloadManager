import argparse
import re
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
import stat

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


# keys for the settings dictionary. TODO: keep this?
class KEY:
    self_update_check = "self_update_check"
    on_start_check_instance_updates = "on_start_check_instance_updates"
    self_update_check_url = "self_update_check_url"
    update_url = "update_url"
    installed_instances = "installed_instances"
    default_instance_type = "default_instance_type"
    curse_client = "curse_client"
    MultiMC = "MultiMC"
    Vanilla_Client = "Vanilla_Client"
    cache_path = "cache_path"


# Defaults settings in case we want to reset_dl to them later.
DEFAULT_PROGRAM_SETTINGS = {
    "self_update_check": True,
    "on_start_check_instance_updates": True,
    "self_update_check_url": "https://raw.githubusercontent.com/TOLoneWolf/cursePackDownloadManager/master/.github/current_version.json",
    "update_url": "https://raw.githubusercontent.com/TOLoneWolf/cursePackDownloadManager/releases",
    "installed_instances": "pdm_installed_instances.json",
    "default_instance_type": "MultiMC",
    "custom": "",
    "curse_client": "",
    "MultiMC": "",
    "Vanilla_Client": "",
    "cache_path": "curse_download_cache"
}
# program_settings should get new values on load if user changed them.
program_settings = {}
program_settings.update(DEFAULT_PROGRAM_SETTINGS)
installed_instances = []

CACHE_PATH = "curse_download_cache"  # FIXME:
MODPACK_ZIP_CACHE = os.path.join(CACHE_PATH, "modpacks_cache")
MOD_CACHE = os.path.join(CACHE_PATH, "mods_cache")
PDM_SETTINGS_FILE = "pdm_settings.json"
INSTALLED_INSTANCE_FILE = "pdm_installed_instances.json"  # FIXME:
PDM_INSTANCE_FOLDER = 'pdm_instance'
PDM_INSTANCE_FILE = 'pdm_instance.json'


req_sess = requests.session()
req_sess.headers.update({
    'User-Agent': requests.utils.default_user_agent() +
    ' ' + PROGRAM_NAME + '/' + PROGRAM_VERSION_NUMBER + '-' + PROGRAM_VERSION_BUILD})


# --- Parse in arguments.
parser = argparse.ArgumentParser(description="Download Curse modpack mods")
parser.add_argument("--manifest", help="manifest.json file from unzipped pack")
parser.add_argument("--debug", action="store_true", dest="debug", help="Run in debugger mode.")
parser.add_argument("--verbose", action="store_true", dest="verbose", help="Outputs standard operation messages to console.")
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


# TODO: Create, save, and load instance settings.
def load_instance_settings(instance_dir):
    if os.path.exists(
            os.path.join(instance_dir, PDM_INSTANCE_FOLDER, PDM_INSTANCE_FILE)):
        instance_config = load_json_file(
            os.path.join(instance_dir, PDM_INSTANCE_FOLDER, PDM_INSTANCE_FILE))['instance_settings']
        # print(instance_config)
        if instance_config:
            InstanceInfo.instance_path = instance_dir
            # ---
            InstanceInfo.source = instance_config['url_source']
            InstanceInfo.project_id = instance_config['project_id']
            InstanceInfo.project_name = instance_config['project_name']
            InstanceInfo.version_id = instance_config['version_id']

            InstanceInfo.instance_name = instance_config['instance_name']
            InstanceInfo.install_type = instance_config['install_type']
            InstanceInfo.update_type = instance_config['update_type']
            InstanceInfo.update_check = instance_config['update_check']
            InstanceInfo.update_automatic = instance_config['update_automatic']
            InstanceInfo.merge_custom = instance_config['merge_custom']
            # print(InstanceInfo.source)
            # print(InstanceInfo.project_id)
            # print(InstanceInfo.project_name)
            # print(InstanceInfo.version_id)
            # print(InstanceInfo.instance_name)
            # print(InstanceInfo.install_type)
            # print(InstanceInfo.update_type)
            # print(InstanceInfo.update_check)
            # print(InstanceInfo.update_automatic)
            # print(InstanceInfo.merge_custom)
            return True
    else:
        # No configs :(
        return False


def save_instance_settings(instance_dir):
    if os.path.exists(instance_dir):
        if not os.path.exists(os.path.join(instance_dir, PDM_INSTANCE_FOLDER)):
            os.mkdir(os.path.join(instance_dir, PDM_INSTANCE_FOLDER))
        instance_config = {
            "instance_settings": {
                "url_source": InstanceInfo.source,
                "install_type": InstanceInfo.install_type,
                "instance_name": InstanceInfo.instance_name,
                "project_id": InstanceInfo.project_id,
                "project_name": InstanceInfo.project_name,
                "update_automatic": InstanceInfo.update_automatic,
                "update_check": InstanceInfo.update_check,
                "update_type": InstanceInfo.update_type,
                "version_id": InstanceInfo.version_id,
                "merge_custom": InstanceInfo.merge_custom
            }
        }
        save_json_file(instance_config, os.path.join(instance_dir, PDM_INSTANCE_FOLDER, PDM_INSTANCE_FILE))
    else:
        raise OSError(
            "Path does not exist.\n"
            "Provided Path: {0}".format(os.path.join(instance_dir, PDM_INSTANCE_FOLDER)))
    return True


def mmc_read_cfg(file_path):
    cfg_dictionary = {}
    if os.path.exists(os.path.join(file_path, 'instance.cfg')):
        with open(os.path.join(file_path, 'instance.cfg')) as file_handler:
            if file_handler:
                for file_line in file_handler:
                    file_line = file_line.strip()
                    if file_line is "":
                        continue
                    elif file_line.startswith('#'):
                        continue
                    else:
                        key, value = file_line.split('=')
                        if value.isdigit():
                            value = int(value)
                        # elif value == 'true':
                        #     value = True
                        # elif value == 'false':
                        #     value = False
                        cfg_dictionary[key] = value
    return cfg_dictionary


def mmc_write_cfg(cfg_dictionary, file_path):
    manifest_path = os.path.abspath(os.path.join(file_path, "manifest.json"))
    manifest_json = load_json_file(manifest_path)
    if 'minecraft' not in manifest_json:
        log.error('Manifest missing files key entries.')
        return False
    elif 'version' not in manifest_json['minecraft']:
        return False
    elif 'modLoaders' not in manifest_json['minecraft']:
        return False
    elif not manifest_json['minecraft']['modLoaders'][0]['id'].startswith('forge-'):
        raise ValueError("Manifest forge version not detected correctly.")
    # print('ForgeVersion=' + str(manifest_json['minecraft']['modLoaders'][0]['id']))
    # print('InstanceType=OneSix')
    # print('IntendedVersion=' + str(manifest_json['minecraft']['version']))
    # print('MCLaunchMethod=LauncherPart')
    # print('iconKey=default')
    # print('name=' + str(os.path.basename(file_path)))

    if type(cfg_dictionary) is dict:
        if cfg_dictionary:
            cfg_dictionary.update({
                'ForgeVersion': str(manifest_json['minecraft']['modLoaders'][0]['id'][6:]),
                'IntendedVersion': str(manifest_json['minecraft']['version']),
            })
        else:
            cfg_dictionary.update({
                'ForgeVersion': str(manifest_json['minecraft']['modLoaders'][0]['id'][6:]),
                'InstanceType': 'OneSix',
                'IntendedVersion': str(manifest_json['minecraft']['version']),
                'MCLaunchMethod': 'LauncherPart',
                # 'iconKey': 'flame',  # default, flame
                'iconKey': InstanceInfo.project_name + '_icon',
                'name': str(os.path.basename(file_path))
            })
        if os.access(os.path.dirname(os.path.abspath(os.path.join(file_path, 'instance.cfg'))), os.W_OK):
            with open(os.path.join(file_path, 'instance.cfg'), 'w') as file_handler:
                for key, value in cfg_dictionary.items():
                    file_handler.write(str(key + '=' + str(value) + '\n'))
                return True
    return False


def save_program_settings():
    save_json_file(program_settings, PDM_SETTINGS_FILE)
    pass


def movetree_overwrite_dst(m_src, m_dest, m_ignore=None):
    def _recursive_overwrite(src, dest, ignore):
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
                    _recursive_overwrite(
                        os.path.join(src, f),
                        os.path.join(dest, f),
                        ignore)
        else:
            shutil.move(src, dest)
    _recursive_overwrite(m_src, m_dest, m_ignore)
    shutil.rmtree(m_src)


def copytree_overwrite_dst(m_src, m_dest, m_ignore=None):
    def _recursive_overwrite(src, dest, ignore):
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
                    _recursive_overwrite(
                        os.path.join(src, f),
                        os.path.join(dest, f),
                        ignore)
        else:
            shutil.copyfile(src, dest)
    _recursive_overwrite(m_src, m_dest, m_ignore)


def shutil_rmtree_on_rm_error(func, path, exc_info):
    """
    shutil.rmtree(installed_instances[<directory>, onerror=shutil_rmtree_on_rm_error)

    :param func:
    :param path: path to file/dir that failed to delete.
    :param exc_info:

    Now, to be fair, the error function could be called for a variety of reasons.
    The 'func' parameter can tell you what function "failed"(os.rmdir() or os.remove()).
    What you do here depends on how bullet proof you want your rmtree to be.
    If it's really just a case of needing to mark files as writable, you could do what I did above.
    If you want to be more careful (i.e. determining if the directory coudln't be removed,
        or if there was a sharing violation on the file while trying to delete it),
        the appropriate logic would have to be inserted into the shutil_rmtree_on_rm_error() function.
    """
    # https://stackoverflow.com/questions/4829043/how-to-remove-read-only-attrib-directory-with-python-in-windows#4829285
    # Sigh.. why can't removing things be nicer...
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    os.chmod(path, stat.S_IWRITE)
    os.unlink(path)


def create_dir_if_not_exist(path):
    log.debug("create_dir_if_not_exist: " + str(path))
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise


def init_pdm_settings():
    # TODO: Finish default configs, and loading them.
    if not os.path.exists(PDM_SETTINGS_FILE):
        save_json_file(program_settings, PDM_SETTINGS_FILE)
        log.debug("Default Program Config Created.")
    if os.path.exists(PDM_SETTINGS_FILE):
        program_settings.update(load_json_file(PDM_SETTINGS_FILE))


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


class InstanceInfo:
    source = ''
    project_id = 0
    project_name = ''
    version_id = 0
    instance_name = ''
    install_type = 'mmc'  # types: mmc, curse
    update_type = ''
    update_check = False
    update_automatic = False
    merge_custom = True

    instance_path = ''
    pack_icon_url = ''
    update_version_id = 0
    list_version_id = []

    master_thread_running = True
    is_done = False
    file_size = 0
    current_file_size = 0
    total_progress = 0
    current_progress = 0
    return_arg = ''

    def reset_dl(self):
        self.is_done = False
        self.file_size = 0
        self.current_file_size = 0
        self.total_progress = 0
        self.current_progress = 0
        self.return_arg = ''

    def clear_instance(self):
        self.source = ''
        self.project_id = 0
        self.project_name = ''
        self.version_id = 0
        self.instance_name = ''
        self.instance_path = ''
        self.pack_icon_url = ''
        self.list_version_id[:] = []
        self.reset_dl()

def instance_update_check():
    # FIXME: redo this to use internal copy instead of loading file every time.
    # TODO: Change to 2 functions, on that supplies list to check to the seond that does the check of each instances passed.
    # TODO: Some kind of project specific update check cache,
    #   to prevent checking same project multiple times within short time frame.
    # Store as dictionary key of project ID, storing version information and pass that on to the update check.
    if os.path.exists(INSTALLED_INSTANCE_FILE):
        pack_instance_list = load_json_file(INSTALLED_INSTANCE_FILE)["instances"]
        log.debug(str(INSTALLED_INSTANCE_FILE))
        log.debug(str(pack_instance_list))
        if pack_instance_list:
            pack_instance_list[:] = [instance_config for instance_config in pack_instance_list if
                                     os.path.exists(os.path.join(instance_config["location"], PDM_INSTANCE_FOLDER, PDM_INSTANCE_FILE))]
            if pack_instance_list:
                save_json_file({"instances": pack_instance_list}, INSTALLED_INSTANCE_FILE)  # FIXME: Do this in a better way to inform the user and give them a chance to fix the path?
                for instance_config in pack_instance_list:
                    instance_config = os.path.join(instance_config["location"], PDM_INSTANCE_FOLDER, PDM_INSTANCE_FILE)
                    if os.path.exists(instance_config):  # If config file exist.
                        instance_settings = load_json_file(instance_config)
                        if not instance_settings["instance_settings"]["update_check"]:
                            continue
                        request_results = get_modpack_version_list(instance_settings["instance_settings"]["project_name"])
                        # results <- [pack_source, project_id, project_name, bare_pack_version_list]
                        print("Instance Name: " + instance_settings["instance_settings"]["instance_name"])
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
                                src_zip = download_modpack_zip(request_results[0], request_results[1],
                                                                          request_results[2],
                                                                          request_results[3][0][1])

                                # TODO: copy old manifest to safety for use in update comparision of mods???.
                                unpack_modpack_zip(src_zip, dst_folder_name, (dst_dir + "\\"))
                                download_mods(os.path.join(dst_dir, dst_folder_name))
                                instance_settings["instance_settings"]["version_id"] = request_results[3][0][1]  # update version id.
                                if 'mmc' in instance_settings['instance_settings']['install_type']:
                                    mmc_file_contents = mmc_read_cfg(dst_dir)
                                    if mmc_write_cfg(mmc_file_contents, dst_dir):
                                        print("MultiMC settings Saved.")
                                    else:
                                        raise RuntimeError("MultiMC settings file save failed to execute correctly.")
                                save_json_file(instance_settings, instance_config)
                        else:
                            print("idk how but you got a newer version then is available?")
                    else:
                        # TODO handle bad instance paths and remove them?.
                        print("instance not found at this path:")
                        print(instance_config)
                        pass
        else:
            print("No instances seam to exist right now.")
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
        dst_dir = os.path.normpath(directory + "\\" + filename)
    log.debug("unzip\npath to zip: " + str(path_to_zip_file) + " dst_dir: " + str(dst_dir))
    with zipfile.ZipFile(path_to_zip_file, "r") as zip_ref:
        zip_ref.extractall(dst_dir)


# def make_zipfile(output_filename, source_dir):
#     relative_root = os.path.abspath(os.path.join(source_dir, os.pardir))
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


def get_modpack_version_list(project_identifier):
    """
    :param project_identifier: curseforge project name or numeric id.
    :return: [project_id, project_name, version_list[0=type,1=id,2=title]] or [] if None.\n

    Example URL's to search.\n
    :ex: https://minecraft.curseforge.com/projects/project-ozone-2-reloaded/files
    :ex: https://www.feed-the-beast.com/projects/ftb-beyond/files
    """
    if type(project_identifier) is str:
        project_identifier = project_identifier.strip().replace(" ", "-").replace(".", "-").lower()
        if project_identifier == "":
            return ['', 0, '', []]
    else:
        return ['', 0, '', []]

    log.debug("https://minecraft.curseforge.com/projects/" + project_identifier + "/files")
    sess_response = req_sess.get(
        "https://minecraft.curseforge.com/projects/" + project_identifier + "/files")
    pack_source = "curseforge"
    log.debug("status code: {0}".format(sess_response.status_code))

    if sess_response.status_code == 404:
        log.debug("https://www.feed-the-beast.com/projects/" + project_identifier + "/files")
        sess_response = req_sess.get(
            "https://www.feed-the-beast.com/projects/" + project_identifier + "/files")
        pack_source = "ftb"
        log.debug("status code: {0}".format(sess_response.status_code))

    if sess_response.status_code == 200:
        project_name = sess_response.url.split("/")[-2:-1][0]  # strip down to project name.
        content_list = str(sess_response.content)
        content_list = content_list.split("\\r\\n")
        combine_lines = False
        content_version_list = []
        build_version_element = []
        bare_pack_version_list = []  # bare_pack_version_list[<VersionType>, <FileID>, <VersionTitle>]
        mod_pack_url_true = False
        current_page_count = 1
        InstanceInfo.pack_icon_url = ''
        for line in content_list:
            line = line.strip().replace("&#x27;", "'")
            if not InstanceInfo.pack_icon_url:
                if line.startswith('<a class="e-avatar64 lightbox" href="') and line.endswith('.png">'):
                    InstanceInfo.pack_icon_url = line[37:-2]
                    continue
            if mod_pack_url_true:  # Have we seen if it's modpack, before we look for versions in the next lines?
                for test_number in re.findall('(?<=page=)\w+', line):
                    test_number = int(test_number)
                    if current_page_count < test_number:
                        current_page_count = test_number
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
        if current_page_count > 1:
            log.debug("Page count: " + str(current_page_count))
            for page in range(2, current_page_count+1):
                if pack_source == 'curseforge':
                    sess_response = req_sess.get(
                        "https://minecraft.curseforge.com/projects/" + project_identifier + "/files/?page=" + str(current_page_count))
                elif pack_source == 'ftb':
                    sess_response = req_sess.get(
                        "https://www.feed-the-beast.com/projects/" + project_identifier + "/files/?page=" + str(current_page_count))
                log.debug("URL: " + sess_response.url)
                if sess_response.status_code == 200:
                    content_list = str(sess_response.content)
                    content_list = content_list.split("\\r\\n")
                    combine_lines = False
                    for line in content_list:
                        line = line.strip().replace("&#x27;", "'")
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
                    raise ConnectionError("URL request failed sub page request: " + sess_response.url)

        if mod_pack_url_true:
            # print(len('<a class="overflow-tip twitch-link" href="/projects//files/'))  # len: 59
            fileid_start_pos = len(project_name) + 59
            log.debug("Project Name: " + str(project_name))
            log.debug("Start Pos: " + str(fileid_start_pos))
            project_id = content_version_list[0][9][9:15]
            for listElement in content_version_list:
                if listElement[2] == '<div class="release-phase tip" title="Release"></div>':
                    bare_pack_version_list.append(
                        [1, listElement[7][fileid_start_pos:-1], listElement[9][28:-4].split(">", 1)[1]])
                elif listElement[2] == '<div class="beta-phase tip" title="Beta"></div>':
                    bare_pack_version_list.append(
                        [2, listElement[7][fileid_start_pos:-1], listElement[9][28:-4].split(">", 1)[1]])
                elif listElement[2] == '<div class="alpha-phase tip" title="Alpha"></div>':
                    bare_pack_version_list.append(
                        [3, listElement[7][fileid_start_pos:-1], listElement[9][28:-4].split(">", 1)[1]])

            print(bare_pack_version_list)
            return [pack_source, project_id, project_name, bare_pack_version_list]
    return ['', 0, '', []]


def download_modpack_zip(pack_source, project_id, project_name, file_id):
    # TODO: remove project_name? curese seems to respond now to ids in the project url while requesting the download.
    """
    Downloads a specific modpack.zip and returns the file path to it in the cache directory.
    :param pack_source: which site it comes from ['curseforge','ftb']
    :param project_id: the numberic id for the modpack project '242493'
    :param project_name: The text id/url name 'what-ever-my-name'
    :param file_id: The id for the specific version requested. '2287097'
    :return: MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id + "/" + file_name
    """
    InstanceInfo().reset_dl()
    log.info("download_modpack_zip\n" + "project_name: " + project_name + " file_id: " + file_id)
    #  Check cache for file first.
    dep_cache_dir = Path(MODPACK_ZIP_CACHE + "/" + str(project_id) + "/" + str(file_id))
    if dep_cache_dir.is_dir():
        cache_file = [files for files in dep_cache_dir.iterdir()]  # Create list with files from directory.
        if len(cache_file) >= 1:  # if there is at least one file.
            file_name = os.path.basename(os.path.normpath(cache_file[0]))  # copy name of first file to var.
            log.debug(MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id + "/" + file_name)
            InstanceInfo.is_done = True
            InstanceInfo.return_arg = MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id + "/" + file_name

            if not os.path.exists(os.path.join(MODPACK_ZIP_CACHE, project_id, 'pack_icon.png')):
                InstanceInfo.current_file_size = 0
                request_file_response = req_sess.get(InstanceInfo.pack_icon_url, stream=True)
                with open(os.path.join(CACHE_PATH, 'pack_icon.png'), 'wb') as fh:
                    for chunk in request_file_response.iter_content(1024):
                        InstanceInfo.current_file_size += len(chunk)
                        fh.write(chunk)
                shutil.move(
                    os.path.join(CACHE_PATH, 'pack_icon.png'),
                    os.path.join(MODPACK_ZIP_CACHE, project_id, 'pack_icon.png'))

            return InstanceInfo.return_arg

    if pack_source == "curseforge":
        request_file_response = req_sess.get(
            "https://minecraft.curseforge.com/projects/{0}/files/{1}/download".format(
                project_id, file_id), stream=True)
    elif pack_source == "ftb":
        request_file_response = req_sess.get(
            "https://www.feed-the-beast.com/projects/{0}/files/{1}/download".format(
                project_id, file_id), stream=True)
    else:
        InstanceInfo.is_done = True
        InstanceInfo.return_arg = ''
        return InstanceInfo.return_arg  # Error detecting pack source url.

    log.debug(request_file_response.url)
    if request_file_response.status_code == 200:
        file_url = Path(request_file_response.url)
        file_name = unquote(file_url.name).split('?')[0]
        InstanceInfo.file_size = int(request_file_response.headers.get('content-length', 0))
        if InstanceInfo.file_size:
            print(str(file_name + " (DL: " + get_human_readable(InstanceInfo.file_size) + ")"))
        else:
            print(str(file_name + " (DL: " + "size: ?" + ")"))

        modpack_part_path = os.path.join(CACHE_PATH, file_name + '.part')
        with open(modpack_part_path, 'wb') as f:
            for chunk in request_file_response.iter_content(1024):
                InstanceInfo.current_file_size += len(chunk)
                f.write(chunk)
                if InstanceInfo.master_thread_running is False:
                    sys.exit()

        create_dir_if_not_exist(MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id)
        shutil.move(modpack_part_path,
                    MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id + "/" + file_name)

        if not os.path.exists(os.path.join(MODPACK_ZIP_CACHE, project_id, 'pack_icon.png')):
            InstanceInfo.current_file_size = 0
            request_file_response = req_sess.get(InstanceInfo.pack_icon_url, stream=True)
            with open(os.path.join(CACHE_PATH, 'pack_icon.png'), 'wb') as fh:
                for chunk in request_file_response.iter_content(1024):
                    InstanceInfo.current_file_size += len(chunk)
                    fh.write(chunk)
            shutil.move(
                os.path.join(CACHE_PATH, 'pack_icon.png'),
                os.path.join(MODPACK_ZIP_CACHE, project_id, 'pack_icon.png'))
    else:
        InstanceInfo.is_done = True
        InstanceInfo.return_arg = ''
        return InstanceInfo.return_arg

    InstanceInfo.is_done = True
    InstanceInfo.return_arg = MODPACK_ZIP_CACHE + "/" + project_id + "/" + file_id + "/" + file_name
    return InstanceInfo.return_arg


def unpack_modpack_zip(src_dir, dst_folder_name, dst_dir):
    # FIXME: unpack.
    print(src_dir, dst_dir+dst_folder_name)
    unzip(src_dir, dst_dir+dst_folder_name)


def download_mods(instance_dir):
    InstanceInfo.is_done = False
    """
    :param instance_dir: The minecraft directory that contains the curse manifest.json file.
    :return: True on success, False on failure.
    """
    InstanceInfo().reset_dl()
    manifest_path = os.path.abspath(os.path.join(instance_dir, "manifest.json"))
    log.debug(str(manifest_path))
    manifest_json = load_json_file(manifest_path)

    if 'manifestType' not in manifest_json or not manifest_json['manifestType'] == 'minecraftModpack':
        log.error('Manifest missing manifestType key entry.')
        InstanceInfo.is_done = True
        return False
    elif 'manifestVersion' not in manifest_json or not manifest_json['manifestVersion'] == 1:
        log.error('Manifest missing manifestVersion key entry.')
        InstanceInfo.is_done = True
        return False
    elif 'overrides' not in manifest_json:
        log.error('Manifest missing overrides key entry.')
        InstanceInfo.is_done = True
        return False
    elif 'files' not in manifest_json:
        log.error('Manifest missing files key entries.')
        InstanceInfo.is_done = True
        return False

    override_path = Path(instance_dir, manifest_json['overrides'])
    minecraft_path = Path(instance_dir, "minecraft")
    mods_path = Path(minecraft_path, "mods")

    if override_path.exists():
        log.info("shutil.move: " + str(override_path) + str(minecraft_path))
        movetree_overwrite_dst(str(override_path), str(minecraft_path))
    if not minecraft_path.exists():
        log.debug("mkdir: " + str(minecraft_path))
        minecraft_path.mkdir()
    if not mods_path.exists():
        log.debug("mkdir: " + str(mods_path))
        mods_path.mkdir()

    InstanceInfo.total_progress = len(manifest_json['files'])

    log.info("Cached files are stored here:\n {0}\n".format(os.path.abspath(CACHE_PATH)))
    log.info("{0} files to download".format(InstanceInfo.total_progress))
    print("Cached files are stored here:\n {0}\n".format(os.path.abspath(CACHE_PATH)))
    print("{0} files to download".format(InstanceInfo.total_progress))

    # TODO: Split downloading into 2 parts.
    # 1st processes the manifest.
    # 2nd part does the downloading.
    # this allows editing the manifest contents passed to the download, making merging and removing in memory
    # instead of doing it directory in the original manifest. This should help with update portion.
    InstanceInfo.current_progress = 1
    for dependency in manifest_json['files']:
        if InstanceInfo.master_thread_running is False:
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
                print("[%d/%d] %s (in cache)" % (InstanceInfo.current_progress, InstanceInfo.total_progress, target_file.name))

                InstanceInfo.current_progress += 1

                # Cache access is successful,
                # Don't download the file
                continue

        # File is not cached and needs to be downloaded
        try:
            file_response = req_sess.get(
                "http://minecraft.curseforge.com/projects/{0}/files/{1}/download".format(
                    dependency['projectID'], dependency['fileID']), stream=True)
            requested_file_sess = req_sess.get(file_response.url, stream=True)

            remote_url = Path(requested_file_sess.url)
            file_name = unquote(remote_url.name).split('?')[0]  # If query data strip it and return just the file name.

            log.debug(str(requested_file_sess.status_code))
            log.debug(str(requested_file_sess.headers['content-type']))

            if (requested_file_sess.status_code == 404) or (file_name == "download"):
                print(str("[%d/%d] " + "Trying to resolve using alternate requesting.") % (InstanceInfo.current_progress, InstanceInfo.total_progress))

                # If curse website fails to provide correct url try Dries API list.
                # get the json from Dries:
                metabase = "https://cursemeta.dries007.net"
                metaurl = "%s/%s/%s.json" % (metabase, dependency['projectID'], dependency['fileID'])
                r = req_sess.get(metaurl)
                # TODO: catch 502 badgateway erros and continue with the rest of download?
                r.raise_for_status()
                main_json = r.json()
                if "code" in main_json:
                    print(str("[%d/%d] " + "ERROR FILE MISSING FROM SOURCE") % (InstanceInfo.current_progress, InstanceInfo.total_progress))
                    # TODO: READD: erred_mod_downloads.append(metaurl.url)
                    InstanceInfo.current_progress += 1
                    continue
                fileurl = main_json["DownloadURL"]
                file_name = main_json["FileNameOnDisk"]
                requested_file_sess = req_sess.get(fileurl, stream=True)

            InstanceInfo.file_size = int(requested_file_sess.headers.get('content-length', 0))
            if InstanceInfo.file_size:
                print(
                    str("[{0}/{1}] " + file_name + " (DL: " + get_human_readable(InstanceInfo.file_size) + ")").format(
                        InstanceInfo.current_progress, InstanceInfo.total_progress))
            else:
                print(str("[%d/%d] " + "MISSING FILE SIZE") % (InstanceInfo.current_progress, InstanceInfo.total_progress))
                InstanceInfo.file_size = 100

            if InstanceInfo.master_thread_running is False:
                log.error("Main Thread Dead, Joining it in the after life.")
                sys.exit()
            InstanceInfo.current_file_size = 0

            mod_part_path = os.path.join(CACHE_PATH, file_name + '.part')
            with open(mod_part_path, 'wb') as file_data:
                for chunk in requested_file_sess.iter_content(chunk_size=1024):
                    InstanceInfo.current_file_size += len(chunk)
                    file_data.write(chunk)
                    if InstanceInfo.master_thread_running is False:
                        file_data.close()
                        os.remove(mod_part_path)
                        log.error("Main Thread Dead, Joining it in the after life.")
                        sys.exit()

            # Try to add file to cache.
            if not dep_cache_dir.exists():
                log.debug("dep_cache.mkdir: " + str(dep_cache_dir))
                dep_cache_dir.mkdir(parents=True)

            log.debug("shutil.move: src: " + str(mod_part_path) +
                      " dst: " + str(dep_cache_dir / file_name))

            shutil.move(mod_part_path,
                        str(dep_cache_dir / file_name))

            log.debug("shutil.copyfile: src: " + str(dep_cache_dir / file_name) +
                      " dst: " + str(dep_cache_dir / file_name))

            shutil.copyfile(str(dep_cache_dir / file_name),
                            str(mods_path / file_name))  # Rename from temp to correct file name.

            InstanceInfo.current_progress += 1
            log.debug("InstanceInfo.current_progress: " + str(InstanceInfo.current_progress))

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
            InstanceInfo.is_done = True
            raise e
    log.info("Finished Processing All Mods Listed In Manifest.")
    print("Unpacking Complete")
    req_sess.close()
    InstanceInfo.is_done = True  # End of thread workload.


def initialize_program_environment():
    global installed_instances
    log.debug("Curse PDM: Checking/Initializing program environment")
    init_pdm_settings()
    create_dir_if_not_exist(MODPACK_ZIP_CACHE)
    create_dir_if_not_exist(MOD_CACHE)
    if os.path.exists(INSTALLED_INSTANCE_FILE):
        installed_instances[:] = load_json_file(INSTALLED_INSTANCE_FILE)["instances"]
    else:
        save_json_file({"instances": installed_instances}, INSTALLED_INSTANCE_FILE)
    # TODO: Program settings file. create if non-existing.
    # TODO: Add other steps that should be check at startup time.


# If this script is being run then start. else if being accessed don't try and run the gui stuffs.
if __name__ == '__main__':
    # print("This is not an executable.")
    pass

