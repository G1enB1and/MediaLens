#define MyAppName "MediaLens"
#define MyAppVersion "v1.1.15" ; Source of Truth: \VERSION
#define MyAppPublisher "G1enB1and"
#define MyAppExeName "MediaLens.exe"
#ifndef MyBuildSourceDir
  #define MyBuildSourceDir "dist\MediaLens"
#endif

[Setup]
; AppId uniquely identifies this application
AppId={{2A9E5F20-B882-4113-A5B2-6CC175D65C23}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
; Allow user to choose "Current User" vs "All Users" (requires admin)
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=.\
OutputBaseFilename=MediaLens_Setup
SetupIconFile=native\mediamanagerx_app\web\MediaLens-Logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyBuildSourceDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyBuildSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Open MediaLens After Installing Setup"; Flags: nowait postinstall skipifsilent

[Code]
function ShouldAutoRelaunchAfterSilentInstall(): Boolean;
begin
  Result := WizardSilent and (Pos('/RELAUNCH', UpperCase(GetCmdTail)) > 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if (CurStep = ssPostInstall) and ShouldAutoRelaunchAfterSilentInstall() then
  begin
    ShellExec('', ExpandConstant('{app}\{#MyAppExeName}'), '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
  end;
end;
