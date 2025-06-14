# build.spec

import sys
import os
from PyInstaller.utils.hooks import collect_data_files
import customtkinter

# --- Prepare data files ---
# Explicitly add customtkinter assets by finding its installation directory
# and then locating the 'assets' folder within it.
customtkinter_path = os.path.dirname(customtkinter.__file__)
customtkinter_assets_path = os.path.join(customtkinter_path, "assets")

datas = []
if os.path.exists(customtkinter_assets_path):
    datas.append((customtkinter_assets_path, "customtkinter/assets"))

# Add tkcalendar data files using the standard hook
datas.extend(collect_data_files('tkcalendar'))

# --- Basic Setup ---
a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=datas, # Add all collected data files here
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False
)


# --- Finalize Analysis ---
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# --- Executable Settings ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='政府采购爬虫',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join('assets', 'app_icon.ico')
)

# --- Bundle Files ---
# The 'a.datas' from the Analysis object is automatically passed to COLLECT
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GovSpider'
)
