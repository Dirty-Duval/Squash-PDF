; Inno Setup Script for Squash PDF Compressor
; Creates a professional Windows installer
; Requires Inno Setup 6.2+ from https://jrsoftware.org/isinfo.php

#define AppName "Squash PDF Compressor"
; AppVersion is normally passed by build_installer.bat (read from src/squash/__init__.py).
#ifndef AppVersion
  #define AppVersion "2.2.1"
#endif
#define AppPublisher "ACWul"
#define AppURL "https://github.com/Dirty-Duval/Squash-PDF"
#define AppExeName "Squash.exe"
#define AppId "{{8F4D3C2B-1A5E-4B7D-9C3F-2E6A8D4B5C7E}"

[Setup]
; Basic application information
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\Squash
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=LICENSE
InfoBeforeFile=README_DIST.txt
OutputDir=dist\installer
OutputBaseFilename=SquashSetup-{#AppVersion}
SetupIconFile=assets\squash.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
WizardImageFile=assets\installer_wizard.bmp
WizardSmallImageFile=assets\installer_wizard_small.bmp
; Allow Inno Setup to close the running app automatically during updates
CloseApplications=yes
RestartApplications=yes
; Mutex registered by the running app so Inno Setup can find and close it
AppMutex=SquashPDFCompressor
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
DisableProgramGroupPage=yes
DisableWelcomePage=no

; Windows version requirements
MinVersion=10.0
OnlyBelowVersion=0

; Version information
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Installer
VersionInfoCopyright=Copyright (C) 2025-2026 {#AppPublisher}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application files
Source: "dist\Squash\Squash.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Squash\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "README_DIST.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
; Start Menu shortcuts
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{group}\README"; Filename: "{app}\README_DIST.txt"

; Desktop shortcut (optional)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Option to launch app after installation
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[InstallDelete]
; Force-delete old shortcuts before install so Windows loads fresh icon from new exe
Type: files; Name: "{autodesktop}\{#AppName}.lnk"
Type: files; Name: "{group}\{#AppName}.lnk"

[UninstallDelete]
; Clean up user data on uninstall (optional - commented out by default)
; Type: filesandordirs; Name: "{userappdata}\Squash"

[Code]
// Check if application is running before installation.
// When launched from the app's own auto-update flow (/CLOSEAPPLICATIONS flag),
// Inno Setup will have already closed the app via AppMutex before reaching here.
// This fallback handles manual double-click installs.
function InitializeSetup(): Boolean;
begin
  if CheckForMutexes('SquashPDFCompressor') then
  begin
    if MsgBox('Squash PDF Compressor is currently running.' + #13#10 +
              'Please close it before continuing, then click OK.',
              mbInformation, MB_OKCANCEL) = IDCANCEL then
    begin
      Result := False;
      Exit;
    end;
    // User clicked OK — check again; if still running, abort
    if CheckForMutexes('SquashPDFCompressor') then
    begin
      MsgBox('Squash is still running. Please close it and run setup again.',
             mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
  Result := True;
end;

// Preserve user settings during upgrade
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    // Future: Backup user settings if needed
  end;
end;

// Custom messages
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel2.Caption :=
    'This will install Squash PDF Compressor v{#AppVersion} on your computer.' + #13#10#13#10 +
    'Squash is a simple, user-friendly PDF compression tool that uses Ghostscript ' +
    'to reduce file sizes while maintaining quality.' + #13#10#13#10 +
    'All processing is done locally on your computer - no internet required!';
end;
