#!/usr/bin/python
# -*- coding: utf-8 -*-


# http://cx-freeze.readthedocs.io/en/latest/distutils.html#build-exe
# http://cx-freeze.readthedocs.io/en/latest/faq.html#using-data-files
from cx_Freeze import setup, Executable
import sys
import os
from downloader_core import PROGRAM_VERSION_NUMBER, PROGRAM_NAME

build_exe_options = {
        "packages": ['idna'],  # Required for requests packages higher then requests==2.11.1 for freeze to work.
        "optimize": 2,
        "include_files": [],
        "excludes": [
            "ctypes",
            "lib2to3",
            "multiprocessing",
            "pydoc_data",
            "unittest",
            "xml",
            "xmlrpc"
        ]
}

base = None
downloaderGUI = "curseforgePackDownloadManagerGUI"
downloaderCLI = "curseforgePackDownloadManagerCLI"
executables_list = [Executable("curseforgePackDownloadManagerGUI.py", targetName=downloaderGUI, base=base),
                    Executable("curseforgePackDownloadManagerCLI.py", targetName=downloaderCLI, base=base)
                    ]

if sys.platform == "win32":
    base = "Win32GUI"  # Makes program work only as GUI on windows.
    downloaderGUI += ".exe"
    downloaderCLI += ".exe"
    curseDownloaderCLI = "cursePackDownloaderCLI.exe"
    manifest_updaterCLI = "manifest_updaterCLI.exe"
    # build_exe_options = {}


    def fix_tkinter_freeze():
        # FIXME: This is required until cx_freeze fixes pathing to os.environ['TCL_LIBRARY'], os.environ['TK_LIBRARY']
        import tkinter

        dummy_tkinter_object = tkinter.Tk()  # Used to get the current tcl, tk libraries.
        os.environ["TCL_LIBRARY"] = os.path.normpath(dummy_tkinter_object.tk.exprstring('$tcl_library'))
        os.environ["TK_LIBRARY"] = os.path.normpath(dummy_tkinter_object.tk.exprstring('$tk_library'))
        for sys_path in sys.path:
            if sys_path.endswith("DLLs"):
                if os.path.exists(sys_path):
                    dll_files = os.listdir(sys_path)
                    for dll in dll_files:
                        if dll.startswith('tcl') and dll.endswith('.dll'):
                            build_exe_options["include_files"].append(os.path.join(sys_path, dll))
                            continue
                        elif dll.startswith('tk') and dll.endswith('.dll'):
                            build_exe_options["include_files"].append(os.path.join(sys_path, dll))
                            continue

    fix_tkinter_freeze()  # Used to fix ref to TCL_LIBRARY, and TK_LIBRARY

    executables_list = [Executable("curseforgePackDownloadManagerGUI.py", targetName=downloaderGUI, base=base),
                        Executable("curseforgePackDownloadManagerCLI.py", targetName=curseDownloaderCLI, base="Console")
                        ]

setup(
    name=PROGRAM_NAME,
    version=PROGRAM_VERSION_NUMBER,
    author='TOLoneWolf',
    # author_email='',
    # packages=[''],
    # url='',
    license='GNU GENERAL PUBLIC LICENSE Version 3',
    description='Curseforge Modpack Downloader manager',
    options={"build_exe": build_exe_options},
    requires=['requests'],
    executables=executables_list
)
