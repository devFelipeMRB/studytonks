; Compile on Windows with Inno Setup 6.3+ after the PyInstaller one-folder build.
; No downloads, Python installation, administrator privilege or startup changes.
#ifndef AppVersion
  #define AppVersion "1.0.2"
#endif

[Setup]
AppId={{78BB0D3E-9A36-441D-AC4B-D49AE2384D27}
AppName=Studytonks
AppVersion={#AppVersion}
AppVerName=Studytonks {#AppVersion}
AppPublisher=devFelipeMRB
AppPublisherURL=https://github.com/devFelipeMRB/studytonks
AppSupportURL=https://github.com/devFelipeMRB/studytonks/issues
AppUpdatesURL=https://github.com/devFelipeMRB/studytonks/releases
DefaultDirName={localappdata}\Programs\Studytonks
DefaultGroupName=Studytonks
PrivilegesRequired=lowest
MinVersion=10.0.17763
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableDirPage=no
DisableProgramGroupPage=yes
AllowNoIcons=yes
UsePreviousAppDir=yes
UninstallDisplayName=Studytonks
UninstallDisplayIcon={app}\Studytonks.exe
SetupIconFile=..\app\assets\studytonks.ico
InfoBeforeFile=install-info.txt
OutputDir=..\dist\release
OutputBaseFilename=Studytonks-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
CloseApplications=yes
CloseApplicationsFilter=Studytonks.exe
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\Studytonks\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Studytonks"; Filename: "{app}\Studytonks.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Studytonks"; Filename: "{app}\Studytonks.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Studytonks.exe"; Description: "{cm:LaunchProgram,Studytonks}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ExistingCommand: String;
  Executable: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    { Remove only this installation's startup entry, previously enabled in-app. }
    { There is deliberately no [Registry] entry that enables startup on install. }
    Executable := ExpandConstant('{app}\Studytonks.exe');
    if RegQueryStringValue(HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Run',
      'Studytonks', ExistingCommand) then
    begin
      if (CompareText(ExistingCommand, '"' + Executable + '"') = 0) or
         (CompareText(ExistingCommand, Executable) = 0) then
        RegDeleteValue(HKCU,
          'Software\Microsoft\Windows\CurrentVersion\Run', 'Studytonks');
    end;
  end;
  { No AppData deletion: notes, assessments, settings and backups survive. }
end;
