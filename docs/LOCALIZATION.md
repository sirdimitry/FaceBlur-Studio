# Localization maintenance

The app and README support `en`, `ru`, `zh` (Simplified Chinese), `ar`, `sr`
(Serbian Cyrillic), `el`, and `es`. English is the GitHub README entry point.
New app installations use `auto`; the first supported system UI language wins,
with English as fallback. An explicit preference overrides automatic selection.

## README and descriptions

Edit **every** `docs/localization/readme/<language>.json` for each content change.
All files must have the same keys and links/placeholders. Keep release facts and
technical instructions equivalent; adapt prose respectfully to each language.
The shared renderer owns release URLs, checksums, screenshots, navigation and
structure so these cannot accidentally diverge between translations.

```bash
venv/bin/python scripts/render_readmes.py
venv/bin/python scripts/render_readmes.py --check
```

The renderer produces `README.md`, the six translated READMEs, and
`docs/APP_DESCRIPTIONS.md`. Do not edit generated files independently. Check mode
fails on missing translation blocks, changed placeholder sets or stale outputs.
It cannot judge semantic accuracy; review the translated text as well.

## Interface strings

`ui/translation_catalog.py` contains the complete catalogs. `TRANSLATIONS` maps
source keys to English; `LOCALIZED` maps those English templates to the five
additional languages. Russian source keys are the Russian catalog. Every new
user-facing string requires all seven translations with identical format fields.
Use `tr(source).format(...)`; formatted messages keep their identity and values
so a language switch preserves filenames, numbers and selections.

The application description in About is translated through the same catalog.
Detailed developer logs and third-party diagnostic messages retain their original
language; user-facing controls, actions, hints and application errors are localized.
Native file dialogs follow the operating system's own dialog language; their app
file-type labels are translated.

## Arabic layout and text

Store logical Unicode. `ui/text_direction.py` shapes Arabic letters and applies
bidi ordering only at Tk's display boundary on Windows/Linux, wrapping logical
words first. macOS Tk labels, canvases and native menus use CoreText's existing
shaping/bidi support and receive logical Unicode to avoid double reordering. Use platform Arabic and Chinese fonts with
system fallback. `ui/layout_direction.py` mirrors inspector placement, text
alignment, action groups, selection controls and numeric-field placement.
Video pixels, spatial face coordinates, timeline progression, transport symbols,
filenames and numeric entry values retain their original meaning. Switching back
to an LTR language restores the original layout without rebuilding the workspace.

```bash
venv/bin/python scripts/test_language.py
venv/bin/python scripts/test_mac_workspace.py
venv/bin/python scripts/test_project_roundtrip.py
```

Test the native Windows app on Windows before claiming a verified Windows
release. A shared-window test on macOS does not verify Windows-native rendering.
