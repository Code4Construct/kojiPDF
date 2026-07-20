; Inno Setup script for kojiPDF v2.4.0
; Nuitka output folder: ..\kojiPDFv2.dist

#define MyAppName "kojiPDF"
#define MyAppVersion "2.4.0"
#define MyAppPublisher "Code4Construct"
#define MyAppURL "https://github.com/Code4Construct/kojiPDF"
#define MyAppExeName "kojiPDFv2.exe"

[Setup]
; Keep this AppId stable for future updates of the same application.
AppId={{E0771E9F-AD69-4942-9444-DC8684390BC6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
UsePreviousAppDir=no
DisableDirPage=no
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\assets\icons\smallicon_v2.ico
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=output
OutputBaseFilename={#MyAppName}_Setup_{#MyAppVersion}
Compression=zip
SolidCompression=no
WizardStyle=modern

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\kojiPDFv2.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; IconIndex: 0
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; IconIndex: 0; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\README.md"; Description: "Open README.md"; Flags: shellexec postinstall skipifsilent unchecked
