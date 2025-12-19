# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ClipAudio.

Usage:
    pip install pyinstaller
    pyinstaller ClipAudio.spec
"""

import os
import certifi

block_cipher = None

a = Analysis(
    ['src/clipaudio/menubar.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include certifi certificates
        (certifi.where(), 'certifi'),
        # Include menu bar icon
        ('assets/menubar_icon.png', 'assets'),
        ('assets/menubar_icon@2x.png', 'assets'),
    ],
    hiddenimports=[
        'clipaudio',
        'rumps',
        'yt_dlp',
        'certifi',
        'AppKit',
        'Foundation',
        'objc',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'PIL'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ClipAudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ClipAudio',
)

app = BUNDLE(
    coll,
    name='ClipAudio.app',
    icon='assets/icon.icns',
    bundle_identifier='com.clipaudio.menubar',
    info_plist={
        'CFBundleName': 'ClipAudio',
        'CFBundleDisplayName': 'ClipAudio',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'LSUIElement': True,  # Hide from Dock (menu bar app)
        'NSHighResolutionCapable': True,
        # Notification permissions
        'NSUserNotificationAlertStyle': 'alert',
    },
)

