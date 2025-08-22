; DocMind Inno Setup インストーラー設定ファイル
; このファイルはInno Setupを使用してプロフェッショナルなWindowsインストーラーを作成します

#define MyAppName "DocMind"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DocMind Project"
#define MyAppURL "https://github.com/docmind/docmind"
#define MyAppExeName "DocMind.exe"
#define MyAppDescription "ローカルAI搭載ドキュメント検索アプリケーション"

[Setup]
; アプリケーション基本情報
AppId={{B8F5E5A1-2C3D-4E5F-6789-ABCDEF123456}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) 2024 {#MyAppPublisher}

; インストール設定
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
InfoBeforeFile=..\installer\docs\install_guide.md
OutputDir=..\installer
OutputBaseFilename=DocMind_Setup_v{#MyAppVersion}
SetupIconFile=..\assets\docmind.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; システム要件
MinVersion=10.0
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; 権限設定
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "associate"; Description: "ドキュメントファイルとの関連付け"; GroupDescription: "ファイル関連付け:"; Flags: unchecked

[Files]
; メインアプリケーション
Source: "..\dist\DocMind.exe"; DestDir: "{app}"; Flags: ignoreversion
; 設定ファイル
Source: "..\config\default_config.json"; DestDir: "{app}\config"; Flags: ignoreversion
; ドキュメント
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; DestName: "README.txt"; Flags: ignoreversion
Source: "..\installer\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
; アセット
Source: "..\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists(ExpandConstant('{#SourcePath}\..\assets'))

[Icons]
; スタートメニューアイコン
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; デスクトップアイコン
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"
; クイック起動アイコン
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; アプリケーション情報をレジストリに登録
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

; ファイル関連付け（オプション）
Root: HKCR; Subkey: ".docmind"; ValueType: string; ValueName: ""; ValueData: "DocMindProject"; Flags: uninsdeletevalue; Tasks: associate
Root: HKCR; Subkey: "DocMindProject"; ValueType: string; ValueName: ""; ValueData: "DocMind Project File"; Flags: uninsdeletekey; Tasks: associate
Root: HKCR; Subkey: "DocMindProject\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: associate
Root: HKCR; Subkey: "DocMindProject\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associate

[Run]
; インストール後の実行オプション
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; アンインストール時の処理
Filename: "{cmd}"; Parameters: "/C taskkill /f /im {#MyAppExeName} /t"; Flags: runhidden

[UninstallDelete]
; アンインストール時に削除するファイル
Type: filesandordirs; Name: "{userappdata}\{#MyAppName}"
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"

[Code]
// カスタムインストール処理

// システム要件チェック
function InitializeSetup(): Boolean;
var
  Version: TWindowsVersion;
  ResultCode: Integer;
begin
  Result := True;
  
  // Windows 10以降かチェック
  GetWindowsVersionEx(Version);
  if Version.Major < 10 then
  begin
    MsgBox('このアプリケーションはWindows 10以降が必要です。', mbError, MB_OK);
    Result := False;
    Exit;
  end;
  
  // .NET Framework 4.8以降の確認（PySide6の要件）
  if not RegKeyExists(HKLM, 'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full') then
  begin
    if MsgBox('.NET Framework 4.8以降が必要です。インストールを続行しますか？', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
      Exit;
    end;
  end;
  
  // 利用可能ディスク容量のチェック（最低2GB）
  if GetSpaceOnDisk(ExtractFileDrive(ExpandConstant('{app}')), False, nil, nil, nil) < 2147483648 then
  begin
    MsgBox('インストールには最低2GBの空きディスク容量が必要です。', mbError, MB_OK);
    Result := False;
    Exit;
  end;
end;

// インストール前の準備
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
  begin
    // 既存のプロセスを終了
    Exec('taskkill', '/f /im {#MyAppExeName} /t', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
  
  if CurStep = ssPostInstall then
  begin
    // ユーザーデータディレクトリの作成
    CreateDir(ExpandConstant('{userappdata}\{#MyAppName}'));
    CreateDir(ExpandConstant('{userappdata}\{#MyAppName}\logs'));
    CreateDir(ExpandConstant('{userappdata}\{#MyAppName}\data'));
    
    // 初期設定ファイルのコピー
    if FileExists(ExpandConstant('{app}\config\default_config.json')) then
    begin
      if not FileExists(ExpandConstant('{userappdata}\{#MyAppName}\config.json')) then
      begin
        FileCopy(ExpandConstant('{app}\config\default_config.json'), 
                ExpandConstant('{userappdata}\{#MyAppName}\config.json'), False);
      end;
    end;
  end;
end;

// アンインストール前の確認
function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  
  // アプリケーションプロセスの終了
  Exec('taskkill', '/f /im {#MyAppExeName} /t', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  // ユーザーデータの削除確認
  if DirExists(ExpandConstant('{userappdata}\{#MyAppName}')) then
  begin
    if MsgBox('ユーザーデータ（設定、ログ、インデックス）も削除しますか？' + #13#10 + 
              '削除しない場合、再インストール時に設定が復元されます。', 
              mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    begin
      DelTree(ExpandConstant('{userappdata}\{#MyAppName}'), True, True, True);
    end;
  end;
end;

// カスタムページの追加（設定オプション）
var
  ConfigPage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  // 設定オプションページの作成
  ConfigPage := CreateInputOptionPage(wpSelectTasks,
    '初期設定', 'DocMindの初期設定を選択してください',
    '以下のオプションを選択してください：',
    True, False);
    
  ConfigPage.Add('初回起動時に自動的にドキュメントフォルダをスキャン');
  ConfigPage.Add('Windows起動時にDocMindを自動起動');
  ConfigPage.Add('使用統計の匿名収集に協力（プライバシーは保護されます）');
  
  // デフォルト値の設定
  ConfigPage.Values[0] := True;
  ConfigPage.Values[1] := False;
  ConfigPage.Values[2] := False;
end;

// 設定の適用
procedure CurPageChanged(CurPageID: Integer);
var
  ConfigFile: string;
  ConfigContent: TStringList;
begin
  if CurPageID = wpFinished then
  begin
    // 設定ファイルの更新
    ConfigFile := ExpandConstant('{userappdata}\{#MyAppName}\config.json');
    if FileExists(ConfigFile) then
    begin
      ConfigContent := TStringList.Create;
      try
        ConfigContent.LoadFromFile(ConfigFile);
        
        // 設定の適用（簡易的なJSON更新）
        if ConfigPage.Values[0] then
        begin
          // 自動スキャン設定
          StringChangeEx(ConfigContent.Text, '"auto_scan": false', '"auto_scan": true', True);
        end;
        
        if ConfigPage.Values[1] then
        begin
          // 自動起動の設定
          RegWriteStringValue(HKCU, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
                             '{#MyAppName}', ExpandConstant('{app}\{#MyAppExeName}'));
        end;
        
        ConfigContent.SaveToFile(ConfigFile);
      finally
        ConfigContent.Free;
      end;
    end;
  end;
end;