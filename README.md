# Reality Czech for Android

An offline-first Android learning application adapted from the [Reality Czech](https://realityczech.org/) open educational curriculum.

## Current build

The application follows the original Unit 1 instructional sequence. The current conversion covers days **1.1–1.3** plus the voiced/voiceless pronunciation material from **1.5**:

- Czech vowels, vowel length, and stress;
- consonants and háček letters;
- formal and informal greetings;
- soft pronunciation patterns with ť, ď, ň, and ě;
- identifying objects with `Co to je?`;
- Czech names and familiar forms;
- identifying people and asking names;
- present-tense and negative forms of `být`;
- noun gender and masculine animacy;
- voiced and voiceless consonants with original human recordings.

The app provides:

- day-grouped lesson navigation and progress tracking;
- explanations, examples, vocabulary, and usage notes;
- multiple-choice, typed-answer, listening-selection, and listening-dictation exercises;
- four Reality Czech interview videos streamed through an in-app YouTube player;
- transcript show/hide controls;
- bundled source images for offline lesson use;
- original human pronunciation recordings where located;
- Android Czech text-to-speech as a clearly labeled fallback;
- normal and slow synthesized playback for vocabulary and generated exercises;
- per-lesson source attribution and licensing metadata;
- CI-enforced media availability and integrity.

Days 1.4 and 1.6–1.11 and Units 2–10 remain to be converted.

## Build

Requirements:

- JDK 17
- Gradle 8.11.1
- Android SDK 35
- network access while synchronizing source media

```bash
python3 tools/sync_media.py
python3 tools/verify_media_checksums.py
python3 tools/validate_course.py
gradle testDebugUnitTest lintDebug assembleDebug
```

The generated media is written to `app/src/main/assets/media/` and packaged into the APK. The APK is written to `app/build/outputs/apk/debug/app-debug.apk`.

## Continuous integration

Every pull request and push to `main` runs `.github/workflows/android.yml`.

Before Gradle runs, CI:

1. expands the canonical inventory in `media/sources.json`;
2. downloads every asset marked `bundle`;
3. checks streaming-only video endpoints;
4. validates content types, file signatures, minimum sizes, IDs, and destination paths;
5. verifies every bundled file against `media/checksums.json`;
6. cross-checks lesson references against the generated media catalog and physical files.

The build fails when a declared URL is unavailable, a download returns the wrong content, a file is missing, a lesson references undeclared media, or upstream bytes differ from the reviewed checksum lock.

Successful workflows upload:

- the installable `reality-czech-debug-apk` artifact;
- `media-sync-report`, including resolved URLs, byte counts, and SHA-256 hashes;
- the Gradle build log;
- the Android lint report.

## Content architecture

Course metadata is stored in `app/src/main/assets/course/index.json`. Lessons are independent JSON files under `app/src/main/assets/course/lessons/`.

This structure keeps source attribution and curriculum content separate from the Android UI. Individual lessons can be added, reviewed, corrected, and tested independently.

`tools/validate_course.py` checks lesson IDs, source URLs, resource links, media IDs, bundled asset paths, transcript references, licensing fields, exercise types, spoken prompts, answer definitions, and course-index coverage.

## Media architecture

`media/sources.json` is the source of truth for media locations. Each entry records the source page, canonical URL, delivery mode, expected type, local APK path, and attribution. Repeated Reality Czech image collections use explicit item lists with URL templates so missing sequence numbers and file extensions remain reviewable in source.

`media/checksums.json` locks every bundled asset to a reviewed SHA-256 value. Updating an upstream asset therefore requires an intentional source review and checksum update rather than silently changing the application build.

Direct images and recordings are generated during CI and packaged under `app/src/main/assets/media/`. They are intentionally not committed as binary files. Interview videos remain streamed through YouTube and are availability-checked through oEmbed rather than downloaded.

Original human recordings are the preferred pronunciation source. Android `TextToSpeech` with the Czech (`cs-CZ`) locale remains available as a fallback and for dynamically generated exercises.

## Licensing

Reality Czech identifies its curriculum as openly licensed under CC BY-SA. Adapted content retains attribution and share-alike treatment. Source-page and item-level credit information is retained in the media manifest and lesson metadata.

Application source code licensing has not yet been selected.
