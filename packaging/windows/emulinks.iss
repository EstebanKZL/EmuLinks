; Instalador de EmuLinks (Inno Setup 6.5+). Lo compila el CI:
;   iscc /DAppVer=6.4 /DGen=win10 /DMinVer=10.0 /DSrcX64=... /DSrcX86=... emulinks.iss
; Un instalador por generación de Windows con las dos arquitecturas adentro:
; en Windows de 64 bits instala la x64; en 32 bits, la x86.
; Instala por usuario sin pedir admin (EmuLinks no lo necesita); el diálogo
; deja elegir "para todos". La desinstalación NO borra %APPDATA%\EmuLinks
; (config) ni la carpeta compartida con los datos de los emuladores.

#ifndef AppVer
  #define AppVer "0.0"
#endif
#ifndef Gen
  #define Gen "win10"
#endif
#ifndef MinVer
  #define MinVer "10.0"
#endif

[Setup]
AppId={{6B0E3C1A-52F4-4C1E-9E1D-EB0E1A7C5D21}
AppName=EmuLinks
AppVersion={#AppVer}
AppVerName=EmuLinks {#AppVer}
AppPublisher=EstebanKZL
AppPublisherURL=https://github.com/EstebanKZL/EmuLinks
AppSupportURL=https://github.com/EstebanKZL/EmuLinks/issues
AppUpdatesURL=https://github.com/EstebanKZL/EmuLinks/releases
DefaultDirName={autopf}\EmuLinks
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion={#MinVer}
OutputDir=Output
OutputBaseFilename=EmuLinks-{#Gen}-setup
SetupIconFile=..\icon\emulinks.ico
UninstallDisplayIcon={app}\EmuLinks.exe
UninstallDisplayName=EmuLinks
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SrcX64}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: Is64BitInstallMode
Source: "{#SrcX86}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: not Is64BitInstallMode

[InstallDelete]
; al actualizar, que no queden DLL de Qt de la versión anterior
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\EmuLinks"; Filename: "{app}\EmuLinks.exe"
Name: "{autodesktop}\EmuLinks"; Filename: "{app}\EmuLinks.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EmuLinks.exe"; Description: "{cm:LaunchProgram,EmuLinks}"; Flags: nowait postinstall skipifsilent
