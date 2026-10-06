# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['flask', 'jinja2', 'werkzeug', 'dotenv', 'reportlab', 'PIL', 'PIL.Image', 'sqlite3', 'PIL', 'dotenv', 'flask', 'jinja2', 'werkzeug']
hiddenimports += collect_submodules('jinja2')
hiddenimports += collect_submodules('reportlab')


a = Analysis(
    ['C:\\Users\\hp\\Documents\\SastoukaStore\\SastoukaStore_13\\_build_sastoukastore_onefile_v2\\sastoukastore_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\hp\\Documents\\SastoukaStore\\SastoukaStore_13\\_build_sastoukastore_onefile_v2\\sastoukastore_payload.zip', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SastoukaStore',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\hp\\Documents\\SastoukaStore\\SastoukaStore_13\\_build_sastoukastore_onefile_v2\\sastoukastore.ico'],
)
