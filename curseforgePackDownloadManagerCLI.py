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

    InstanceInfo.source, InstanceInfo.project_id, InstanceInfo.project_name, \
        InstanceInfo.version_ids = get_modpack_version_list('ftb beyond')

    print(InstanceInfo.source)
    print(InstanceInfo.project_id)
    print(InstanceInfo.project_name)
    print(InstanceInfo.version_ids)
    print(InstanceInfo.version_ids[0][1])

    src_zip = download_modpack_zip(
        InstanceInfo.source, InstanceInfo.project_id, InstanceInfo.project_name, InstanceInfo.version_ids[0][1])

    print(src_zip)
    # instance_update_check(manager)
