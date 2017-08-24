from tkinter import *
from tkinter import ttk, simpledialog
from tkinter import messagebox
from tkinter import filedialog
from downloader_core import *
import json
import os
import threading
import time
from pathlib import Path


'''
Author(s): TOLoneWolf
License: in license.txt

This contains the code used to make the GUI interface.
'''


instanceData = {}
instanceListData = ["first", "second", "third", "forth", "sixth", "Seventh", "Eighth", "ninth"]


def center(toplevel):
    toplevel.update_idletasks()
    w = toplevel.winfo_screenwidth()
    h = toplevel.winfo_screenheight()
    size = tuple(int(_) for _ in toplevel.geometry().split('-')[0].split('+')[0].split('x'))
    x = w / 2 - size[0] / 2
    y = h / 2 - size[1] / 2
    size = (size[0], size[1], x, y)
    toplevel.geometry("%dx%d+%d+%d" % size)


# ----------------------------------------------------------------


class NewFromCurseUrl(Toplevel):
    def __init__(self):
        Toplevel.__init__(self)
        self.minsize(width=400, height=75)
        self.maxsize(width=400, height=75)
        self.resizable(FALSE, FALSE)
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.title("New From CurseForge URL")
        center(self)
        self.focus()
        self.grab_set()
        for column_index in range(2):
            self.columnconfigure(column_index, weight=1)
        for row_index in range(3):
            self.rowconfigure(row_index, weight=1)

        self.lbl_entry_url = ttk.Label(self, text="Enter MOD_PACK_NAME Here: \n"
                                                  "Example: https://minecraft.curseforge.com/projects/MOD_PACK_NAME")
        self.entry_mod_pack_name = ttk.Entry(self)
        self.button_submit = ttk.Button(self, text="Enter", command=self.fetch_pack_from_url)
        self.button_cancel = ttk.Button(self, text="Cancel", command=self.close_window)
        # ---
        self.lbl_entry_url.grid(column=0, row=0, sticky='N', columnspan=2)
        self.entry_mod_pack_name.grid(column=0, row=1, sticky='EW', columnspan=2)
        self.entry_mod_pack_name.focus()
        self.button_submit.grid(column=0, row=2, sticky='NESW')
        self.button_cancel.grid(column=1, row=2, sticky='NESW')
        self.bind('<Return>', self.fetch_pack_from_url)

    def close_window(self):
        self.grab_release()
        self.destroy()

    def fetch_pack_from_url(self, event=None):
        manager = CurseDownloader()
        project_identifier = self.entry_mod_pack_name.get()
        pack_version_response = manager.retrieve_pack_version_lists(project_identifier)
        if pack_version_response is None:
            messagebox.showerror(
                "No Pack Found By Name/ID", "Mod pack name/ID returned no versions."
                "\nPlease make sure you typed it exactly as what is shown in your web browser.")
            self.close_window()
        else:
            project_id = pack_version_response[0]
            project_name = pack_version_response[1]
            bare_pack_version_list = pack_version_response[2]

            # TODO Implement Version Selection And Then Download Selected Version.
            release_only_list = []
            beta_only_list = []
            alpha_only_list = []
            for listElement in bare_pack_version_list:
                if listElement[0] == "R":
                    release_only_list.append(listElement)
                if listElement[0] == "B":
                    beta_only_list.append(listElement)
                if listElement[0] == "A":
                    alpha_only_list.append(listElement)

            print("Project ID: " + project_id)
            if len(release_only_list) > 0:
                for listElement in release_only_list:
                    print(listElement)
            if len(beta_only_list) > 0:
                for listElement in beta_only_list:
                    print(listElement)
            if len(alpha_only_list) > 0:
                for listElement in alpha_only_list:
                    print(listElement)
        # TODO Implement mod downloading after url fetch and zip download.
        # workThread = threading.Thread(target=manager.download_mods, args=("242001", "2349268"))
        # workThread.start()
        # while not manager.isDone:
        #     time.sleep(0.05)
        #     if manager.fileSize is not None:
        #         percent = round((manager.currentProgress/manager.fileSize) * 100, 0)
        #         print(str(percent) + " P: " + str(manager.currentProgress) + "/" + str(manager.fileSize))
        # print("Done")
            VersionSelectionMenu()
            self.close_window()


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
                    print("error: Folder With That Name Already Exists.")
                else:
                    # FIXME dfsdfsdf
                    # TODO unpack zip file.
                    unzip(file_path, dst_dir)
                    # TODO process manifest.
                    # TODO download mods.


class VersionSelectionMenu(Toplevel):
    def __init__(self):
        Toplevel.__init__(self)
        self.minsize(width=400, height=75)
        self.maxsize(width=400, height=75)
        self.resizable(FALSE, FALSE)
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.title("Select Mod Pack Version")
        center(self)
        self.focus()
        self.grab_set()
        for column_index in range(2):
            self.columnconfigure(column_index, weight=1)
        for row_index in range(3):
            self.rowconfigure(row_index, weight=1)

        self.lbl_entry_url = ttk.Label(self, text="Enter MOD_PACK_NAME Here: \n"
                                                  "Example: https://minecraft.curseforge.com/projects/MOD_PACK_NAME")
        self.entry_mod_pack_name = ttk.Entry(self)
        self.button_submit = ttk.Button(self, text="Enter")
        self.button_cancel = ttk.Button(self, text="Cancel", command=self.close_window)
        # ---
        self.lbl_entry_url.grid(column=0, row=0, sticky='N', columnspan=2)
        self.entry_mod_pack_name.grid(column=0, row=1, sticky='EW', columnspan=2)
        self.entry_mod_pack_name.focus()
        self.button_submit.grid(column=0, row=2, sticky='NESW')
        self.button_cancel.grid(column=1, row=2, sticky='NESW')

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
        center(self)
        self.focus()
        self.grab_set()
        self.columnconfigure(0, weight=1)
        for row_index in range(5):
            self.rowconfigure(row_index, weight=1)

        button_new_from_url = ttk.Button(self, text="New From Curse URL", command=NewFromCurseUrl)
        button_new_from_zip = ttk.Button(self, text="New From Curse Pack.zip", command=OpenPackZip)
        button_new_from_manifest = ttk.Button(self, text="New From Curse Manifest.json")
        button_new_from_existing_instance = ttk.Button(self, text="Copy Existing Instance", command=CopyInstance)
        button_close_window = ttk.Button(self, text="Close", command=self.close_window)
        # ---
        button_new_from_url.grid(column=0, row=0, sticky='NESW')
        button_new_from_zip.grid(column=0, row=1, sticky='NESW')
        button_new_from_manifest.grid(column=0, row=2, sticky='NESW')
        button_new_from_existing_instance.grid(column=0, row=3, sticky='NESW')
        button_close_window.grid(column=0, row=4, sticky='NESW')

    def close_window(self):
        self.grab_release()
        self.destroy()


class EditInstance:
    pass  # TODO add editing instances options.


class ProgramSettings:
    pass  # TODO add program settings options.


class RootWindow(Tk):
    def __init__(self):
        Tk.__init__(self)
        self.title(PROGRAM_NAME + ' v' + PROGRAM_VERSION_NUMBER + " " + PROGRAM_VERSION_BUILD)
        self.minsize(width=600, height=300)
        center(self)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.logWindow = Text(self, state="disabled", width=40)
        self.logWindowScrollbar = Scrollbar(self, command=self.logWindow.yview)
        self.logWindow['yscrollcommand'] = self.logWindowScrollbar.set
        self.menu_buttons = ttk.Frame(self)
        self.button_create_new_instance = ttk.Button(self.menu_buttons, text="New Instance", command=NewInstanceWindow)
        self.checkInstanceUpdate = ttk.Button(self.menu_buttons, text="Check For Instance Updates")
        self.bEditInstance = ttk.Button(self.menu_buttons, text="Edit Instance", command=EditInstance)
        self.bProgramSettings = ttk.Button(self.menu_buttons, text="Program Settings", command=ProgramSettings)
        self.selfUpdateCheck = ttk.Button(self.menu_buttons, text="Self Update",
                                          command=lambda: self.set_output("No Updates :P"))
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


# If this script is being run then start. else if being accessed don't try and run the gui stuffs.
if __name__ == '__main__':
    # needs to be inside a Tk() master window to display the askstring.
    # ask = simpledialog.askstring("test", "yo")
    RootWindow()
