#define MyAppName "MediaLens"
#define MyAppVersion "v1.2.6" ; Source of Truth: \VERSION
#define MyAppPublisher "MediaLens"
#define MyLegacyAppName "MediaManagerX"
#define MyLegacyPublisher "G1enB1and"
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
UsePreviousAppDir=no
; Allow user to choose "Current User" vs "All Users" (requires admin)
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
RestartApplications=no
OutputDir=.\
OutputBaseFilename=MediaLens_Setup
SetupIconFile=native\mediamanagerx_app\web\MediaLens-Logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyBuildSourceDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyBuildSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
Type: filesandordirs; Name: "{app}\*"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Open MediaLens After Installing Setup"; Flags: nowait postinstall skipifsilent

[Code]
var
  CleanupUninstallData: Boolean;
  KeepUninstallDatabase: Boolean;
  KeepUninstallSettings: Boolean;
  KeepUninstallRecycleBin: Boolean;
  KeepUninstallThumbnails: Boolean;
  KeepUninstallLocalAiModels: Boolean;
  KeepUninstallAiRuntimes: Boolean;
  KeepUninstallDebugLogs: Boolean;
  KeepUninstallImportBackups: Boolean;
  KeepUninstallLegacyData: Boolean;
  KeepUninstallOtherData: Boolean;

function SamePath(Left, Right: String): Boolean;
begin
  Result := CompareText(RemoveBackslash(Left), RemoveBackslash(Right)) = 0;
end;

procedure EnsureDir(Path: String);
begin
  if not DirExists(Path) then
    ForceDirectories(Path);
end;

function UniqueLegacyTarget(Path: String): String;
var
  DotPos, Index: Integer;
  Base, Ext, Candidate: String;
begin
  DotPos := 0;
  for Index := Length(Path) downto 1 do
  begin
    if Copy(Path, Index, 1) = '.' then
    begin
      DotPos := Index;
      Break;
    end;
    if Copy(Path, Index, 1) = '\' then
      Break;
  end;

  if DotPos > 0 then
  begin
    Base := Copy(Path, 1, DotPos - 1);
    Ext := Copy(Path, DotPos, Length(Path) - DotPos + 1);
  end
  else
  begin
    Base := Path;
    Ext := '';
  end;

  for Index := 1 to 999 do
  begin
    Candidate := Base + '.legacy-' + IntToStr(Index) + Ext;
    if not FileExists(Candidate) and not DirExists(Candidate) then
    begin
      Result := Candidate;
      Exit;
    end;
  end;

  Result := Base + '.legacy' + Ext;
end;

function CopyTreeMerge(Source, Dest: String): Boolean;
var
  FindRec: TFindRec;
  SourcePath, DestPath, CopyPath: String;
begin
  Result := True;
  if not DirExists(Source) then
    Exit;
  if SamePath(Source, Dest) then
    Exit;

  EnsureDir(Dest);
  if FindFirst(AddBackslash(Source) + '*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
        begin
          SourcePath := AddBackslash(Source) + FindRec.Name;
          DestPath := AddBackslash(Dest) + FindRec.Name;
          if FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY <> 0 then
          begin
            if not CopyTreeMerge(SourcePath, DestPath) then
              Result := False;
          end
          else
          begin
            CopyPath := DestPath;
            if FileExists(CopyPath) or DirExists(CopyPath) then
              CopyPath := UniqueLegacyTarget(CopyPath);
            EnsureDir(ExtractFilePath(CopyPath));
            if not CopyFile(SourcePath, CopyPath, True) then
              Result := False;
          end;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

procedure MigrateLegacyAppData;
var
  Target, LegacyRoot, LegacyMediaManagerX, LegacyMediaLens: String;
begin
  Target := ExpandConstant('{userappdata}\{#MyAppName}');
  LegacyRoot := ExpandConstant('{userappdata}\{#MyLegacyPublisher}');
  LegacyMediaManagerX := AddBackslash(LegacyRoot) + '{#MyLegacyAppName}';
  LegacyMediaLens := AddBackslash(LegacyRoot) + '{#MyAppName}';

  EnsureDir(Target);
  if CopyTreeMerge(LegacyMediaManagerX, Target) then
    DelTree(LegacyMediaManagerX, True, True, True);
  if CopyTreeMerge(LegacyMediaLens, Target) then
    DelTree(LegacyMediaLens, True, True, True);
  RemoveDir(LegacyRoot);
end;

procedure DeleteLegacyInstallDir(Path: String);
begin
  if DirExists(Path) and not SamePath(Path, ExpandConstant('{app}')) then
    DelTree(Path, True, True, True);
end;

procedure DeleteLegacyShortcuts;
begin
  DeleteFile(ExpandConstant('{autoprograms}\{#MyLegacyAppName}.lnk'));
  DeleteFile(ExpandConstant('{autodesktop}\{#MyLegacyAppName}.lnk'));
  DeleteFile(ExpandConstant('{userdesktop}\{#MyLegacyAppName}.lnk'));
  DeleteFile(ExpandConstant('{commondesktop}\{#MyLegacyAppName}.lnk'));
end;

function ShortcutTarget(Path: String): String;
var
  Shell, Shortcut: Variant;
begin
  Result := '';
  try
    Shell := CreateOleObject('WScript.Shell');
    Shortcut := Shell.CreateShortcut(Path);
    Result := Shortcut.TargetPath;
  except
    Result := '';
  end;
end;

function IsLegacyShortcutTarget(Target: String): Boolean;
var
  LowerTarget, CurrentExe: String;
begin
  LowerTarget := LowerCase(Target);
  CurrentExe := LowerCase(ExpandConstant('{app}\{#MyAppExeName}'));
  Result := (Target <> '') and (CompareText(Target, CurrentExe) <> 0) and
    ((Pos('\mediamanagerx\', LowerTarget) > 0) or
     ((ExtractFileName(LowerTarget) = LowerCase('{#MyAppExeName}')) and (Pos('\medialens\', LowerTarget) > 0)));
end;

procedure RemoveStaleTaskbarShortcuts;
var
  TaskbarDir, ShortcutPath, Target: String;
  FindRec: TFindRec;
begin
  TaskbarDir := ExpandConstant('{userappdata}\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar');
  if not DirExists(TaskbarDir) then
    Exit;

  if FindFirst(AddBackslash(TaskbarDir) + '*.lnk', FindRec) then
  begin
    try
      repeat
        ShortcutPath := AddBackslash(TaskbarDir) + FindRec.Name;
        Target := ShortcutTarget(ShortcutPath);
        if IsLegacyShortcutTarget(Target) then
          DeleteFile(ShortcutPath);
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

procedure CleanupLegacyInstalls;
begin
  DeleteLegacyInstallDir(ExpandConstant('{autopf}\{#MyLegacyAppName}'));
  DeleteLegacyInstallDir(ExpandConstant('{autopf32}\{#MyLegacyAppName}'));
  DeleteLegacyInstallDir(ExpandConstant('{localappdata}\Programs\{#MyLegacyAppName}'));
  DeleteLegacyInstallDir(ExpandConstant('{localappdata}\Programs\{#MyAppName}'));
  DeleteLegacyShortcuts();
  RemoveStaleTaskbarShortcuts();
end;

function PromptKeepUninstallCategory(Title, Description: String): Boolean;
begin
  Result := MsgBox(
    Title + #13#10#13#10 +
    Description + #13#10#13#10 +
    'Choose Yes to keep this data after uninstalling MediaLens.' + #13#10 +
    'Choose No to delete it now.',
    mbConfirmation,
    MB_YESNO
  ) = IDYES;
end;

function StartsWithText(Value, Prefix: String): Boolean;
begin
  Result := Copy(Value, 1, Length(Prefix)) = Prefix;
end;

function ContainsText(Value, Token: String): Boolean;
begin
  Result := Pos(Token, Value) > 0;
end;

function IsLegacyAppDataEntry(Name: String): Boolean;
var
  LowerName: String;
begin
  LowerName := LowerCase(Name);
  Result :=
    StartsWithText(LowerName, 'mediamanagerx') or
    ContainsText(LowerName, '.legacy-') or
    ContainsText(LowerName, '.legacy');
end;

function ShouldKeepAppDataEntry(Name: String): Boolean;
var
  LowerName: String;
begin
  LowerName := LowerCase(Name);

  if (LowerName = 'medialens.db') then
  begin
    Result := KeepUninstallDatabase;
    Exit;
  end;

  if (LowerName = 'settings.ini') or (LowerName = 'settings') then
  begin
    Result := KeepUninstallSettings;
    Exit;
  end;

  if (LowerName = 'recyclebin') or (LowerName = 'recycle_bin.sqlite') then
  begin
    Result := KeepUninstallRecycleBin;
    Exit;
  end;

  if (LowerName = 'thumbs') then
  begin
    Result := KeepUninstallThumbnails;
    Exit;
  end;

  if (LowerName = 'local_ai_models') then
  begin
    Result := KeepUninstallLocalAiModels;
    Exit;
  end;

  if (LowerName = 'ai-runtimes') or (LowerName = 'python') or (LowerName = 'python-bootstrap') then
  begin
    Result := KeepUninstallAiRuntimes;
    Exit;
  end;

  if (LowerName = 'debugging-logs') or (LowerName = 'app.log') or (LowerName = 'faulthandler.log') or (LowerName = 'crash-reports') then
  begin
    Result := KeepUninstallDebugLogs;
    Exit;
  end;

  if (LowerName = 'import-backups') then
  begin
    Result := KeepUninstallImportBackups;
    Exit;
  end;

  if IsLegacyAppDataEntry(Name) then
  begin
    Result := KeepUninstallLegacyData;
    Exit;
  end;

  Result := KeepUninstallOtherData;
end;

procedure DeletePath(Path: String);
begin
  if DirExists(Path) then
    DelTree(Path, True, True, True)
  else if FileExists(Path) then
    DeleteFile(Path);
end;

procedure CleanupUnselectedMediaLensAppData;
var
  Root, EntryPath, LegacyRoot: String;
  FindRec: TFindRec;
begin
  Root := ExpandConstant('{userappdata}\{#MyAppName}');
  if DirExists(Root) then
  begin
    if FindFirst(AddBackslash(Root) + '*', FindRec) then
    begin
      try
        repeat
          if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
          begin
            EntryPath := AddBackslash(Root) + FindRec.Name;
            if not ShouldKeepAppDataEntry(FindRec.Name) then
              DeletePath(EntryPath);
          end;
        until not FindNext(FindRec);
      finally
        FindClose(FindRec);
      end;
    end;
    RemoveDir(Root);
  end;

  if not KeepUninstallLegacyData then
  begin
    LegacyRoot := ExpandConstant('{userappdata}\{#MyLegacyPublisher}');
    DeletePath(LegacyRoot);
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  CleanupUninstallData := False;

  if UninstallSilent then
    Exit;

  MsgBox(
    'MediaLens can remove its app data during uninstall.' + #13#10#13#10 +
    'You will be asked which categories to keep. Anything not selected to keep will be deleted, including legacy leftovers.',
    mbInformation,
    MB_OK
  );

  CleanupUninstallData := True;
  KeepUninstallDatabase := PromptKeepUninstallCategory(
    'Keep MediaLens database?',
    'This includes your library database, metadata, tags, collections, scan state, and review decisions.'
  );
  KeepUninstallSettings := PromptKeepUninstallCategory(
    'Keep app settings?',
    'This includes UI preferences, folder settings, scanner settings, duplicate rules, and local AI settings.'
  );
  KeepUninstallRecycleBin := PromptKeepUninstallCategory(
    'Keep MediaLens recycle bin retention?',
    'This includes recycle_bin.sqlite and retained files in the MediaLens RecycleBin folder.'
  );
  KeepUninstallThumbnails := PromptKeepUninstallCategory(
    'Keep thumbnails?',
    'This includes cached gallery thumbnails. They can be regenerated, but keeping them speeds up browsing after reinstall.'
  );
  KeepUninstallLocalAiModels := PromptKeepUninstallCategory(
    'Keep downloaded local AI models?',
    'This includes downloaded model files and model caches under local_ai_models.'
  );
  KeepUninstallAiRuntimes := PromptKeepUninstallCategory(
    'Keep local AI runtime environments?',
    'This includes ai-runtimes, the managed Python runtime, and Python bootstrap files.'
  );
  KeepUninstallDebugLogs := PromptKeepUninstallCategory(
    'Keep debugging logs and crash reports?',
    'This includes sanitized app logs, faulthandler logs, and crash reports under debugging-logs.'
  );
  KeepUninstallImportBackups := PromptKeepUninstallCategory(
    'Keep import backups?',
    'This includes local backups created before restoring a MediaLens library backup.'
  );
  KeepUninstallLegacyData := PromptKeepUninstallCategory(
    'Keep legacy MediaManagerX leftovers?',
    'This includes legacy mediamanagerx files, .legacy files, and the old G1enB1and\MediaManagerX app-data tree.'
  );
  KeepUninstallOtherData := PromptKeepUninstallCategory(
    'Keep any other MediaLens app-data files?',
    'This preserves any unrecognized files in the MediaLens app-data folder. Choose No for the cleanest uninstall.'
  );
end;

function ShouldAutoRelaunchAfterSilentInstall(): Boolean;
begin
  Result := WizardSilent and (Pos('/RELAUNCH', UpperCase(GetCmdTail)) > 0);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and CleanupUninstallData then
    CleanupUnselectedMediaLensAppData();
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
  begin
    MigrateLegacyAppData();
    CleanupLegacyInstalls();
  end;

  if (CurStep = ssPostInstall) and ShouldAutoRelaunchAfterSilentInstall() then
  begin
    ShellExec('', ExpandConstant('{app}\{#MyAppExeName}'), '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
  end;
end;
