# -*- mode: python ; coding: utf-8 -*-
# Спецификация PyInstaller для ChatList

import os
import re

# Генерация version_info.txt из version.py (единый источник версии)
_spec_dir = os.path.dirname(os.path.abspath(SPECPATH))
_version_file = os.path.join(_spec_dir, 'version.py')
if not os.path.exists(_version_file):
    _spec_dir = os.getcwd()
    _version_file = os.path.join(_spec_dir, 'version.py')
with open(_version_file, 'r', encoding='utf-8') as _f:
    _m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', _f.read())
__version__ = _m.group(1) if _m else "0.0.0"

_v = [int(x) for x in __version__.split('.')]
while len(_v) < 4:
    _v.append(0)
_v_tuple = tuple(_v[:4])

_version_info_content = f'''# UTF-8
# Сгенерировано из version.py
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={_v_tuple},
    prodvers={_v_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'ChatList'),
          StringStruct('FileDescription', 'ChatList - Сравнение ответов нейросетей'),
          StringStruct('FileVersion', '{__version__}'),
          StringStruct('InternalName', 'ChatList'),
          StringStruct('LegalCopyright', ''),
          StringStruct('OriginalFilename', 'ChatList.exe'),
          StringStruct('ProductName', 'ChatList'),
          StringStruct('ProductVersion', '{__version__}')
        ])
    ]),
    VarFileInfo([VarStruct('Translation', [0x0409, 1200])])
  ]
)
'''

_version_info_path = os.path.join(_spec_dir, 'version_info.txt')
with open(_version_info_path, 'w', encoding='utf-8') as _f:
    _f.write(_version_info_content)

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'version',
        'db',
        'models',
        'network',
        'config',
        'export',
        'logger',
        'markdown',
        'markdown.extensions',
        'markdown.extensions.extra',
        'markdown.extensions.nl2br',
        'markdown.extensions.sane_lists',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ChatList',
    version=_version_info_path,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Без консоли (GUI-приложение)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
