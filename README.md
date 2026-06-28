# Reality Czech for Android

An offline-first Android learning application adapted from the [Reality Czech](https://realityczech.org/) open educational curriculum.

## Current prototype

The initial application includes:

- five introductory Unit 1 lessons;
- lesson objectives, explanations, examples, and vocabulary;
- immediate-feedback quizzes;
- persistent lesson completion;
- a simple vocabulary review deck;
- item-level source links and a licensing/attribution screen;
- GitHub Actions CI that runs tests and lint, builds a debug APK, and uploads it as an artifact.

This is a functional scaffold, not yet a complete conversion of all ten Reality Czech units.

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

Course material is stored in `app/src/main/assets/course.json`. This keeps curriculum conversion separate from the Android interface and provides a stable target for a future importer.

## Licensing

Reality Czech identifies its curriculum as openly licensed. Adapted content must retain attribution and share-alike treatment where CC BY-SA applies. Embedded or linked third-party images, recordings, video, and adapted texts may carry separate licenses; each imported item must preserve its own attribution metadata.

Application source code licensing has not yet been selected.
