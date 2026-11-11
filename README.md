# Words & Whimsy

A personal English vocabulary journal with a vintage literary design. Type a word, press **Generate**, review the English entry, and save.

## Features
- **Live preview**: as you type a word, the dictionary meaning, British/American IPA, easy spelling and speakers appear before you press Generate.
- **Generate**: AI-written English entry (definition, part of speech, synonyms, antonyms, example) plus IPA and recorded audio from a dictionary source. IPA is never invented; missing data is shown as *unavailable*.
- **Pronunciation Studio**: British/American IPA, easy spelling, syllables and stress (derived from IPA), recorded audio with device text-to-speech fallback, practice mode with optional speech recognition.
- **Word Garden**: every word is a flower; mastered words bloom.
- **Memory Lane**: flashcards, meaning/word/synonym/sentence-completion questions, spaced repetition.
- **Literary Desk**, **Word Passport**, **Daily Pages**: journal, statistics, and day-by-day history.
- **Backup and restore** (Word Passport page): export all words, reviews and journal pages to a `.json` file; restore by merging a backup into the current data (nothing is deleted, newer edits win, duplicate words are not created).
- Everything is saved in the browser (`localStorage`). No account, no backend.

## Install as an app (phone)
Open the live site, then:
- **iPhone (Safari):** Share, then **Add to Home Screen**.
- **Android (Chrome):** menu, then **Install app**.

It opens full screen with its own icon and also works offline. The installed app keeps its own storage, separate from the browser tab, so use **Backup and restore** (Word Passport page) to move existing words across.

## Run
Open `index.html` in a browser, or serve the folder (`python3 -m http.server`).

## How generation works
- Definitions and examples come from Claude through the Claude artifact runtime (`claude.use("sample")`). Outside Claude artifacts that capability is absent, so the app falls back to the dictionary text, or to manual entry.
- Pronunciation comes from the [Free Dictionary API](https://dictionaryapi.dev/) (no key needed). No API keys are stored in this repo.
- To use another AI provider, replace the `SAMPLE.json(...)` call in `gen()` with a call to your own backend. Do not put API keys in frontend code.

## Tests
```
node tests/unit.test.js                 # pure logic
pip install playwright && playwright install chromium
python3 tests/e2e_regression.py         # full app regression
python3 tests/e2e_pronunciation.py      # audio, voices, practice (simulated)
python3 tests/e2e_generation.py         # generate workflow (simulated AI/dictionary)
python3 tests/e2e_backup.py             # streak consistency, export, restore, merge
```
Services are simulated in the tests; real dictionary and AI output are not exercised.

## Known limitations
Data is per browser and device; use Backup and restore to move it. Settings (goal, voice) are not included in backups. Syllable, stress and easy spelling are approximations derived from IPA. Speech recognition depends on the browser.
