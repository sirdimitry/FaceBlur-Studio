# FaceBlur Studio conventions

- Preserve both macOS and Windows behavior when changing the shared UI.
- Support English, Russian, Simplified Chinese, Arabic, Serbian Cyrillic, Greek,
  and Spanish. Use respectful, task-based copy. All new user-facing strings need
  translations in every supported language; preserve formatting placeholders.
- New installs follow the system UI language, falling back to English. Explicit
  language choices persist. Arabic uses RTL text and mirrored workspace layout;
  video pixels, coordinates, timelines, paths and numeric inputs retain their
  meaning and order.
- README.md is the English entry point. Every README must have the same content,
  facts, sections and links, with a language navigation row at the top.
- For any README change, update every file in docs/localization/readme/, then run
  `venv/bin/python scripts/render_readmes.py` and its `--check` mode. Do not edit
  generated README files independently. Preserve Arabic RTL markup.
- App descriptions are generated from the same multilingual README sources.
- Run the language and project regression checks for localization changes. Be
  explicit about native Windows checks that were not run on Windows.
