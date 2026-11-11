; Instalador de EmuLinks (Inno Setup 6). No se compila a mano: lo llama
; scripts/build.py pasando /DAppVersion /DArch /DMinWin /DSourceDir /DOutputDir
; /DOutputName /DPublisher. SourceDir es la carpeta --standalone de Nuitka.
; Un instalador por línea y arquitectura (win-x64, win7-x64, win7-x86).
; Instala por usuario sin pedir admin (EmuLinks no lo necesita); el diálogo deja
; elegir "para todos". La desinstalación NO borra la configuración ni la carpeta
; compartida con los datos de los emuladores.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef Arch
  #define Arch "x64"
#endif
#ifndef MinWin
  #define MinWin "10.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\build\nuitka\main.dist"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist\release"
#endif
#ifndef Publisher
  #define Publisher "EstebanKZL"
#endif
#ifndef OutputName
  #define OutputName "EmuLinks-setup"
#endif

#define AppName "EmuLinks"
#define AppExe  "EmuLinks.exe"

[Setup]
; AppId fijo: NO cambiarlo nunca, es lo que permite actualizar sobre una instalación anterior.
AppId={{6B0E3C1A-52F4-4C1E-9E1D-EB0E1A7C5D21}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#Publisher}
AppContact=89585806+EstebanKZL@users.noreply.github.com
AppPublisherURL=https://github.com/EstebanKZL/EmuLinks
AppSupportURL=https://github.com/EstebanKZL/EmuLinks/issues
AppUpdatesURL=https://github.com/EstebanKZL/EmuLinks/releases
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
SetupIconFile=..\assets\icon.ico
OutputDir={#OutputDir}
OutputBaseFilename={#OutputName}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#Publisher}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
MinVersion={#MinWin}
CloseApplications=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
#if Arch == "x64"
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
#endif

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; Hasta la 6.5 el programa venía de PyInstaller (carpeta _internal): se borra al
; actualizar para que no queden DLL de Qt viejas junto a las de Nuitka.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
