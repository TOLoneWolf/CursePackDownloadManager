import os
from downloader_core import *

'''
Author(s): TOLoneWolf

This contains the code used to make the CLI interface.
'''


if __name__ == '__main__':
    pass
    initialize_program_environment()
    # Test some instance update code.

    load_instance_settings("instances\\test4")

    InstanceInfo.source, InstanceInfo.project_id, InstanceInfo.project_name, \
        InstanceInfo.list_version_id = get_modpack_version_list('ftb beyond')
    # print(InstanceInfo.list_version_id)
    InstanceInfo.update_version_id = 0
    InstanceInfo.update_type = "R"
    if InstanceInfo.source:
        # print(InstanceInfo.source)
        # print(InstanceInfo.project_id)
        # print(InstanceInfo.project_name)
        # print(InstanceInfo.list_version_id)
        # print(InstanceInfo.list_version_id[0][1])
        for versions in InstanceInfo.list_version_id:
            if InstanceInfo.update_type == "All":
                if int(versions[1]) > int(InstanceInfo.version_id):
                    InstanceInfo.update_version_id = versions[1]
                    break
            elif versions[0] == InstanceInfo.update_type:
                if int(versions[1]) > int(InstanceInfo.version_id):
                    InstanceInfo.update_version_id = versions[1]
                    break
        src_zip = download_modpack_zip(
            InstanceInfo.source, InstanceInfo.project_id, InstanceInfo.project_name, InstanceInfo.update_version_id)

        print(src_zip)

    # instance_update_check(manager)

    # load_instance_settings("instances\\test4")
    # InstanceInfo.instance_name = 'Jo Joes 5'
    # save_instance_settings("instances\\test4")
