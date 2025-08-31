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
        'psutil'
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
        'psutil': 'psutil'
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
        PROJECT_ROOT / "build_scripts" / "pyinstaller_spec.py"
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
                shutil.rmtree(directory)
                logger.info(f"削除完了: {directory}")
            except Exception as e:
                logger.warning(f"削除に失敗: {directory} - {e}")

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

    spec_file = PROJECT_ROOT / "build_scripts" / "pyinstaller_spec.py"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--log-level=INFO",
        str(spec_file)
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding='utf-8'
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
    import platform
    if platform.system() == "Windows":
        exe_path = DIST_DIR / "pyinstaller_spec" / "pyinstaller_spec.exe"
    else:
        exe_path = DIST_DIR / "pyinstaller_spec" / "pyinstaller_spec"

    if not exe_path.exists():
        logger.error(f"実行可能ファイルが見つかりません: {exe_path}")
        return

    # 配布ディレクトリの作成
    distribution_dir = INSTALLER_DIR / "DocMind"
    distribution_dir.mkdir(parents=True, exist_ok=True)

    # 実行可能ファイルをコピー（名前をDocMind.exeに変更）
    shutil.copy2(exe_path, distribution_dir / "DocMind.exe")
    
    # インストーラーファイルを作成（シンプルなコピー版）
    installer_name = f"DocMind_Setup_v1.0.0.exe"
    installer_path = INSTALLER_DIR / installer_name
    shutil.copy2(exe_path, installer_path)
    logger.info(f"インストーラーファイルを作成: {installer_path}")
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


def create_installer_script() -> None:
    """
    インストーラースクリプトを作成
    """
    logger.info("インストーラースクリプトを作成中...")

    installer_script = """@echo off
REM DocMind インストーラー
REM このスクリプトはDocMindアプリケーションをインストールします

echo DocMindインストーラーへようこそ
echo.

REM インストール先ディレクトリの設定
set "INSTALL_DIR=%PROGRAMFILES%\\DocMind"
set /p custom_dir="インストール先 (デフォルト: %INSTALL_DIR%): "
if not "%custom_dir%"=="" set "INSTALL_DIR=%custom_dir%"

echo.
echo インストール先: %INSTALL_DIR%
echo.

REM 管理者権限の確認
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo このインストーラーは管理者権限で実行する必要があります
    echo 右クリックして「管理者として実行」を選択してください
    pause
    exit /b 1
)

REM インストールディレクトリの作成
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo インストールディレクトリを作成しました
)

REM ファイルのコピー
echo ファイルをコピー中...
xcopy /E /I /Y "DocMind\\*" "%INSTALL_DIR%\\"
if %errorLevel% neq 0 (
    echo ファイルのコピーに失敗しました
    pause
    exit /b 1
)

REM スタートメニューショートカットの作成
echo スタートメニューショートカットを作成中...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\DocMind.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\DocMind.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'DocMind - ローカルAI搭載ドキュメント検索'; $Shortcut.Save()"

REM デスクトップショートカットの作成確認
set /p desktop_shortcut="デスクトップにショートカットを作成しますか？ (Y/n): "
if /i not "%desktop_shortcut%"=="n" (
    echo デスクトップショートカットを作成中...
    powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\\Desktop\\DocMind.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\DocMind.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'DocMind - ローカルAI搭載ドキュメント検索'; $Shortcut.Save()"
)

REM レジストリエントリの作成（アンインストール情報）
echo アンインストール情報を登録中...
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DocMind" /v "DisplayName" /t REG_SZ /d "DocMind" /f
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DocMind" /v "DisplayVersion" /t REG_SZ /d "1.0.0" /f
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DocMind" /v "Publisher" /t REG_SZ /d "DocMind Project" /f
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DocMind" /v "InstallLocation" /t REG_SZ /d "%INSTALL_DIR%" /f
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\DocMind" /v "UninstallString" /t REG_SZ /d "%INSTALL_DIR%\\uninstall.bat" /f

echo.
echo インストールが完了しました！
echo DocMindはスタートメニューまたはデスクトップから起動できます。
echo.
pause
"""

    installer_path = INSTALLER_DIR / "install.bat"
    with open(installer_path, 'w', encoding='shift_jis') as f:
        f.write(installer_script)

    logger.info(f"インストーラースクリプトを作成: {installer_path}")


def create_documentation() -> None:
    """
    ユーザードキュメントを作成
    """
    logger.info("ユーザードキュメントを作成中...")

    docs_dir = INSTALLER_DIR / "docs"
    docs_dir.mkdir(exist_ok=True)

    # インストールガイド
    install_guide = """# DocMind インストールガイド

## システム要件

- Windows 10 (64-bit) 以降
- 空きディスク容量: 最低 2GB（推奨 5GB以上）
- メモリ: 最低 4GB（推奨 8GB以上）
- インターネット接続: 初回起動時のAIモデルダウンロードに必要

## インストール手順

1. `install.bat` を右クリックして「管理者として実行」を選択
2. インストール先を指定（デフォルトのまま推奨）
3. インストールの完了を待つ
4. スタートメニューまたはデスクトップのショートカットからDocMindを起動

## 初回起動時の設定

1. DocMindを起動すると、初回セットアップが開始されます
2. 検索対象のフォルダを選択してください
3. AIモデルのダウンロードが自動的に開始されます（数分かかる場合があります）
4. インデックス作成が完了すると、検索が利用可能になります

## 使用方法

### 基本的な検索
1. 検索ボックスにキーワードを入力
2. 検索タイプを選択（全文検索/セマンティック検索/ハイブリッド）
3. 検索結果から目的のドキュメントを選択
4. プレビューペインでドキュメント内容を確認

### フォルダの追加
1. 左ペインのフォルダツリーで右クリック
2. 「フォルダを追加」を選択
3. 検索対象に追加したいフォルダを選択

### 設定の変更
1. メニューバーから「設定」を選択
2. 各種設定を変更
3. 「適用」をクリックして設定を保存

## トラブルシューティング

### 起動しない場合
- Windows Defenderやウイルス対策ソフトが実行をブロックしていないか確認
- 管理者権限で実行してみる
- イベントビューアーでエラーログを確認

### 検索結果が表示されない場合
- インデックス作成が完了しているか確認
- 検索対象フォルダが正しく設定されているか確認
- ファイルが対応形式（PDF、Word、Excel、Markdown、テキスト）か確認

### パフォーマンスが遅い場合
- 利用可能メモリを確認
- 検索対象ファイル数を制限
- 設定でキャッシュサイズを調整

## アンインストール

1. `uninstall.bat` を実行
2. ユーザーデータの削除を選択（必要に応じて）
3. アンインストールの完了を待つ

## サポート

問題が解決しない場合は、以下の情報を含めてサポートにお問い合わせください：
- Windowsのバージョン
- エラーメッセージ
- ログファイル（%USERPROFILE%\\DocMind\\logs\\docmind.log）
"""

    with open(docs_dir / "install_guide.md", 'w', encoding='utf-8') as f:
        f.write(install_guide)

    # ユーザーマニュアル
    user_manual = """# DocMind ユーザーマニュアル

## 概要

DocMindは、ローカルPC上のドキュメントを高速かつ正確に検索するためのAI搭載アプリケーションです。
従来のキーワード検索に加えて、意味を理解するセマンティック検索機能を提供します。

## 主な機能

### 1. ハイブリッド検索
- **全文検索**: 正確なキーワードマッチング
- **セマンティック検索**: 意味に基づく検索
- **ハイブリッド検索**: 両方の手法を組み合わせた最適な検索

### 2. 対応ファイル形式
- PDF (.pdf)
- Microsoft Word (.docx, .doc)
- Microsoft Excel (.xlsx, .xls)
- Markdown (.md)
- テキストファイル (.txt)

### 3. リアルタイム更新
- ファイルの追加、変更、削除を自動検出
- インデックスの自動更新

## インターフェース

### 3ペインレイアウト
1. **左ペイン**: フォルダツリー
2. **中央ペイン**: 検索結果
3. **右ペイン**: ドキュメントプレビュー

### 検索機能
- 検索ボックス: クエリの入力
- 検索タイプ選択: 検索方法の選択
- フィルター: 結果の絞り込み

## 詳細な使用方法

### 検索のコツ

#### 全文検索
- 正確なキーワードを使用
- 複数のキーワードはスペースで区切る
- 引用符で完全一致検索: "正確なフレーズ"

#### セマンティック検索
- 自然な文章で質問
- 概念や意味で検索
- 類義語も自動的に考慮

#### ハイブリッド検索
- 最も包括的な検索結果
- 精度と網羅性のバランス
- 推奨される検索方法

### 高度な機能

#### 検索履歴
- 過去の検索クエリを保存
- ワンクリックで再検索
- 頻繁な検索の効率化

#### ブックマーク
- 重要なドキュメントをブックマーク
- 素早いアクセス
- カテゴリ別整理

#### エクスポート
- 検索結果のエクスポート
- CSV、JSON形式対応
- レポート作成に活用

## 設定とカスタマイズ

### 基本設定
- 検索対象フォルダの管理
- 検索タイムアウトの設定
- インデックス更新頻度

### 表示設定
- テーマの選択
- フォントサイズの調整
- レイアウトのカスタマイズ

### パフォーマンス設定
- キャッシュサイズの調整
- 同時処理数の設定
- メモリ使用量の制限

## ベストプラクティス

### 効率的な検索
1. 具体的なキーワードから開始
2. 結果が多すぎる場合はフィルターを使用
3. セマンティック検索で関連文書を発見

### ファイル管理
1. 検索対象フォルダを適切に整理
2. ファイル名に意味のある名前を付ける
3. 定期的な不要ファイルの削除

### パフォーマンス最適化
1. 検索対象を必要最小限に限定
2. 大きなファイルは分割を検討
3. 定期的なインデックスの最適化

## FAQ

### Q: 検索が遅いのですが？
A: 以下を確認してください：
- 検索対象ファイル数
- 利用可能メモリ
- ディスクの空き容量

### Q: 特定のファイルが検索されません
A: 以下を確認してください：
- ファイル形式が対応しているか
- ファイルが破損していないか
- インデックスが最新か

### Q: セマンティック検索の精度を上げるには？
A: 以下を試してください：
- より具体的な質問文を使用
- 専門用語を含める
- 複数の表現で検索

## 技術仕様

### システム要件
- OS: Windows 10/11 (64-bit)
- CPU: Intel Core i3以上推奨
- メモリ: 4GB以上（8GB推奨）
- ストレージ: 2GB以上の空き容量

### 対応言語
- 日本語
- 英語
- その他の言語（部分的サポート）

### セキュリティ
- すべての処理はローカルで実行
- 外部サーバーへのデータ送信なし
- プライバシー完全保護
"""

    with open(docs_dir / "user_manual.md", 'w', encoding='utf-8') as f:
        f.write(user_manual)

    logger.info("ユーザードキュメントを作成しました")


def main():
    """
    メインビルド処理
    """
    logger.info("DocMind Windowsビルドプロセスを開始します")

    try:
        # 1. 要件チェック
        if not check_requirements():
            logger.error("要件チェックに失敗しました")
            return 1

        # 2. ビルドディレクトリのクリーンアップ
        clean_build_directories()

        # 3. アセットファイルの作成
        create_assets()

        # 4. デフォルト設定ファイルの作成
        create_default_config()

        # 5. PyInstallerでビルド
        if not run_pyinstaller():
            logger.error("PyInstallerビルドに失敗しました")
            return 1

        # 6. 配布用ファイルの準備
        prepare_distribution()

        # 7. インストーラースクリプトの作成
        create_installer_script()

        # 8. ドキュメントの作成
        create_documentation()

        logger.info("ビルドプロセスが正常に完了しました")
        logger.info(f"配布ファイル: {INSTALLER_DIR}")

        return 0

    except Exception as e:
        logger.error(f"ビルドプロセス中にエラーが発生しました: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
