#define MyAppName "MediaLens"
#define MyAppVersion "v1.0.22" ; Source of Truth: \VERSION
#define MyAppPublisher "G1enB1and"
#define MyAppExeName "MediaLens.exe"

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
Source: "dist\{#MyAppName}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Open MediaLens After Installing Setup"; Flags: nowait postinstall skipifsilent
