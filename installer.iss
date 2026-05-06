; ACAS Pro Installer Script
; Inno Setup Script for professional Windows installer

#define MyAppName "ACAS Pro"
#define MyAppVersion "4.0.0"
#define MyAppPublisher "ACAS Technology"
#define MyAppURL "https://acas-tech.com"
#define MyAppExeName "ACAS-Pro.exe"

[Setup]
AppId={{ACAS-PRO-2026-ENTERPRISE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/support
AppUpdatesURL={#MyAppURL}/updates
DefaultDirName={autopf}\ACAS-Pro
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir=installer
OutputBaseFilename=ACAS-Pro-Setup-4.0.0
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "dist\ACAS-Pro\ACAS-Pro.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "src\*"; DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
