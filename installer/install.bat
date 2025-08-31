@echo off
REM DocMind インストーラー
REM このスクリプトはDocMindアプリケーションをインストールします

echo DocMindインストーラーへようこそ
echo.

REM インストール先ディレクトリの設定
set "INSTALL_DIR=%PROGRAMFILES%\DocMind"
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
xcopy /E /I /Y "DocMind\*" "%INSTALL_DIR%\"
if %errorLevel% neq 0 (
    echo ファイルのコピーに失敗しました
    pause
    exit /b 1
)

REM スタートメニューショートカットの作成
echo スタートメニューショートカットを作成中...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\DocMind.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\DocMind.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'DocMind - ローカルAI搭載ドキュメント検索'; $Shortcut.Save()"

REM デスクトップショートカットの作成確認
set /p desktop_shortcut="デスクトップにショートカットを作成しますか？ (Y/n): "
if /i not "%desktop_shortcut%"=="n" (
    echo デスクトップショートカットを作成中...
    powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\DocMind.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\DocMind.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'DocMind - ローカルAI搭載ドキュメント検索'; $Shortcut.Save()"
)

REM レジストリエントリの作成（アンインストール情報）
echo アンインストール情報を登録中...
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DocMind" /v "DisplayName" /t REG_SZ /d "DocMind" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DocMind" /v "DisplayVersion" /t REG_SZ /d "1.0.0" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DocMind" /v "Publisher" /t REG_SZ /d "DocMind Project" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DocMind" /v "InstallLocation" /t REG_SZ /d "%INSTALL_DIR%" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DocMind" /v "UninstallString" /t REG_SZ /d "%INSTALL_DIR%\uninstall.bat" /f

echo.
echo インストールが完了しました！
echo DocMindはスタートメニューまたはデスクトップから起動できます。
echo.
pause
