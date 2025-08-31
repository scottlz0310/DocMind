@echo off
REM DocMind アンインストールスクリプト
REM このスクリプトはDocMindアプリケーションをアンインストールします

echo DocMindをアンインストール中...

REM プロセスの終了
taskkill /f /im DocMind.exe 2>nul

REM ユーザーデータの削除確認
set /p confirm="ユーザーデータも削除しますか？ (y/N): "
if /i "%confirm%"=="y" (
    if exist "%USERPROFILE%\DocMind" (
        rmdir /s /q "%USERPROFILE%\DocMind"
        echo ユーザーデータを削除しました
    )
)

REM スタートメニューショートカットの削除
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\DocMind.lnk" (
    del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\DocMind.lnk"
    echo スタートメニューショートカットを削除しました
)

REM デスクトップショートカットの削除
if exist "%USERPROFILE%\Desktop\DocMind.lnk" (
    del "%USERPROFILE%\Desktop\DocMind.lnk"
    echo デスクトップショートカットを削除しました
)

echo アンインストールが完了しました
pause
