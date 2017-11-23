import argparse
from tkinter import *
from tkinter import ttk, simpledialog
from tkinter import messagebox
from tkinter import filedialog
from downloader_core import *
import json
import os
import threading
import queue
import time
from pathlib import Path
from distutils.util import strtobool

'''
Author(s): TOLoneWolf

This contains the code used to make the graphical user interface.
'''


def center_window(toplevel):
    toplevel.update_idletasks()
    w = toplevel.winfo_screenwidth()
    h = toplevel.winfo_screenheight()
    size = tuple(int(_) for _ in toplevel.geometry().split('-')[0].split('+')[0].split('x'))
    x = int(w / 2 - size[0] / 2)
    y = int(h / 2 - size[1] / 2)
    toplevel.geometry("{0}x{1}+{2}+{3}".format(size[0], size[1], x, y))


# ----------------------------------------------------------------


class NewFromCurseUrl(Toplevel):
    def __init__(self):
        Toplevel.__init__(self)
        self.minsize(width=400, height=150)
        self.maxsize(width=400, height=150)
        self.resizable(FALSE, FALSE)
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.title("New From CurseForge URL")
        center_window(self)
        self.focus()
        self.grab_set()
        for column_index in range(2):
            self.columnconfigure(column_index, weight=1)
        for row_index in range(4):
            self.rowconfigure(row_index, weight=1)

        self.lbl_entry_url = ttk.Label(self, text="Enter MOD_PACK_NAME Here: \n"
                                                  "Example: https://minecraft.curseforge.com/projects/MOD_PACK_NAME")
        self.entry_mod_pack_name = ttk.Entry(self)
        self.lbl_feedback_info = ttk.Label(self, text="")
        # FIXME Remove this debug line below. 'self.entry_mod_pack_name.insert(END, "triarcraft")'
        # self.entry_mod_pack_name.insert(END, "project ozone 2 reloaded")
        # self.entry_mod_pack_name.insert(END, "btf beyond")
        self.entry_mod_pack_name.insert(END, "wyldbits")
        self.button_submit = ttk.Button(self, text="Enter", command=self.fetch_pack_from_url)
        self.button_cancel = ttk.Button(self, text="Cancel", command=self.close_window)
        # ---
        self.lbl_entry_url.grid(column=0, row=0, sticky='N', columnspan=2)
        self.entry_mod_pack_name.grid(column=0, row=1, sticky='EW', columnspan=2)
        self.entry_mod_pack_name.focus()
        self.lbl_feedback_info.grid(column=0, row=2, sticky='N', columnspan=2)
        self.button_submit.grid(column=0, row=3, sticky='NESW')
        self.button_cancel.grid(column=1, row=3, sticky='NESW')
        self.bind('<Return>', self.fetch_pack_from_url)

    def close_window(self):
        self.grab_release()
        self.destroy()

    def fetch_pack_from_url(self, *_):
        self.lbl_feedback_info.config(text="")
        # project_identifier: get user input, remove left and right white space, replace any remaining internal spaces \
        # with dash/negative char, and convert any uppercase letters to lower, and finally store it in var.
        project_identifier = self.entry_mod_pack_name.get()
        pack_version_response = get_modpack_version_list(project_identifier)
        if pack_version_response:  # If version list has contents.
            self.lbl_feedback_info.config(text="")
            VersionSelectionMenu(pack_version_response)
            self.close_window()
        else:
            self.lbl_feedback_info.config(text="Failed: Check ID / Name is correct and try again.")


class OpenPackZip:
    def __init__(self):
        file_path = filedialog.askopenfile(title="Select Modpack Zip",
                                           filetypes=(("Curse Packs", "*.zip"), ("All File Types", "*.*")))
        if file_path is not None:
            dst_folder_path = filedialog.askdirectory(title="Destination Directory For Modpack")
            if dst_folder_path is not None:
                file_path = os.path.normpath(file_path.name)
                file_path_norm = os.path.normpath(file_path)
                filename_and_ext = os.path.basename(file_path_norm)
                filename, extension = os.path.splitext(filename_and_ext)
                dst_dir = os.path.normpath(dst_folder_path + "\\" + filename)

                # print("zip path: " + file_path)
                # print("dst dir: " + dst_dir)
                if os.path.exists(dst_dir):
                    log.info("Folder With That Name Already Exists.")
                else:
                    unzip(file_path, dst_dir)


class SelectUnpackDirectory(Toplevel):
    # TODO: Select unpack directory.
    def __init__(self, src_zip):
        self.src_zip = src_zip
        Toplevel.__init__(self)
        self.minsize(width=600, height=300)
        self.maxsize(width=600, height=300)
        self.resizable(FALSE, FALSE)
        self.protocol("MW_DELETE_WINDOW", self.close_window)
        self.title("Select Directory")
        center_window(self)
        self.focus()
        self.grab_set()

        self.rdo_var_type = StringVar(value='custom')
        self.rdo_btn_default = ttk.Radiobutton(self, text="Custom (default)", variable=self.rdo_var_type, value='custom')
        self.rdo_btn_mmc = ttk.Radiobutton(self, text="MMC Instance", variable=self.rdo_var_type, value='mmc')
        self.rdo_btn_curse = ttk.Radiobutton(self, text="Curse Instance", variable=self.rdo_var_type, value='curse')
        # --- update check
        self.con_update_check = ttk.Frame(self)
        self.lbl_update_check = ttk.Label(self.con_update_check, text="Allow update Check: ")
        self.rdo_var_check_update = StringVar(value='True')
        self.rdo_btn_check_udate_true = ttk.Radiobutton(self.con_update_check, text="Enabled", variable=self.rdo_var_check_update, value="True")
        self.rdo_btn_check_udate_false = ttk.Radiobutton(self.con_update_check, text="Disabled", variable=self.rdo_var_check_update, value="False")
        self.lbl_update_check.grid(column=0, row=0, sticky='EW', columnspan=2)
        self.rdo_btn_check_udate_true.grid(column=0, row=1, sticky='W')
        self.rdo_btn_check_udate_false.grid(column=1, row=1, sticky='W')
        for column_index in range(1+1):
            self.con_update_check.columnconfigure(column_index, weight=1)
        for row_index in range(1+1):
            self.con_update_check.rowconfigure(row_index, weight=1)
        # --- auto update
        self.con_auto_update = ttk.Frame(self)
        self.lbl_auto_update = ttk.Label(self.con_auto_update, text="Allow Updating: ")
        self.rdo_var_auto_update = StringVar(value='True')
        self.rdo_btn_auto_update_true = ttk.Radiobutton(self.con_auto_update, text="Enabled", variable=self.rdo_var_auto_update, value="True")
        self.rdo_btn_auto_update_false = ttk.Radiobutton(self.con_auto_update, text="Disabled", variable=self.rdo_var_auto_update, value="False")
        self.lbl_auto_update.grid(column=0, row=0, sticky='EW', columnspan=2)
        self.rdo_btn_auto_update_true.grid(column=0, row=1, sticky='W')
        self.rdo_btn_auto_update_false.grid(column=1, row=1, sticky='W')
        for column_index in range(1+1):
            self.con_auto_update.columnconfigure(column_index, weight=1)
        for row_index in range(1+1):
            self.con_auto_update.rowconfigure(row_index, weight=1)
        # ---
        self.lbl_entry_name = ttk.Label(self, text="Enter Instance Name: ")
        self.entry_instance_name = ttk.Entry(self)
        self.lbl_dst_folder = ttk.Label(self, text="Select Destination Folder: ")
        self.btn_dst_folder = ttk.Button(self, text="Browse", command=self.browse_folder)
        self.entry_directory = ttk.Entry(self)
        self.btn_submit = ttk.Button(self, text="Unpack", command=self.process)
        self.btn_cancel = ttk.Button(self, text="Cancel", command=self.close_window)
        # ---
        self.rdo_btn_default.grid(column=0, row=0, sticky="NW")
        self.rdo_btn_mmc.grid(column=1, row=0, sticky='NW')
        self.rdo_btn_curse.grid(column=2, row=0, sticky='NW')
        self.con_update_check.grid(column=0, row=1, sticky='W')
        self.con_auto_update.grid(column=1, row=1, sticky='W')
        self.lbl_entry_name.grid(column=0, row=2, sticky='NESW', columnspan=2)
        self.entry_instance_name.grid(column=0, row=3, sticky='EW', columnspan=1)
        self.lbl_dst_folder.grid(column=0, row=4, sticky='NESW')
        self.btn_dst_folder.grid(column=2, row=4, sticky='NESW')
        self.entry_directory.grid(column=0, row=5, sticky='EW', columnspan=3)
        self.btn_submit.grid(column=0, row=6, sticky='NESW')
        self.btn_cancel.grid(column=2, row=6, sticky='NESW')
        for column_index in range(2+1):
            self.columnconfigure(column_index, weight=1)
        for row_index in range(6+1):
            self.rowconfigure(row_index, weight=1)

    def close_window(self):
        self.grab_release()
        self.destroy()

    def browse_folder(self):
        if self.rdo_var_type.get() == "custom":
            path_dst_dir = filedialog.askdirectory(
                title="Select Destination Folder",
                initialdir=program_settings["custom"])
        elif self.rdo_var_type.get() == "mmc":
            path_dst_dir = filedialog.askdirectory(
                title="Select Destination Folder",
                initialdir=os.path.join(program_settings["MultiMC"], 'instances'))
        elif self.rdo_var_type.get() == "curse":
            path_dst_dir = filedialog.askdirectory(
                title="Select Destination Folder",
                initialdir=program_settings["curse_client"])
        else:
            path_dst_dir = filedialog.askdirectory(title="Select Destination Folder")
        if not path_dst_dir == "":
            self.entry_directory.delete(0, END)
            self.entry_directory.insert(END, path_dst_dir)

    def process(self):
        if self.entry_directory.get():
            if self.entry_instance_name.get:
                InstanceInfo.instance_name = self.entry_instance_name.get()
                InstanceInfo.install_type = self.rdo_var_type.get()
                InstanceInfo.update_check = bool(strtobool(self.rdo_var_check_update.get()))
                InstanceInfo.update_automatic = bool(strtobool(self.rdo_var_auto_update.get()))
                InstanceInfo.instance_path = os.path.normpath(os.path.join(self.entry_directory.get(), self.entry_instance_name.get()))
                log.debug("unpack process: " + str(InstanceInfo.instance_path))
                unzip(self.src_zip, InstanceInfo.instance_path)
                save_instance_settings(InstanceInfo.instance_path)
                if os.path.exists(InstanceInfo.instance_path.join("manifest.json")):
                    if not os.path.exists(InstanceInfo.instance_path.join(PDM_INSTANCE_FOLDER)):
                        os.mkdir(InstanceInfo.instance_path.join(PDM_INSTANCE_FOLDER))
                    shutil.copy(InstanceInfo.instance_path.join('manifest.json'), os.path.join(InstanceInfo.instance_path, PDM_INSTANCE_FOLDER, "manifest.json"))
                work_thread = threading.Thread(target=download_mods, args=(InstanceInfo.instance_path,))
                work_thread.start()
                self.close_window()
                InstanceInfo.is_done = False
                while not InstanceInfo.is_done:
                    time.sleep(0.2)
                    if InstanceInfo.file_size:
                        percent = round((int(InstanceInfo.current_file_size) / int(InstanceInfo.file_size)) * 100, 0)
                        print(str(percent) + " P: " + str(get_human_readable(InstanceInfo.current_file_size)) + "/" + str(get_human_readable(InstanceInfo.file_size)))

                # Copy user saved settings and mods back into the instance.
                if InstanceInfo.merge_custom:
                    if os.path.exists(
                            os.path.normpath(os.path.join(InstanceInfo.instance_path, PDM_INSTANCE_FOLDER, 'config'))):
                        copytree_overwrite_dst(
                            os.path.normpath(os.path.join(InstanceInfo.instance_path, PDM_INSTANCE_FOLDER, 'config')),
                            os.path.normpath(os.path.join(InstanceInfo.instance_path,'minecraft', 'config')))

                    if os.path.exists(
                            os.path.normpath(os.path.join(InstanceInfo.instance_path, PDM_INSTANCE_FOLDER, 'mods'))):
                        copytree_overwrite_dst(
                            os.path.normpath(os.path.join(InstanceInfo.instance_path, PDM_INSTANCE_FOLDER, 'mods')),
                            os.path.normpath(os.path.join(InstanceInfo.instance_path, 'minecraft', 'mods')))

                if InstanceInfo.install_type == 'curse':
                    movetree_overwrite_dst(
                        os.path.join(InstanceInfo.instance_path, 'minecraft'),
                        InstanceInfo.instance_path)
                if InstanceInfo.install_type == 'mmc':
                    if not os.path.exists(
                            os.path.join(
                                program_settings['MultiMC'], 'icons',
                                InstanceInfo.project_name + 'icon.png')):
                        shutil.copy(
                            os.path.join(MODPACK_ZIP_CACHE, InstanceInfo.project_id, 'pack_icon.png'),
                            os.path.join(
                                program_settings['MultiMC'], 'icons',
                                InstanceInfo.project_name + '_icon.png'))

                    mmc_cfg_contents = mmc_read_cfg(InstanceInfo.instance_path)
                    if not mmc_write_cfg(mmc_cfg_contents, InstanceInfo.instance_path):
                        raise RuntimeError("MultiMC settings file save failed to execute correctly.")

                save_instance_settings(InstanceInfo.instance_path)
                if not {"location": InstanceInfo.instance_path} in installed_instances:
                    installed_instances.append({"location": InstanceInfo.instance_path})
                    save_json_file({"instances": installed_instances}, INSTALLED_INSTANCE_FILE)

                print("work_thread: manager.downloads_mods 'isDone' detected.")
                print("Manager Done Downloading")


class VersionSelectionMenu(Toplevel):
    def __init__(self, pack_info):
        if pack_info:  # If list is not empty.
            Toplevel.__init__(self)
            self.minsize(width=400, height=300)
            self.maxsize(width=400, height=300)
            self.resizable(FALSE, FALSE)
            self.protocol("WM_DELETE_WINDOW", self.close_window)
            self.title("Select Mod Pack Version")
            center_window(self)
            self.focus()
            self.grab_set()
            # --- Variables and stuff.
            self.pack_source = pack_info[0]
            self.project_id = pack_info[1]
            self.project_name = pack_info[2]
            self.pack_version_list = pack_info[3]
            self.current_version_list = []

            # --- GUI objects.
            self.lbl_select_version = ttk.Label(self, text="Select the desired version of the pack to install.")
            self.lbl_project_id = ttk.Label(self, text="Project ID: %s\nProject Name: %s" % (self.project_id, self.project_name))
            self.lbl_combo_release_type = ttk.Label(self, text="Release Types: ")
            self.combo_release_type = ttk.Combobox(self, state='readonly')
            self.combo_release_type.bind("<<ComboboxSelected>>", self.combo_release_type_update)
            # --- container object.
            self.listbox_version_container = ttk.Frame(self)
            self.listbox_version = Listbox(self.listbox_version_container, height=12)
            # dotbox, none, or underline
            self.listbox_version.config(activestyle="none")
            # FIXME: Remove the following line and self.update_selected method. No longer needed?
            # self.listbox_version.bind('<<ListboxSelect>>', self.update_selected)
            self.scroll_listbox_version = ttk.Scrollbar(self.listbox_version_container, command=self.listbox_version.yview)
            # --- config container contents.
            self.listbox_version.grid(column=0, row=0, sticky='NESW', columnspan=1)
            self.listbox_version.focus()
            self.scroll_listbox_version.grid(column=1, row=0, sticky='NESW', columnspan=1)
            self.listbox_version['yscrollcommand'] = self.scroll_listbox_version.set
            # ---
            self.listbox_version_container.columnconfigure(0, weight=1)
            self.listbox_version_container.columnconfigure(1, weight=0)
            self.listbox_version_container.rowconfigure(0, weight=1)
            # --- GUI objects.
            self.button_submit = ttk.Button(self, text="Download Selected", command=self.download_selected_pack_version)
            self.button_submit['state'] = DISABLED  # disallow now and allow later if list is populated.
            self.button_cancel = ttk.Button(self, text="Cancel", command=self.close_window)
            # -- GUI grid config.
            self.lbl_select_version.grid(column=0, row=0, sticky='N', columnspan=2)
            self.lbl_project_id.grid(column=0, row=1, sticky='', columnspan=2)
            self.lbl_combo_release_type.grid(column=0, row=2, sticky='E')
            self.combo_release_type.grid(column=1, row=2, sticky='W')
            self.listbox_version_container.grid(column=0, row=3, sticky='NESW', columnspan=2)
            self.button_submit.grid(column=0, row=4, sticky='NESW')
            self.button_cancel.grid(column=1, row=4, sticky='NESW')

            for column_index in range(1+1):
                self.columnconfigure(column_index, weight=1)
            for row_index in range(4+1):
                self.rowconfigure(row_index, weight=1)

            # --- Logic
            self.combo_release_type['values'] = ('Release', 'Release + Beta', 'Release + Beta + Alpha',)
            self.combo_release_type.set(self.combo_release_type['values'][0])
            self.combo_release_type_update()
        else:  # else if pack_info is empty
            log.error("pack_info list is empty! This should not happen!")

    # TODO: Clean up the list_only_these_versions if possible.
    def combo_release_type_update(self, *_):
        log.debug("combobox: " + str(self.combo_release_type.get()))
        display_list = []
        self.current_version_list = []  # Reset list every time.
        list_only_these_versions = self.combo_release_type.get()
        for listElement in self.pack_version_list:
            if list_only_these_versions == "Release":
                if listElement[0] == 1:
                    self.current_version_list.append(listElement[1])
                    display_list.append('Release' + ' - ' + listElement[1] + ' - ' + listElement[2])

            elif list_only_these_versions == "Release + Beta":
                if listElement[0] == 1:
                    self.current_version_list.append(listElement[1])
                    display_list.append('Release' + ' - ' + listElement[1] + ' - ' + listElement[2])
                elif listElement[0] == 2:
                    self.current_version_list.append(listElement[1])
                    display_list.append('Beta' + ' - ' + listElement[1] + ' - ' + listElement[2])

            elif list_only_these_versions == "Release + Beta + Alpha":
                if listElement[0] == 1:
                    self.current_version_list.append(listElement[1])
                    display_list.append('Release' + ' - ' + listElement[1] + ' - ' + listElement[2])
                elif listElement[0] == 2:
                    self.current_version_list.append(listElement[1])
                    display_list.append('Beta' + ' - ' + listElement[1] + ' - ' + listElement[2])
                elif listElement[0] == 3:
                    self.current_version_list.append(listElement[1])
                    display_list.append('Alpha' + ' - ' + listElement[1] + ' - ' + listElement[2])

        self.listbox_version.delete(0, END)
        for listElement in display_list:
            self.listbox_version.insert(END, listElement)
        self.listbox_version.selection_set(0)
        self.listbox_version.activate(0)
        self.listbox_version.see(0)
        if not self.current_version_list:
            self.button_submit['state'] = DISABLED  # Something failed better not allow them to continue.
        else:
            self.button_submit['state'] = NORMAL  # Something failed better not allow them to continue.
        log.debug("Version Current Selection: " + str(self.listbox_version.curselection()))

    # FIXME: Remove this as it is no longer used??
    # def update_selected(self, *_):
    #     log.debug("Debug: current selection: " + str(self.listbox_version.curselection()[0]))

    def download_selected_pack_version(self):
        print("download_selected_pack_version")
        print(self.project_name, self.current_version_list[self.listbox_version.curselection()[0]])
        src_zip = download_modpack_zip(
            pack_source=self.pack_source,
            project_id=self.project_id,
            project_name=self.project_name,
            file_id=self.current_version_list[self.listbox_version.curselection()[0]])
        print("work_thread: manager.download_modpack_zip 'isDone' detected.")
        print("Manager Done Downloading")
        if src_zip:
            local_type = self.combo_release_type.get()
            if local_type == "Release":
                InstanceInfo.update_type = 1
            elif local_type == "Release + Beta":
                InstanceInfo.update_type = 2
            elif local_type == "Release + Beta + Alpha":
                InstanceInfo.update_type = 3

            InstanceInfo.source = self.pack_source
            InstanceInfo.project_id = self.project_id
            InstanceInfo.project_name = self.project_name
            InstanceInfo.version_id = self.current_version_list[self.listbox_version.curselection()[0]]
            SelectUnpackDirectory(src_zip)
        else:
            log.error("src_zip returned nothing!")

        # # TODO: Probably use ques to get threads working right.
        # work_thread = threading.Thread(target=manager.download_modpack_zip, args=(
            # pack_source=self.pack_source,
            # project_id=self.project_id,
            # project_name=self.project_name,
            # file_id=self.current_version_list[3][self.listbox_version.curselection()[0]][1])
        # work_thread.start()
        # self.close_window()
        # while not manager.is_done:
        #     time.sleep(0.05)
        #     if manager.file_size:
        #         percent = round((int(manager.current_file_size) / int(manager.file_size)) * 100, 0)
        #         print(str(percent) + " P: " + str(get_human_readable(manager.current_file_size)) + "/" + str(get_human_readable(manager.file_size)))
        #     else:
        #         print("unknown size. Currently downloaded: " + get_human_readable(manager.current_file_size))
        # print("work_thread: manager.download_modpack_zip 'isDone' detected.")
        # print("Manager Done Downloading")
        # manager.reset_download_status()
        # SelectUnpackDirectory(manager.return_arg)
        self.close_window()

    def close_window(self):
        self.grab_release()
        self.destroy()


class CopyInstance:
    def __init__(self):
        # src, dst = Path()
        path_src_dir = filedialog.askdirectory(title="Select Source Minecraft Folder")
        if not path_src_dir == "":
            print(path_src_dir)
            path_dst_dir = filedialog.askdirectory(title="Select Destination For Copy")
            if not path_dst_dir == "":
                print(path_dst_dir)
                # copy_instance(path_src_dir, path_dst_dir)


class NewInstanceWindow(Toplevel):
    def __init__(self):
        Toplevel.__init__(self)
        self.minsize(width=600, height=400)
        self.resizable(FALSE, FALSE)
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.title("New Instance")
        center_window(self)
        self.focus()
        self.grab_set()

        # --- Layout
        button_new_from_url = ttk.Button(self, text="New From Curse URL", command=self.new_from_url)
        button_new_from_zip = ttk.Button(self, text="New From Curse Pack.zip", command=self.open_pack_zip)
        button_new_from_manifest = ttk.Button(self, text="New From Curse Manifest.json", command=self.pack_from_manifest)
        button_new_from_existing_instance = ttk.Button(self, text="Copy Existing Instance", command=self.copy_instance)
        button_close_window = ttk.Button(self, text="Close", command=self.close_window)
        # FIXME: When implemented correctly remove the following disabled states.
        button_new_from_zip.config(state='disabled')
        button_new_from_manifest.config(state='disabled')
        button_new_from_existing_instance.config(state='disabled')
        # ---
        button_new_from_url.grid(column=0, row=0, sticky='NESW')
        button_new_from_zip.grid(column=0, row=1, sticky='NESW')
        button_new_from_manifest.grid(column=0, row=2, sticky='NESW')
        button_new_from_existing_instance.grid(column=0, row=3, sticky='NESW')
        button_close_window.grid(column=0, row=4, sticky='NESW')

        self.columnconfigure(0, weight=1)
        for row_index in range(4 + 1):
            self.rowconfigure(row_index, weight=1)
        # --- Logic

    def close_window(self):
        self.grab_release()
        self.destroy()

    def new_from_url(self):
        self.close_window()
        NewFromCurseUrl()

    def open_pack_zip(self):
        self.close_window()
        OpenPackZip()

    def pack_from_manifest(self):
        self.close_window()
        # TODO: Create from manifest.
        print("pack_from_manifest: nothing here yet....")
        pass

    def copy_instance(self):
        self.close_window()
        CopyInstance()


class EditInstance(Toplevel):
    def __init__(self):
        Toplevel.__init__(self)
        self.minsize(width=700, height=300)
        self.maxsize(width=700, height=300)
        self.resizable(FALSE, FALSE)
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.title("Edit Instance")
        center_window(self)
        self.focus()
        self.grab_set()

        self.local_display_list = []
        # --- Container
        self.con_listbox = ttk.Frame(self)
        self.listbox_instances = Listbox(self.con_listbox, height=12)
        self.listbox_instances.config(activestyle="none")
        self.scroll_listbox_instances = ttk.Scrollbar(self.con_listbox, command=self.listbox_instances.yview)
        self.listbox_instances.grid(column=0, row=0, sticky='NESW')
        self.scroll_listbox_instances.grid(column=1, row=0, sticky='NS')
        self.listbox_instances['yscrollcommand'] = self.scroll_listbox_instances.set
        self.listbox_instances.focus()
        self.listbox_instances.bind('<<ListboxSelect>>', self.instance_selected)
        for column_index in range(0 + 1):
            self.con_listbox.columnconfigure(column_index, weight=1)
        for row_index in range(0 + 1):
            self.con_listbox.rowconfigure(row_index, weight=1)
        # --- Container Grid Layout
        self.btn_add_existing = ttk.Button(self, text="Add Existing Instance To PDM", command=self.add_existing)
        self.btn_manually_update = ttk.Button(self, text="Manually Update", command=self.manually_update)
        self.btn_update_instance = ttk.Button(self, text="Update Instance", command=self.update_instance)
        self.btn_check_instance_update = ttk.Button(self, text="Check Instance for update", command=self.check_instance_update)
        self.btn_remove_refernce = ttk.Button(self, text="Remove From PDM", command=self.remove_from_manager)
        self.btn_delete = ttk.Button(self, text="Delete Instance", command=self.delete)
        self.btn_close = ttk.Button(self, text="Close", command=self.close_window)
        # FIXME: Remove these disable lines when functions actually do something.
        self.btn_add_existing.config(state='disabled')
        self.btn_manually_update.config(state='disabled')
        self.btn_update_instance.config(state='disabled')
        self.btn_check_instance_update.config(state='disabled')
        # --- Grid Layout
        self.con_listbox.grid(column=0, row=0, sticky='NESW', columnspan=2, rowspan=7)
        self.btn_add_existing.grid(column=2, row=0, sticky='NESW')
        self.btn_manually_update.grid(column=2, row=1, sticky='NESW')
        self.btn_update_instance.grid(column=2, row=2, sticky='NESW')
        self.btn_check_instance_update.grid(column=2, row=3, sticky='NESW')
        self.btn_remove_refernce.grid(column=2, row=4, sticky='NESW')
        self.btn_delete.grid(column=2, row=5, sticky='NESW')
        self.btn_close.grid(column=2, row=6, sticky='NESW')

        for column_index in range(2 + 1):
            self.columnconfigure(column_index, weight=1)
        for row_index in range(6 + 1):
            self.rowconfigure(row_index, weight=1)
        self.list_update()
        self.listbox_instances.selection_set(0)
        self.listbox_instances.activate(0)
        self.listbox_instances.see(0)

    def close_window(self):
        self.grab_release()
        self.destroy()

    def list_update(self):
        self.local_display_list[:] = []  # Reset to blank.
        log.debug("list_update")
        self.listbox_instances.delete(0, END)
        for instance in installed_instances:
            if os.path.exists(instance['location']):
                load_instance_settings(instance['location'])
                self.local_display_list.append(instance)
                log.debug(InstanceInfo.instance_name + " - " + InstanceInfo.instance_path)
                self.listbox_instances.insert(END, InstanceInfo.instance_name + " - " + InstanceInfo.instance_path)
        installed_instances[:] = self.local_display_list  # FIXME: Do better cleanup of bad paths.

    def instance_selected(self, *_):
        log.debug("instance_selected")
        if self.listbox_instances.curselection():
            log.debug(self.listbox_instances.curselection()[0])
            log.debug(installed_instances[self.listbox_instances.curselection()[0]])

    def add_existing(self):
        log.debug("add_existing")
        # TODO: Add path if existing minecraft directory.
        # initialdir=program_settings["custom"]
        path_dst_dir = filedialog.askdirectory(
            title="Select Minecraft Instance Folder")
        if path_dst_dir:
            if os.path.exists(path_dst_dir):
                if os.path.exists(os.path.join(path_dst_dir, 'manifest.json')):
                    if os.path.exists(os.path.join(path_dst_dir, 'minecraft')):
                        log.debug("default or MultiMC")
                    elif os.path.exists(os.path.join(path_dst_dir, 'mods')):
                        log.debug("curse/twitch client")
                    # Ask for modpack name. search for it.
                    # Ask what install type it is.
                    # Ask file id (aka version) from list fetched from the web.
                    # Ask if update check, auto update.
                else:
                    log.debug("manifest.json is missing from directory, invalid instance.")
            else:
                raise IOError("I Got An Invalid Directory Path! HELP!")

    def manually_update(self):
        log.debug("manually_update")
        # TODO: Basically copy create new instance setup.
        if self.listbox_instances.curselection():
            log.debug(installed_instances[self.listbox_instances.curselection()[0]])

    def update_instance(self):
        log.debug("update_instance")
        # TODO: updates instance if one is newer and ignores auto update setting off.
        if self.listbox_instances.curselection():
            log.debug(installed_instances[self.listbox_instances.curselection()[0]])

    def check_instance_update(self):
        log.debug("check_instance_update")
        # TODO: Just checks if there is an update for this instance.
        if self.listbox_instances.curselection():
            log.debug(installed_instances[self.listbox_instances.curselection()[0]])

    def remove_from_manager(self):
        log.debug("remove_from_manager")
        # TODO: Remove instance from manager.
        if self.listbox_instances.curselection():
            log.debug(installed_instances[self.listbox_instances.curselection()[0]])
            del installed_instances[self.listbox_instances.curselection()[0]]
            print(installed_instances)
            self.list_update()
            save_json_file({"instances": installed_instances}, INSTALLED_INSTANCE_FILE)

    def delete(self):
        log.debug("delete")
        # TODO: Remove instance completely.
        if self.listbox_instances.curselection():
            log.debug(installed_instances[self.listbox_instances.curselection()[0]])
            if os.path.exists(installed_instances[self.listbox_instances.curselection()[0]]['location']):
                shutil.rmtree(installed_instances[self.listbox_instances.curselection()[0]]['location'], onerror=shutil_rmtree_on_rm_error)
                del installed_instances[self.listbox_instances.curselection()[0]]
                print(installed_instances)
                self.list_update()
                save_json_file({"instances": installed_instances}, INSTALLED_INSTANCE_FILE)


class ProgramSettings(Toplevel):
    def __init__(self):
        Toplevel.__init__(self)
        self.minsize(width=600, height=300)
        self.maxsize(width=600, height=300)
        self.resizable(FALSE, FALSE)
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.title("Program Settings")
        center_window(self)
        self.focus()
        self.grab_set()

        self.custom_instance_path = ''
        self.multimc_instance_path = ''
        self.curse_client_instance_path = ''
        self.vanilla_instance_path = ''

        self.lbl_custom_path = ttk.Label(self, text="Custom Instance Directory Path: ("
                                                    "Ex: C:\..\my games\minecraft\instances)")
        self.ent_custom_path = ttk.Entry(self)
        self.lbl_multimc_path = ttk.Label(self, text="MultiMC Directory Path: ("
                                                     "Ex: C:\..\..\MultiMC 5)")
        self.ent_multimc_path = ttk.Entry(self)
        self.lbl_curse_path = ttk.Label(self, text="Curse(Twitch) Client Instance Directory Path: ")
        self.ent_curse_path = ttk.Entry(self)
        self.lbl_vanilla_path = ttk.Label(self, text="Vanilla Instance Directory Path: ")
        self.ent_vanilla_path = ttk.Entry(self)

        self.btn_save = ttk.Button(self, text="Save", command=self.save)
        self.btn_apply = ttk.Button(self, text="Apply", command=self.apply)
        self.btn_reset = ttk.Button(self, text="Reset", command=self.reset)
        self.btn_close = ttk.Button(self, text="Close", command=self.close_window)
        # --- Grid Layout
        self.lbl_custom_path.grid(column=0, row=0, sticky='W')
        self.ent_custom_path.grid(column=0, row=1, sticky='EW', columnspan=3)
        self.lbl_multimc_path.grid(column=0, row=2, sticky='W')
        self.ent_multimc_path.grid(column=0, row=3, sticky='EW', columnspan=3)
        self.lbl_curse_path.grid(column=0, row=4, sticky='W')
        self.ent_curse_path.grid(column=0, row=5, sticky='EW', columnspan=3)
        self.lbl_vanilla_path.grid(column=0, row=6, sticky='W')
        self.ent_vanilla_path.grid(column=0, row=7, sticky='EW', columnspan=3)

        self.btn_save.grid(column=0, row=15, sticky='NESW')
        self.btn_apply.grid(column=1, row=15, sticky='NESW')
        self.btn_reset.grid(column=2, row=15, sticky='NESW')
        self.btn_close.grid(column=3, row=15, sticky='NESW')

        for column_index in range(3+1):
            self.columnconfigure(column_index, weight=1)
        for row_index in range(15+1):
            self.rowconfigure(row_index, weight=1)

        self.reset()

    def close_window(self):
        self.grab_release()
        self.destroy()

    def reset(self):
        self.ent_custom_path.delete(0, END)
        self.ent_custom_path.insert(0, program_settings["custom"])
        self.ent_multimc_path.delete(0, END)
        self.ent_multimc_path.insert(0,program_settings["MultiMC"])
        self.ent_curse_path.delete(0, END)
        self.ent_curse_path.insert(0, program_settings["curse_client"])
        self.ent_vanilla_path.delete(0, END)
        self.ent_vanilla_path.insert(0, program_settings["Vanilla_Client"])

    def apply(self):
        program_settings['custom'] = os.path.normpath(self.ent_custom_path.get())
        program_settings['MultiMC'] = os.path.normpath(self.ent_multimc_path.get())
        program_settings['curse_client'] = os.path.normpath(self.ent_curse_path.get())
        program_settings["Vanilla_Client"] = os.path.normpath(self.ent_vanilla_path.get())

    def save(self):
        self.apply()
        save_program_settings()


class RootWindow(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.title(PROGRAM_NAME + ' v' + PROGRAM_VERSION_NUMBER + " " + PROGRAM_VERSION_BUILD)
        self.minsize(width=600, height=300)
        center_window(self)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.logWindow = Text(self, state="disabled", width=40)
        self.logWindowScrollbar = Scrollbar(self, command=self.logWindow.yview)
        self.logWindow['yscrollcommand'] = self.logWindowScrollbar.set
        self.menu_buttons = ttk.Frame(self)
        self.button_create_new_instance = ttk.Button(self.menu_buttons, text="New Instance", command=NewInstanceWindow)
        self.checkInstanceUpdate = ttk.Button(self.menu_buttons, text="Check For Instance Updates", command=self.check_instance_update)
        self.bEditInstance = ttk.Button(self.menu_buttons, text="Edit Instance", command=EditInstance)
        self.bProgramSettings = ttk.Button(self.menu_buttons, text="Program Settings", command=ProgramSettings)
        self.selfUpdateCheck = ttk.Button(self.menu_buttons, text="Self Update",
                                          command=lambda: self.set_output("No Updates :P"))
        self.selfUpdateCheck.config(state='disabled') # FIXME: Remove when implemented self update.
        self.closeProgram = ttk.Button(self.menu_buttons, text="Exit Program", command=self.close_window)
        # ---
        self.logWindow.grid(column=0, row=0, sticky='NESW')
        self.logWindowScrollbar.grid(column=1, row=0, sticky='NESW')
        self.menu_buttons.grid(column=3, row=0, sticky='NESW')
        # ---
        self.button_create_new_instance.grid(column=0, row=0, sticky='NESW')
        self.checkInstanceUpdate.grid(column=0, row=1, sticky='NESW')
        self.bEditInstance.grid(column=0, row=2, sticky='NESW')
        self.bProgramSettings.grid(column=0, row=3, sticky='NESW')
        self.selfUpdateCheck.grid(column=0, row=4, sticky='NESW')
        self.closeProgram.grid(column=0, row=5, sticky='NESW')

        self.columnconfigure(0, weight=4)
        self.columnconfigure(2, weight=0)
        self.columnconfigure(3, weight=1)
        self.rowconfigure(0, weight=1)

        for row_index in range(6):
            self.menu_buttons.rowconfigure(row_index, weight=1)
        self.menu_buttons.columnconfigure(0, weight=1)
        # root.resizable(FALSE, FALSE)

        self.set_output("This")
        self.set_output("a")
        self.set_output("log\n testing log \n\n\n\n\n\n\n\n\n\n\n\n more test log \n\n\n\n\n\n\n\n even more test log")
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.mainloop()

    def set_output(self, message):
        self.logWindow['state'] = "normal"
        self.logWindow.insert("end", message + "\n")
        self.logWindow['state'] = "disabled"
        self.logWindow.see(END)

    def close_window(self):
        self.destroy()

    def check_instance_update(self):
        instance_update_check()


# If this script is being run then start. else if being accessed don't try and run the gui stuffs.
if __name__ == '__main__':
    # needs to be inside a Tk() master window to display the askstring.
    # ask = simpledialog.askstring("test", "yo")
    initialize_program_environment()
    print("Cached files are stored here:\n %s\n" % os.path.abspath(CACHE_PATH))
    RootWindow()
    InstanceInfo.master_thread_running = False  # FIXME: used to tell download thread to close. Redo the whole threading thing.
