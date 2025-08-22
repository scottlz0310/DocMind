@echo off
REM DocMind 完全ビルドスクリプト
REM このスクリプトはDocMindの完全なビルドプロセスを実行します

echo DocMind 完全ビルドプロセスを開始します
echo.

REM 現在のディレクトリを保存
set ORIGINAL_DIR=%CD%
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM プロジェクトルートに移動
cd /d "%PROJECT_ROOT%"

echo プロジェクトルート: %PROJECT_ROOT%
echo.

REM Python環境の確認
echo Python環境を確認中...
python --version
if %errorLevel% neq 0 (
    echo Python 3.11以降がインストールされていることを確認してください
    pause
    exit /b 1
)

REM 仮想環境の確認
if not exist "venv" (
    echo 仮想環境を作成中...
    python -m venv venv
    if %errorLevel% neq 0 (
        echo 仮想環境の作成に失敗しました
        pause
        exit /b 1
    )
)

REM 仮想環境をアクティベート
echo 仮想環境をアクティベート中...
call venv\Scripts\activate.bat
if %errorLevel% neq 0 (
    echo 仮想環境のアクティベートに失敗しました
    pause
    exit /b 1
)

REM 依存関係のインストール
echo 依存関係をインストール中...
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo 依存関係のインストールに失敗しました
    pause
    exit /b 1
)

REM ビルド用依存関係のインストール
echo ビルド用依存関係をインストール中...
pip install -r build_scripts\requirements_build.txt
if %errorLevel% neq 0 (
    echo ビルド用依存関係のインストールに失敗しました
    pause
    exit /b 1
)

REM テストの実行（オプション）
set /p run_tests="テストを実行しますか？ (y/N): "
if /i "%run_tests%"=="y" (
    echo テストを実行中...
    python -m pytest tests/ -v
    if %errorLevel% neq 0 (
        echo テストが失敗しました。続行しますか？
        set /p continue="続行しますか？ (y/N): "
        if /i not "%continue%"=="y" (
            pause
            exit /b 1
        )
    )
)

REM Windowsビルドの実行
echo Windowsビルドを実行中...
python build_scripts\build_windows.py
if %errorLevel% neq 0 (
    echo Windowsビルドに失敗しました
    pause
    exit /b 1
)

REM Inno Setupインストーラーの作成（オプション）
set /p create_installer="Inno Setupインストーラーを作成しますか？ (y/N): "
if /i "%create_installer%"=="y" (
    echo Inno Setupインストーラーを作成中...
    
    REM Inno Setup コンパイラーの検索
    set INNO_COMPILER=""
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
        set INNO_COMPILER="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    ) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
        set INNO_COMPILER="C:\Program Files\Inno Setup 6\ISCC.exe"
    ) else (
        echo Inno Setup 6が見つかりません。手動でインストールしてください。
        echo https://jrsoftware.org/isinfo.php
        goto :skip_inno
    )
    
    %INNO_COMPILER% "build_scripts\docmind_installer.iss"
    if %errorLevel% neq 0 (
        echo Inno Setupインストーラーの作成に失敗しました
    ) else (
        echo Inno Setupインストーラーが正常に作成されました
    )
)
:skip_inno

REM デプロイメントテストの実行（オプション）
set /p run_deployment_test="デプロイメントテストを実行しますか？ (y/N): "
if /i "%run_deployment_test%"=="y" (
    echo デプロイメントテストを実行中...
    
    REM インストーラーファイルを検索
    set INSTALLER_FILE=""
    if exist "installer\DocMind_Setup_v1.0.0.exe" (
        set INSTALLER_FILE="installer\DocMind_Setup_v1.0.0.exe"
    ) else if exist "installer\install.bat" (
        set INSTALLER_FILE="installer\install.bat"
    ) else (
        echo インストーラーファイルが見つかりません
        goto :skip_deployment_test
    )
    
    python build_scripts\test_deployment.py %INSTALLER_FILE%
    if %errorLevel% neq 0 (
        echo デプロイメントテストで問題が発生しました
        echo 詳細はdeployment_test_report.txtを確認してください
    ) else (
        echo デプロイメントテストが正常に完了しました
    )
)
:skip_deployment_test

REM ビルド成果物の確認
echo.
echo ビルド成果物:
echo ================
if exist "dist\DocMind.exe" (
    echo ✓ 実行可能ファイル: dist\DocMind.exe
) else (
    echo ✗ 実行可能ファイルが見つかりません
)

if exist "installer\install.bat" (
    echo ✓ バッチインストーラー: installer\install.bat
) else (
    echo ✗ バッチインストーラーが見つかりません
)

if exist "installer\DocMind_Setup_v1.0.0.exe" (
    echo ✓ Inno Setupインストーラー: installer\DocMind_Setup_v1.0.0.exe
) else (
    echo - Inno Setupインストーラーは作成されませんでした
)

if exist "installer\docs" (
    echo ✓ ドキュメント: installer\docs\
) else (
    echo ✗ ドキュメントが見つかりません
)

echo.
echo ビルドプロセスが完了しました！
echo 配布ファイルは installer\ ディレクトリにあります。

REM 元のディレクトリに戻る
cd /d "%ORIGINAL_DIR%"

pause