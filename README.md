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
- 94 bundled human recordings, with source speaker names retained where published;
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
- network access while synchronizing URL-backed source media

```bash
python3 tools/sync_media.py --skip-unit1-discovery
python3 tools/verify_vendor_media.py
python3 tools/verify_media_checksums.py
python3 tools/validate_course.py
gradle testDebugUnitTest lintDebug assembleDebug
```

The generated URL-backed media is written to `app/src/main/assets/media/` and packaged into the APK. The APK is written to `app/build/outputs/apk/debug/app-debug.apk`.

## Continuous integration

Every pull request and push to `main` runs `.github/workflows/android.yml`.

Normal Android CI does not crawl or export source documents. Before Gradle runs, it:

1. expands the canonical URL inventory;
2. downloads every URL-backed asset marked `bundle`;
3. checks streaming-only video endpoints;
4. validates content types, file signatures, minimum sizes, IDs, and destination paths;
5. verifies committed document-only media shards when present;
6. verifies URL-backed files against `media/checksums.json`;
7. cross-checks lesson references against the generated media catalog and physical files.

The build fails when a declared URL is unavailable, a download returns the wrong content, a committed shard is missing or altered, a lesson references undeclared media, or upstream bytes differ from the reviewed checksum lock.

Successful workflows upload:

- the installable `reality-czech-debug-apk` artifact;
- `media-sync-report`, including resolved URLs, byte counts, and SHA-256 hashes;
- the Gradle build log;
- the Android lint report.

## Media ingestion

Source discovery is a separate update workflow because it is expensive and depends on external document-export formats.

`.github/workflows/ingest-unit1-media.yml` runs `tools/ingest_unit1_media.py`. It:

1. crawls the complete Unit 1 source graph;
2. exports public Google documents;
3. extracts media embedded only inside those documents;
4. records the source document, internal member, source lesson, creator/license text, and inherited site attribution where no narrower credit exists;
5. deduplicates media by SHA-256;
6. writes 16 deterministic repository shards under `media/vendor/unit1-document-media/`;
7. verifies those shards and opens or updates a media-ingestion pull request.

Each shard remains below GitHub's individual-file limit. Normal Android CI verifies the committed shards without repeating source extraction.

## Content architecture

Course metadata is stored in `app/src/main/assets/course/index.json`. Lessons are independent JSON files under `app/src/main/assets/course/lessons/`.

This structure keeps source attribution and curriculum content separate from the Android UI. Individual lessons can be added, reviewed, corrected, and tested independently.

`tools/validate_course.py` checks lesson IDs, source URLs, resource links, media IDs, bundled asset paths, transcript references, licensing fields, exercise types, spoken prompts, answer definitions, and course-index coverage.

## Media architecture

`media/sources.json` and the Unit 1 audio manifests are the source of truth for stable public media locations. Each entry records the source page, canonical URL, delivery mode, expected type, local APK path, lesson mappings, speaker information where available, and attribution.

`media/checksums.json` locks every URL-backed bundled asset to a reviewed SHA-256 value. Updating an upstream asset therefore requires an intentional source review and checksum update rather than silently changing the application build.

Media that exists only inside source documents is committed as content-addressed shard archives. `media/vendor/unit1-document-media/manifest.json` maps every extracted file back to its source document and attribution record. `tools/verify_vendor_media.py` verifies each shard and every file inside it.

Direct images and recordings are generated during CI and packaged under `app/src/main/assets/media/`. Interview videos remain streamed through YouTube and are availability-checked through oEmbed rather than downloaded.

Original human recordings are the preferred pronunciation source. Android `TextToSpeech` with the Czech (`cs-CZ`) locale remains available as a fallback and for dynamically generated exercises.

## Licensing

Reality Czech identifies its curriculum as openly licensed under CC BY-SA. Adapted content retains attribution and share-alike treatment. Source-page, document-level, item-level, and inherited attribution records are retained in the media manifests.

Application source code licensing has not yet been selected.
