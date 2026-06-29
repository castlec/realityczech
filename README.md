# Reality Czech for Android

An offline-first Android learning application adapted from the [Reality Czech](https://realityczech.org/) open educational curriculum.

## Current build

The application follows the original Unit 1 instructional sequence. The current conversion covers days **1.1–1.3** through nine native lessons:

- Czech vowels, vowel length, and stress;
- consonants and háček letters;
- formal and informal greetings;
- soft pronunciation patterns with ť, ď, ň, and ě;
- identifying objects with `Co to je?`;
- Czech names and familiar forms;
- identifying people and asking names;
- present-tense and negative forms of `být`;
- noun gender and masculine animacy.

The app provides:

- day-grouped lesson navigation and progress tracking;
- explanations, examples, vocabulary, and usage notes;
- multiple-choice and typed-answer exercises with immediate feedback;
- four Reality Czech interview videos streamed through an in-app YouTube player;
- selectable video controls and transcript show/hide controls;
- Czech pronunciation playback for every vocabulary item and review card;
- normal and slow playback through the Android device speech service;
- listening-selection and listening-dictation exercise types;
- six initial listening exercises in the pronunciation lessons;
- links back to the original Reality Czech pages;
- per-lesson source attribution and licensing metadata;
- GitHub Actions CI that validates content, tests, lints, builds, and uploads a debug APK.

Days 1.4–1.11 and Units 2–10 remain to be converted. Original source pronunciation recordings and lesson images are not yet bundled because their direct files and item-level credits still need to be mapped.

## Build

Requirements:

- JDK 17
- Gradle 8.11.1
- Android SDK 35

```bash
gradle testDebugUnitTest lintDebug assembleDebug
```

The APK is written to `app/build/outputs/apk/debug/app-debug.apk`.

## Continuous integration

Every pull request and push to `main` runs `.github/workflows/android.yml`. A successful workflow provides a `reality-czech-debug-apk` artifact containing an installable debug APK.

## Content architecture

Course metadata is stored in `app/src/main/assets/course/index.json`. Lessons are independent JSON files under `app/src/main/assets/course/lessons/`.

This structure keeps source attribution and curriculum content separate from the Android UI. Individual lessons can be added, reviewed, corrected, and tested independently.

`tools/validate_course.py` checks lesson IDs, source URLs, resource links, media IDs, transcript references, licensing fields, exercise types, spoken prompts, answer definitions, and course-index coverage.

## Media architecture

Interview videos are not copied into the repository or APK. They use the official YouTube IFrame player inside an Android `WebView`, while Reality Czech remains the linked source page for annotations and attribution.

Vocabulary pronunciation and listening exercises currently use Android `TextToSpeech` with the Czech (`cs-CZ`) locale. One shared engine is used for the app session. Playback controls are disabled when Czech voice data is unavailable.

The synthesized speech is supplemental practice and is clearly distinguished from original Reality Czech recordings.

## Licensing

Reality Czech identifies its curriculum as openly licensed. Adapted content must retain attribution and share-alike treatment where CC BY-SA applies. Third-party images, recordings, videos, and texts may carry separate licenses; each imported item must preserve its own attribution metadata.

Original videos remain streamed from their provider rather than downloaded into the APK.

Application source code licensing has not yet been selected.
