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
- selectable video controls for lessons containing several clips;
- transcript show/hide controls beside the related video;
- transcript metadata prepared for future tap-to-seek timing;
- links back to the original Reality Czech lesson and video pages;
- per-lesson source attribution and licensing metadata;
- a vocabulary review deck;
- GitHub Actions CI that validates course data, runs tests and lint, builds a debug APK, and uploads it as an artifact.

Days 1.4–1.11 and Units 2–10 remain to be converted. Pronunciation audio and source images are not yet bundled; their item-level rights and credits must be mapped first.

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

This structure keeps source attribution and curriculum content separate from the Android UI. Individual lessons can be added, reviewed, corrected, and tested without rewriting one large course file.

`tools/validate_course.py` checks lesson IDs, source URLs, resource links, media providers and IDs, transcript-to-media references, licensing fields, supported exercise types, answer definitions, and whether every lesson file appears in the course index.

## Media architecture

Interview videos are not copied into the repository or APK. The app uses the official YouTube IFrame player inside an Android `WebView`, while Reality Czech remains the linked source page for annotations and attribution.

Lesson resources declare a media provider and stable media ID. Transcript lines can declare the matching media ID and an optional start time, allowing future tap-to-replay behavior without changing the lesson file format.

## Licensing

Reality Czech identifies its curriculum as openly licensed. Adapted content must retain attribution and share-alike treatment where CC BY-SA applies. Linked or embedded third-party images, recordings, videos, and adapted texts may carry separate licenses; each imported item must preserve its own attribution metadata.

Original videos remain streamed from their provider rather than downloaded into the APK.

Application source code licensing has not yet been selected.
