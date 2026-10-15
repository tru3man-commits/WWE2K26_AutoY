#define AppName "WWE 2K26 AutoY"
#define AppExe "WWE2K26_AutoY.exe"

[Setup]
AppId={{082C3AD4-076D-41EE-A20D-1E3A17A103ED}
AppName={#AppName}
AppVersion=0.2.2
AppPublisher=AutoY
DefaultDirName={autopf}\WWE2K26_AutoY
DefaultGroupName={#AppName}
OutputDir=..\output
OutputBaseFilename=WWE2K26_AutoY_Setup
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.19041
PrivilegesRequired=admin
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
SetupLogging=yes
CloseApplications=yes
AppMutex=Local\WWE2K26AutoY.Managed
UninstallDisplayIcon={app}\{#AppExe}
InfoBeforeFile=..\INSTALL_INFO.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\WWE2K26_AutoY\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "redist\HidHide_1.5.230_x64.exe"; Flags: dontcopy
Source: "redist\ViGEmBus_1.22.0_x64_x86_arm64.exe"; Flags: dontcopy
Source: "redist\verified-downloads.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Restore controller"; Filename: "{app}\{#AppExe}"; Parameters: "--restore"
Name: "{group}\User guide"; Filename: "{app}\USER_GUIDE.pdf"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch AutoY"; Flags: nowait postinstall skipifsilent runasoriginaluser; Check: CanLaunch

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "WWE2K26_AutoY_Recovery"; Flags: dontcreatekey uninsdeletevalue

[Code]
var
  InstalledDriver: Boolean;

function HasService(Name: String): Boolean;
begin
  Result := RegKeyExists(HKLM, 'SYSTEM\CurrentControlSet\Services\' + Name);
end;

function HasHidHide: Boolean;
begin
  Result := HasService('HidHide') and
    (FileExists(ExpandConstant('{pf64}\Nefarius Software Solutions\HidHide\HidHideCLI.exe')) or
     FileExists(ExpandConstant('{pf64}\Nefarius Software Solutions\HidHide\x64\HidHideCLI.exe')));
end;

function InstallDriver(FileName, ServiceName: String): String;
var
  Code: Integer;
begin
  Result := '';
  ExtractTemporaryFile(FileName);
  { Use the official interactive installer, retaining its license and reboot UI. }
  if not Exec(ExpandConstant('{tmp}\') + FileName, '', '', SW_SHOWNORMAL, ewWaitUntilTerminated, Code) then
    Result := 'Could not launch ' + FileName
  else if (Code <> 0) and (Code <> 3010) and (Code <> 1641) then
    Result := 'Driver installation did not complete (exit code ' + IntToStr(Code) + '). Retry Setup.'
  else if not HasService(ServiceName) then
    Result := 'Driver installation was cancelled or incomplete. Retry Setup and finish the driver installer.'
  else
    InstalledDriver := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if not HasService('ViGEmBus') then begin
    Result := InstallDriver('ViGEmBus_1.22.0_x64_x86_arm64.exe', 'ViGEmBus');
    if Result <> '' then exit;
  end;
  if not HasHidHide then begin
    Result := InstallDriver('HidHide_1.5.230_x64.exe', 'HidHide');
    if Result <> '' then exit;
    if not HasHidHide then
      Result := 'The HidHide command-line client is missing. Repair HidHide, then retry Setup.';
  end;
end;

function NeedRestart: Boolean;
begin
  Result := InstalledDriver;
end;

function CanLaunch: Boolean;
begin
  Result := not InstalledDriver;
end;

function InitializeUninstall: Boolean;
var
  Code: Integer;
begin
  Result := Exec(ExpandConstant('{app}\{#AppExe}'), '--restore-silent', '', SW_HIDE, ewWaitUntilTerminated, Code);
  if Result then Result := (Code = 0);
  if not Result then
    MsgBox('Close AutoY and HidHide Configuration Client, then retry uninstall. Controller recovery must complete first.', mbError, MB_OK);
end;
