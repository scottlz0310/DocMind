@echo off
REM DocMind �A���C���X�g�[���X�N���v�g
REM ���̃X�N���v�g��DocMind�A�v���P�[�V�������A���C���X�g�[�����܂�

echo DocMind���A���C���X�g�[����...

REM �v���Z�X�̏I��
taskkill /f /im DocMind.exe 2>nul

REM ���[�U�[�f�[�^�̍폜�m�F
set /p confirm="���[�U�[�f�[�^���폜���܂����H (y/N): "
if /i "%confirm%"=="y" (
    if exist "%USERPROFILE%\DocMind" (
        rmdir /s /q "%USERPROFILE%\DocMind"
        echo ���[�U�[�f�[�^���폜���܂���
    )
)

REM �X�^�[�g���j���[�V���[�g�J�b�g�̍폜
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\DocMind.lnk" (
    del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\DocMind.lnk"
    echo �X�^�[�g���j���[�V���[�g�J�b�g���폜���܂���
)

REM �f�X�N�g�b�v�V���[�g�J�b�g�̍폜
if exist "%USERPROFILE%\Desktop\DocMind.lnk" (
    del "%USERPROFILE%\Desktop\DocMind.lnk"
    echo �f�X�N�g�b�v�V���[�g�J�b�g���폜���܂���
)

echo �A���C���X�g�[�����������܂���
pause
