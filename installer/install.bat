@echo off
REM DocMind �C���X�g�[���[
REM ���̃X�N���v�g��DocMind�A�v���P�[�V�������C���X�g�[�����܂�

echo DocMind�C���X�g�[���[�ւ悤����
echo.

REM �C���X�g�[����f�B���N�g���̐ݒ�
set "INSTALL_DIR=%PROGRAMFILES%\DocMind"
set /p custom_dir="�C���X�g�[���� (�f�t�H���g: %INSTALL_DIR%): "
if not "%custom_dir%"=="" set "INSTALL_DIR=%custom_dir%"

echo.
echo �C���X�g�[����: %INSTALL_DIR%
echo.

REM �Ǘ��Ҍ����̊m�F
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ���̃C���X�g�[���[�͊Ǘ��Ҍ����Ŏ��s����K�v������܂�
    echo �E�N���b�N���āu�Ǘ��҂Ƃ��Ď��s�v��I�����Ă�������
    pause
    exit /b 1
)

REM �C���X�g�[���f�B���N�g���̍쐬
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo �C���X�g�[���f�B���N�g�����쐬���܂���
)

REM �t�@�C���̃R�s�[
echo �t�@�C�����R�s�[��...
xcopy /E /I /Y "DocMind\*" "%INSTALL_DIR%\"
if %errorLevel% neq 0 (
    echo �t�@�C���̃R�s�[�Ɏ��s���܂���
    pause
    exit /b 1
)

REM �X�^�[�g���j���[�V���[�g�J�b�g�̍쐬
echo �X�^�[�g���j���[�V���[�g�J�b�g���쐬��...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\DocMind.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\DocMind.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'DocMind - ���[�J��AI���ڃh�L�������g����'; $Shortcut.Save()"

REM �f�X�N�g�b�v�V���[�g�J�b�g�̍쐬�m�F
set /p desktop_shortcut="�f�X�N�g�b�v�ɃV���[�g�J�b�g���쐬���܂����H (Y/n): "
if /i not "%desktop_shortcut%"=="n" (
    echo �f�X�N�g�b�v�V���[�g�J�b�g���쐬��...
    powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\DocMind.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\DocMind.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'DocMind - ���[�J��AI���ڃh�L�������g����'; $Shortcut.Save()"
)

REM ���W�X�g���G���g���̍쐬�i�A���C���X�g�[�����j
echo �A���C���X�g�[������o�^��...
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DocMind" /v "DisplayName" /t REG_SZ /d "DocMind" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DocMind" /v "DisplayVersion" /t REG_SZ /d "1.0.0" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DocMind" /v "Publisher" /t REG_SZ /d "DocMind Project" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DocMind" /v "InstallLocation" /t REG_SZ /d "%INSTALL_DIR%" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\DocMind" /v "UninstallString" /t REG_SZ /d "%INSTALL_DIR%\uninstall.bat" /f

echo.
echo �C���X�g�[�����������܂����I
echo DocMind�̓X�^�[�g���j���[�܂��̓f�X�N�g�b�v����N���ł��܂��B
echo.
pause
