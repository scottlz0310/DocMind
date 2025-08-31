@echo off
REM DocMind スタートアップスクリプト
REM このスクリプトはDocMindアプリケーションを起動します

echo DocMindを起動中...

REM データディレクトリの作成
if not exist "%USERPROFILE%\DocMind" (
    mkdir "%USERPROFILE%\DocMind"
    echo データディレクトリを作成しました: %USERPROFILE%\DocMind
)

REM アプリケーションの起動
start "" "%~dp0DocMind.exe"

echo DocMindが起動しました
pause
