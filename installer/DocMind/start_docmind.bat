@echo off
REM DocMind �X�^�[�g�A�b�v�X�N���v�g
REM ���̃X�N���v�g��DocMind�A�v���P�[�V�������N�����܂�

echo DocMind���N����...

REM �f�[�^�f�B���N�g���̍쐬
if not exist "%USERPROFILE%\DocMind" (
    mkdir "%USERPROFILE%\DocMind"
    echo �f�[�^�f�B���N�g�����쐬���܂���: %USERPROFILE%\DocMind
)

REM �A�v���P�[�V�����̋N��
start "" "%~dp0DocMind.exe"

echo DocMind���N�����܂���
pause
