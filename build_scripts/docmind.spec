"""
DocMind - PyInstaller設定ファイル
Windows向けアプリケーションパッケージ化設定

このファイルはPyInstallerがDocMindアプリケーションを
単一の実行可能ファイルにパッケージ化するための設定を定義します。
"""

import sys
import os
from pathlib import Path
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.api import PYZ, EXE, COLLECT

# プロジェクトルートディレクトリの取得
# PyInstaller実行時はSPECPATHが利用可能、それ以外は現在のディレクトリから推定
try:
    project_root = Path(os.path.abspath(SPECPATH)).parent
except NameError:
    # テスト実行時など、SPECPATHが定義されていない場合
    project_root = Path(os.path.dirname(os.path.abspath(__file__))).parent if '__file__' in globals() else Path.cwd()
src_path = project_root / "src"

# 追加データファイルの定義
added_files = [
    # アイコンファイル
    (str(project_root / "assets" / "docmind.ico"), "assets"),
    # 設定ファイル
    (str(project_root / "config" / "default_config.json"), "config"),
    # ライセンスファイル
    (str(project_root / "LICENSE"), "."),
    # README
    (str(project_root / "README.md"), "."),
]

# 隠れたインポートの定義（PyInstallerが自動検出できないモジュール）
hidden_imports = [
    # PySide6関連
    'PySide6.QtCore',
    'PySide6.QtWidgets',
    'PySide6.QtGui',
    'PySide6.QtSvg',

    # sentence-transformers関連
    'sentence_transformers',
    'transformers',
    'torch',
    'numpy',
    'scipy',
    'scipy.spatial.distance',
    'sklearn',
    'sklearn.metrics.pairwise',

    # ドキュメント処理関連
    'fitz',  # PyMuPDF
    'docx',  # python-docx
    'openpyxl',

    # その他の依存関係
    'whoosh',
    'watchdog',
    'chardet',
    'psutil',

    # 標準ライブラリの一部（明示的に含める）
    'sqlite3',
    'pickle',
    'json',
    'logging',
    'threading',
    'multiprocessing',
]

# 除外するモジュール（不要なライブラリを除外してサイズを削減）
excluded_modules = [
    'matplotlib',
    'IPython',
    'jupyter',
    'notebook',
    'pandas',  # 使用していない場合
    'scipy',   # 使用していない場合
]

# バイナリファイルの除外（不要なバイナリを除外）
excluded_binaries = []

# 追加バイナリファイル（scipyなどの重要なライブラリ）
import scipy
scipy_path = scipy.__path__[0]
additional_binaries = [
    (scipy_path, 'scipy'),
]

# PyInstallerの分析設定
a = Analysis(
    [str(project_root / 'main.py')],
    pathex=[str(project_root), str(src_path)],
    binaries=additional_binaries,
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 不要なファイルの除外
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 実行可能ファイルの設定
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DocMind',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # UPX圧縮を有効化（サイズ削減）
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # コンソールウィンドウを非表示
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "docmind.ico") if (project_root / "assets" / "docmind.ico").exists() else None,
    version=str(project_root / "build_scripts" / "version_info.txt") if (project_root / "build_scripts" / "version_info.txt").exists() else None,
)

# ディレクトリ形式の配布ファイル作成
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DocMind'
)

# Windows向けの追加設定
if sys.platform == "win32":
    # Windowsサービスとしての実行を無効化
    exe.console = False
    exe.debug = False
