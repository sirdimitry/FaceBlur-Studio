<p align="right"><a href="README.md">English</a> · <strong>Русский</strong></p>

<p align="center"><img src="assets/banner.png" alt="FaceBlur Studio" width="100%"></p>

# FaceBlur Studio

<p align="center"><strong>Локальное размытие лиц в видео</strong><br>Предпросмотр, отслеживание лиц и выбор объектов для размытия.</p>

> **Скачать:** [FaceBlur Studio 1.1.23 для Mac с Apple Silicon (DMG, 292 МиБ)](https://github.com/sirdimitry/FaceBlur-Studio/releases/download/v1.1.23/FaceBlur_Studio_v1.1.23_Apple_Silicon.dmg). Это предварительная версия. [Скачать для Windows 10/11 x64 (EXE, 126 МиБ)](https://github.com/sirdimitry/FaceBlur-Studio/releases/download/v1.1.25/FaceBlur-Studio-1.1.25-Windows-Setup.exe).

## Как выглядит приложение

![FaceBlur Studio 1.1.23: окно анализа и предпросмотра видео](assets/faceblur-studio-1.1.23.png)

## Возможности

- Автоматический поиск и отслеживание лиц с помощью YOLOv8-face.
- Выбор лиц, которые нужно размыть; предпросмотр результата и ручная настройка маски.
- Сохранение и открытие проекта `.fbp` с результатами анализа.
- Экспорт MP4 с исходной звуковой дорожкой, если она есть.
- Чтение кадров из видео по мере надобности, без хранения всего ролика в оперативной памяти.
- Локальная обработка: приложение не отправляет видео в облако.

Автоматическое распознавание может пропустить лицо. Перед публикацией проверьте всё экспортированное видео.

## Установка

**Windows 10/11 x64:** скачайте [установщик](https://github.com/sirdimitry/FaceBlur-Studio/releases/download/v1.1.25/FaceBlur-Studio-1.1.25-Windows-Setup.exe), запустите его и следуйте мастеру установки на русском или английском языке. По умолчанию программа устанавливается в `%LOCALAPPDATA%\Programs\FaceBlur Studio` для текущего пользователя без обязательных прав администратора. Python, FFmpeg, модель и библиотеки включены. Удаление доступно через настройки Windows; проекты и настройки сохраняются.

Установщик не подписан сертификатом. Установка, повторная установка, запуск и удаление проверены на рабочей Windows 11; чистая Windows/VM пока не проверена. См. [инструкции сборки](docs/WINDOWS_INSTALLER.md) и [результаты проверки](docs/WINDOWS_VALIDATION.md).

SHA-256 Windows: `f562513abe0fdb32a9dd0fbfef3826ab0967d4468d284bb4204b50e25524ef9d`

**Mac с Apple Silicon:** скачайте [DMG](https://github.com/sirdimitry/FaceBlur-Studio/releases/download/v1.1.23/FaceBlur_Studio_v1.1.23_Apple_Silicon.dmg), откройте его и перетащите **FaceBlur Studio** в **Applications**. Python, FFmpeg и модель распознавания уже включены; отдельно устанавливать их для DMG не нужно.

Этот предварительный DMG имеет локальную подпись и **не нотариализован** Apple. macOS может заблокировать первый запуск. Если вы доверяете скачанному файлу, воспользуйтесь [инструкцией Apple «Открыть всё равно»](https://support.apple.com/en-au/102445) в «Системные настройки → Конфиденциальность и безопасность». Установка на другом чистом Mac ещё не проверена, поэтому работу на любой системе гарантировать нельзя. Этот образ рассчитан на Apple Silicon; Mac с Intel и Windows им не поддерживаются.

SHA-256: `b83947aa54d0b39ebc9bd638eb6c3858e30c63bfd46007604987b319ba712dee`

**Запуск из исходного кода.** Нужны Python 3.12 и установленный FFmpeg. Модель `yolov8s-face.pt` уже находится в репозитории. На Mac можно установить FFmpeg через `brew install ffmpeg`.

```bash
git clone https://github.com/sirdimitry/FaceBlur-Studio.git
cd FaceBlur-Studio
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Для запуска исходников на Windows нужны Python 3.12 и FFmpeg в PATH. Активируйте окружение командой `.\venv\Scripts\Activate.ps1` и установите `requirements-windows.txt` вместо `requirements.txt`. См. [памятку по Windows](docs/WINDOWS_HANDOFF.md) и [сборку установщика](docs/WINDOWS_INSTALLER.md). Для [сборки DMG](scripts/build_macos_dmg.sh) нужен `create-dmg`.

## Диагностика

Лог при запуске из исходников: `debug_app.log` в папке проекта. Лог установленного Mac-приложения: `~/Library/Logs/FaceBlurStudio/debug_app.log`. Лог установленного Windows-приложения: `%LOCALAPPDATA%\FaceBlurStudio\Logs\debug_app.log`. Лог может содержать локальные пути к файлам; проверьте его перед публикацией.

## Состав репозитория

Здесь находятся исходный код, модель распознавания лиц, [иконка приложения](AutoBlureFace_icon.png), [баннер](assets/banner.png) и актуальный скриншот. Установщик Windows и DMG приложены к [GitHub Release v1.1.23](https://github.com/sirdimitry/FaceBlur-Studio/releases/tag/v1.1.23), а не добавлены в дерево исходников.

## Лицензия

Отдельный файл лицензии в репозитории пока не опубликован. Условия повторного использования исходного кода и включённых моделей следует уточнить до распространения или переработки проекта.
