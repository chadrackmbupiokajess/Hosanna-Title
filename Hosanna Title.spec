# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['vmix_titres.py'],
    pathex=[],
    binaries=[],
    datas=[('en cours.png', '.'), ('a suivre.png', '.'), ('HosannaTitle.png', '.'), ('titre_actuel.txt', '.'), ('titre_suivant.txt', '.')],
    hiddenimports=[],
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
    name='Hosanna Title',
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
)
