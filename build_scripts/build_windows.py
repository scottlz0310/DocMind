#!/usr/bin/env python3
"""
DocMind - Windows向けビルドスクリプト
PyInstallerを使用してWindows実行可能ファイルを生成

このスクリプトは以下の処理を実行します：
1. 依存関係の確認
2. PyInstallerによる実行可能ファイルの生成
3. 必要なファイルのコピー
4. インストーラーの準備
"""

import logging
import shutil
import subprocess
import sys
from pathlib import Path

# プロジェクトルートの設定
PROJECT_ROOT = Path(__file__).parent.parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
INSTALLER_DIR = PROJECT_ROOT / "installer"

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "build.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def check_requirements() -> bool:
    """
    ビルドに必要な要件をチェック

    Returns:
        bool: すべての要件が満たされている場合True
    """
    logger.info("ビルド要件をチェック中...")

    # Python バージョンチェック

    # 必要なパッケージのチェック
    required_packages = [
        'PyInstaller',
        'PySide6',
        'sentence-transformers',
        'Whoosh',
        'PyMuPDF',
        'python-docx',
        'openpyxl',
        'watchdog',
        'chardet',
        'psutil',
        'scipy'
    ]

    missing_packages = []
    import_map = {
        'PyInstaller': 'PyInstaller',
        'PySide6': 'PySide6',
        'sentence-transformers': 'sentence_transformers',
        'Whoosh': 'whoosh',
        'PyMuPDF': 'fitz',
        'python-docx': 'docx',
        'openpyxl': 'openpyxl',
        'watchdog': 'watchdog',
        'chardet': 'chardet',
        'psutil': 'psutil',
        'scipy': 'scipy'
    }
    
    for package in required_packages:
        try:
            import_name = import_map.get(package, package.lower().replace('-', '_'))
            __import__(import_name)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        logger.error(f"不足しているパッケージ: {', '.join(missing_packages)}")
        logger.error("pip install -e .[build,dev] を実行してください")
        return False

    # プロジェクトファイルの存在チェック
    required_files = [
        PROJECT_ROOT / "main.py",
        PROJECT_ROOT / "pyproject.toml",
        PROJECT_ROOT / "build_scripts" / "docmind.spec"
    ]

    missing_files = [f for f in required_files if not f.exists()]
    if missing_files:
        logger.error(f"必要なファイルが見つかりません: {missing_files}")
        return False

    logger.info("すべての要件が満たされています")
    return True


def clean_build_directories() -> None:
    """
    ビルドディレクトリをクリーンアップ
    """
    logger.info("ビルドディレクトリをクリーンアップ中...")

    directories_to_clean = [BUILD_DIR, DIST_DIR, INSTALLER_DIR]

    for directory in directories_to_clean:
        if directory.exists():
            try:
                # Windowsでの権限問題を回避するため、読み取り専用属性を削除
                import stat
                import os
                
                def remove_readonly(func, path, _):
                    """読み取り専用ファイルを削除可能にする"""
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                
                shutil.rmtree(directory, onerror=remove_readonly)
                logger.info(f"削除完了: {directory}")
            except Exception as e:
                logger.warning(f"削除に失敗: {directory} - {e}")
                # 削除に失敗した場合は続行

    # 必要なディレクトリを再作成
    for directory in directories_to_clean:
        directory.mkdir(parents=True, exist_ok=True)


def create_assets() -> None:
    """
    アセットファイルを作成
    """
    logger.info("アセットファイルを作成中...")

    assets_dir = PROJECT_ROOT / "assets"
    assets_dir.mkdir(exist_ok=True)

    # アイコンファイルが存在しない場合はダミーを作成
    icon_path = assets_dir / "docmind.ico"
    if not icon_path.exists():
        logger.info("アイコンファイルが見つからないため、ダミーアイコンを作成します")
        # 簡単なダミーアイコンファイルを作成（実際のプロジェクトでは適切なアイコンを用意）
        try:
            from PIL import Image
            img = Image.new('RGB', (32, 32), color='blue')
            img.save(icon_path, format='ICO')
        except ImportError:
            logger.warning("PILが利用できないため、アイコンファイルをスキップします")


def create_default_config() -> None:
    """
    デフォルト設定ファイルを作成
    """
    logger.info("デフォルト設定ファイルを作成中...")

    config_dir = PROJECT_ROOT / "config"
    config_dir.mkdir(exist_ok=True)

    default_config = {
        "data_directory": "./docmind_data",
        "log_level": "INFO",
        "search_timeout": 5,
        "max_documents": 50000,
        "embedding_model": "all-MiniLM-L6-v2",
        "ui_language": "ja",
        "auto_index": True,
        "watch_directories": []
    }

    import json
    config_path = config_dir / "default_config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2, ensure_ascii=False)

    logger.info(f"デフォルト設定ファイルを作成: {config_path}")


def run_pyinstaller() -> bool:
    """
    PyInstallerを実行してアプリケーションをビルド

    Returns:
        bool: ビルドが成功した場合True
    """
    logger.info("PyInstallerでアプリケーションをビルド中...")

    spec_file = PROJECT_ROOT / "build_scripts" / "docmind.spec"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--log-level=INFO",
        f"--workpath={BUILD_DIR}",
        f"--distpath={DIST_DIR}",
        str(spec_file)
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'  # エンコーディングエラーを置換文字で処理
        )

        if result.returncode == 0:
            logger.info("PyInstallerビルドが成功しました")
            return True
        else:
            logger.error("PyInstallerビルドが失敗しました:")
            logger.error(f"stdout: {result.stdout}")
            logger.error(f"stderr: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"PyInstallerの実行中にエラーが発生: {e}")
        return False


def prepare_distribution() -> None:
    """
    配布用ファイルを準備
    """
    logger.info("配布用ファイルを準備中...")

    # 実行可能ファイルの場所（PyInstallerの出力先）
    exe_path = DIST_DIR / "DocMind" / "DocMind.exe"

    if not exe_path.exists():
        logger.error(f"実行可能ファイルが見つかりません: {exe_path}")
        return

    # 配布ディレクトリの作成
    distribution_dir = INSTALLER_DIR / "DocMind"
    distribution_dir.mkdir(parents=True, exist_ok=True)

    # 実行ファイルをコピー
    shutil.copy2(exe_path, distribution_dir / "DocMind.exe")
    
    # _internalディレクトリをコピー
    internal_src = exe_path.parent / "_internal"
    internal_dst = distribution_dir / "_internal"
    if internal_src.exists():
        shutil.copytree(internal_src, internal_dst)
        logger.info(f"_internalディレクトリをコピー: {internal_dst}")
    
    # データディレクトリを作成
    data_dir = distribution_dir / "docmind_data"
    data_dir.mkdir(exist_ok=True)
    
    logger.info("実行可能ファイルをコピーしました")

    # 追加ファイルをコピー
    additional_files = [
        (PROJECT_ROOT / "LICENSE", "LICENSE.txt"),
        (PROJECT_ROOT / "README.md", "README.txt"),
    ]

    for src, dst in additional_files:
        if src.exists():
            shutil.copy2(src, distribution_dir / dst)
            logger.info(f"ファイルをコピー: {src} -> {dst}")

    # スタートアップスクリプトを作成
    create_startup_script(distribution_dir)

    # アンインストールスクリプトを作成
    create_uninstall_script(distribution_dir)
    
    # Inno Setupインストーラーを作成
    create_inno_setup_installer()


def create_startup_script(distribution_dir: Path) -> None:
    """
    スタートアップスクリプトを作成

    Args:
        distribution_dir: 配布ディレクトリのパス
    """
    startup_script = """@echo off
REM DocMind スタートアップスクリプト
REM このスクリプトはDocMindアプリケーションを起動します

echo DocMindを起動中...

REM データディレクトリの作成
if not exist "%USERPROFILE%\\DocMind" (
    mkdir "%USERPROFILE%\\DocMind"
    echo データディレクトリを作成しました: %USERPROFILE%\\DocMind
)

REM アプリケーションの起動
start "" "%~dp0DocMind.exe"

echo DocMindが起動しました
pause
"""

    script_path = distribution_dir / "start_docmind.bat"
    with open(script_path, 'w', encoding='shift_jis') as f:
        f.write(startup_script)

    logger.info(f"スタートアップスクリプトを作成: {script_path}")


def create_uninstall_script(distribution_dir: Path) -> None:
    """
    アンインストールスクリプトを作成

    Args:
        distribution_dir: 配布ディレクトリのパス
    """
    uninstall_script = """@echo off
REM DocMind アンインストールスクリプト
REM このスクリプトはDocMindアプリケーションをアンインストールします

echo DocMindをアンインストール中...

REM プロセスの終了
taskkill /f /im DocMind.exe 2>nul

REM ユーザーデータの削除確認
set /p confirm="ユーザーデータも削除しますか？ (y/N): "
if /i "%confirm%"=="y" (
    if exist "%USERPROFILE%\\DocMind" (
        rmdir /s /q "%USERPROFILE%\\DocMind"
        echo ユーザーデータを削除しました
    )
)

REM スタートメニューショートカットの削除
if exist "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\DocMind.lnk" (
    del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\DocMind.lnk"
    echo スタートメニューショートカットを削除しました
)

REM デスクトップショートカットの削除
if exist "%USERPROFILE%\\Desktop\\DocMind.lnk" (
    del "%USERPROFILE%\\Desktop\\DocMind.lnk"
    echo デスクトップショートカットを削除しました
)

echo アンインストールが完了しました
pause
"""

    script_path = distribution_dir / "uninstall.bat"
    with open(script_path, 'w', encoding='shift_jis') as f:
        f.write(uninstall_script)

    logger.info(f"アンインストールスクリプトを作成: {script_path}")


def create_inno_setup_installer() -> None:
    """
    Inno Setupインストーラーを作成
    """
    logger.info("Inno Setupインストーラーを作成中...")
    
    iss_file = PROJECT_ROOT / "build_scripts" / "docmind_installer.iss"
    if not iss_file.exists():
        logger.warning("Inno Setupスクリプトが見つかりません。スキップします。")
        return
    
    try:
        # Inno Setup Compilerを実行
        cmd = ["iscc", str(iss_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Inno Setupインストーラーの作成が完了しました")
        else:
            logger.warning(f"Inno Setupが利用できません: {result.stderr}")
            logger.info("代替インストーラーを作成します")
            create_simple_installer()
            
    except FileNotFoundError:
        logger.warning("Inno Setup Compilerが見つかりません。代替インストーラーを作成します")
        create_simple_installer()


def create_simple_installer() -> None:
    """
    シンプルなインストーラーを作成（Inno Setupが利用できない場合）
    """
    logger.info("シンプルなインストーラーを作成中...")
    
    # 7-Zipを使用してSFXアーカイブを作成
    try:
        distribution_dir = INSTALLER_DIR / "DocMind"
        installer_name = f"DocMind_Setup_v1.0.0.exe"
        installer_path = INSTALLER_DIR / installer_name
        
        # 7-Zipでアーカイブを作成
        cmd = [
            "7z", "a", "-sfx7z.sfx", str(installer_path), 
            str(distribution_dir / "*")
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"SFXインストーラーを作成: {installer_path}")
        else:
            # 7-Zipも利用できない場合は、ZIPファイルを作成
            logger.warning("7-Zipが利用できません。ZIPアーカイブを作成します")
            create_zip_archive()
            
    except FileNotFoundError:
        logger.warning("7-Zipが見つかりません。ZIPアーカイブを作成します")
        create_zip_archive()


def create_zip_archive() -> None:
    """
    ZIPアーカイブを作成
    """
    import zipfile
    
    logger.info("ZIPアーカイブを作成中...")
    
    distribution_dir = INSTALLER_DIR / "DocMind"
    zip_name = f"DocMind_v1.0.0.zip"
    zip_path = INSTALLER_DIR / zip_name
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in distribution_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(distribution_dir)
                zipf.write(file_path, arcname)
    
    logger.info(f"ZIPアーカイブを作成: {zip_path}")


def main() -> None:
    """
    メイン実行関数
    """
    logger.info("DocMind Windowsビルドプロセスを開始します")

    try:
        # 1. 要件チェック
        if not check_requirements():
            logger.error("ビルド要件が満たされていません")
            sys.exit(1)

        # 2. ビルドディレクトリのクリーンアップ
        clean_build_directories()

        # 3. アセットファイルの作成
        create_assets()

        # 4. デフォルト設定ファイルの作成
        create_default_config()

        # 5. PyInstallerでビルド
        if not run_pyinstaller():
            logger.error("PyInstallerビルドに失敗しました")
            sys.exit(1)

        # 6. 配布用ファイルの準備
        prepare_distribution()

        logger.info("ビルドプロセスが正常に完了しました")
        logger.info(f"配布ファイル: {INSTALLER_DIR}")

    except Exception as e:
        logger.error(f"ビルドプロセス中にエラーが発生: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
