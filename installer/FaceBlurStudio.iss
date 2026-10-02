; Build with Inno Setup 6.7.3 or newer. No paid plugins or external runtimes.
#ifndef AppVersion
  #define AppVersion "1.1.28"
#endif
#ifndef PackageDir
  #define PackageDir "..\dist\FaceBlur Studio"
#endif
#define AppName "FaceBlur Studio"
#define AppExe "FaceBlur Studio.exe"

[Setup]
AppId={{D214BBF1-A626-4D17-8DD9-63FE6AD6EC03}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=@sirdimitry
AppPublisherURL=https://x.com/sirdimitry
AppSupportURL=https://github.com/sirdimitry/FaceBlur-Studio/issues
AppUpdatesURL=https://github.com/sirdimitry/FaceBlur-Studio/releases
DefaultDirName={localappdata}\Programs\FaceBlur Studio
DefaultGroupName=FaceBlur Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist\installer
OutputBaseFilename=FaceBlur-Studio-{#AppVersion}-Windows-Setup
SetupIconFile=..\app_icon.ico
UninstallDisplayIcon={app}\_internal\app_icon.ico
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern dark windows11 includetitlebar
WizardSizePercent=110
WizardImageFile=..\assets\installer\wizard-sidebar.png
WizardSmallImageFile=..\assets\installer\wizard-mark.png
WizardImageBackColor=#101525
WizardSmallImageBackColor=#101525
WizardBackColor=#101525
WizardBackImageFile=..\assets\installer\wizard-background.png
WizardBackImageOpacity=255
DisableWelcomePage=no
DisableReadyPage=no
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
VersionInfoCompany=@sirdimitry
VersionInfoDescription=FaceBlur Studio branded installer
VersionInfoProductName={#AppName}
VersionInfoVersion={#AppVersion}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#PackageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\installer\progress-banner.png"; Flags: dontcopy

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; IconFilename: "{app}\_internal\app_icon.ico"; AppUserModelID: "FaceBlurStudio.Desktop"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; IconFilename: "{app}\_internal\app_icon.ico"; Tasks: desktopicon; AppUserModelID: "FaceBlurStudio.Desktop"

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[CustomMessages]
russian.WelcomeLabel1=Добро пожаловать в FaceBlur Studio
russian.WelcomeLabel2=Ваши видео. Ваша приватность.%n%nАвтоматическое размытие лиц с обработкой на вашем компьютере.%n%nУстановщик добавит FaceBlur Studio {#AppVersion} и всё необходимое для работы. Отдельная установка Python не требуется.
russian.FinishedHeadingLabel=Всё готово к работе
russian.FinishedLabel=FaceBlur Studio установлен.%n%nДобавьте видео, найдите лица и выберите, кого скрыть. Обработка видео выполняется локально.
english.WelcomeLabel1=Welcome to FaceBlur Studio
english.WelcomeLabel2=Your videos. Your privacy.%n%nAutomatic face blurring, processed on your computer.%n%nSetup will install FaceBlur Studio {#AppVersion} and everything it needs. No separate Python installation is required.
english.FinishedHeadingLabel=Ready when you are
english.FinishedLabel=FaceBlur Studio is installed.%n%nAdd a video, find faces and choose who to hide. Video processing happens locally.

[Code]
var
  AuthorLink: TNewStaticText;
  ProgressBanner: TBitmapImage;

procedure OpenAuthor(Sender: TObject);
var
  ErrorCode: Integer;
begin
  ShellExec('open', 'https://x.com/sirdimitry', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
end;

procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel1.Caption := CustomMessage('WelcomeLabel1');
  WizardForm.WelcomeLabel2.Caption := CustomMessage('WelcomeLabel2');
  WizardForm.FinishedHeadingLabel.Caption := CustomMessage('FinishedHeadingLabel');
  WizardForm.FinishedLabel.Caption := CustomMessage('FinishedLabel');

  { Visible on every wizard page, including welcome and completion. }
  AuthorLink := TNewStaticText.Create(WizardForm);
  AuthorLink.Parent := WizardForm;
  AuthorLink.Caption := 'FaceBlur Studio  /  @sirdimitry';
  AuthorLink.Left := ScaleX(16);
  AuthorLink.Top := WizardForm.CancelButton.Top + ScaleY(7);
  AuthorLink.Font.Color := $00FFCD60;
  AuthorLink.Cursor := crHand;
  AuthorLink.OnClick := @OpenAuthor;

  { Dedicated wide artwork below installation progress. }
  ExtractTemporaryFile('progress-banner.png');
  ProgressBanner := TBitmapImage.Create(WizardForm);
  ProgressBanner.Parent := WizardForm.InstallingPage;
  ProgressBanner.Left := WizardForm.ProgressGauge.Left;
  ProgressBanner.Top := WizardForm.ProgressGauge.Top + WizardForm.ProgressGauge.Height + ScaleY(22);
  ProgressBanner.Width := WizardForm.ProgressGauge.Width;
  ProgressBanner.Height := ScaleY(118);
  ProgressBanner.Stretch := True;
  ProgressBanner.PngImage.LoadFromFile(ExpandConstant('{tmp}\progress-banner.png'));
end;
