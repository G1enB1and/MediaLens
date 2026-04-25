# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules


scipy_special_hiddenimports = collect_submodules(
    'scipy.special',
    filter=lambda name: '.tests' not in name,
)

local_ai_runtime_excludes = [
    'accelerate',
    'huggingface_hub',
    'onnxruntime',
    'safetensors',
    'sentencepiece',
    'tokenizers',
    'torch',
    'torchvision',
    'transformers',
]

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('native/mediamanagerx_app/web', 'native/mediamanagerx_app/web'),
        ('app/mediamanager/db/schema_v1.sql', 'app/mediamanager/db'),
        ('VERSION', '.'),
        ('qt.conf', '.'),
        ('ReleaseNotes.md', '.'),
        ('requirements-local-ai-wd-swinv2.txt', '.'),
        ('requirements-local-ai-internlm-xcomposer2.txt', '.'),
        ('requirements-local-ai-gemma.txt', '.'),
        ('requirements-local-ocr-paddle.txt', '.'),
        ('app/mediamanager/ai_captioning', 'app/mediamanager/ai_captioning'),
        ('app/mediamanager/ocr', 'app/mediamanager/ocr'),
        ('native/mediamanagerx_app/TOS.md', '.'),
        ('native/mediamanagerx_app/CHANGELOG.md', '.'),
        ('native/mediamanagerx_app/SEARCH_SYNTAX.md', '.'),
    ],
    hiddenimports=[
        'imagehash',
        'numpy',
        'scipy.ndimage',
        'pywt',
        'cv2',
        'winsdk',
        'winsdk.windows.media.ocr',
        'winsdk.windows.graphics.imaging',
        'winsdk.windows.storage',
        'winsdk.windows.globalization',
    ] + scipy_special_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'mkl',
        'tcl',
        'tk',
        'tkinter',
        'matplotlib',
        'pandas',
        'notebook',
        'nbconvert',
        'nbformat',
    ] + local_ai_runtime_excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MediaLens',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['native/mediamanagerx_app/web/MediaLens-Logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MediaLens',
)
