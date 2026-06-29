#!/usr/bin/env python3
"""Validate the modular Reality Czech course and generated media assets."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
COURSE_DIR = ROOT / "app/src/main/assets/course"
INDEX_FILE = COURSE_DIR / "index.json"
LESSON_DIR = COURSE_DIR / "lessons"
MEDIA_ROOT = ROOT / "app/src/main/assets/media"
MEDIA_CATALOG_FILE = MEDIA_ROOT / "catalog.json"
SUPPORTED_EXERCISES = {"multiple_choice", "text_entry", "listen_select", "listen_type"}
CHOICE_EXERCISES = {"multiple_choice", "listen_select"}
TEXT_EXERCISES = {"text_entry", "listen_type"}
LISTENING_EXERCISES = {"listen_select", "listen_type"}
YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
PRONUNCIATION_IMAGE_KIND = "pronunciation image"


def fail(message: str) -> None:
    print(f"course validation failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing file: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")


def valid_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def main() -> None:
    index = read_json(INDEX_FILE)
    media_catalog = read_json(MEDIA_CATALOG_FILE)
    catalog_assets = media_catalog.get("assets")
    if not isinstance(catalog_assets, list) or not catalog_assets:
        fail("generated media catalog has no assets")

    bundled_source_urls = {
        item.get("sourceUrl")
        for item in catalog_assets
        if item.get("delivery") == "bundle" and item.get("sourceUrl")
    }
    bundled_asset_paths = {
        f"media/{item.get('localPath')}"
        for item in catalog_assets
        if item.get("delivery") == "bundle" and item.get("localPath")
    }

    for item in catalog_assets:
        if item.get("delivery") == "bundle":
            local_path = item.get("localPath")
            if not local_path or not (MEDIA_ROOT / local_path).is_file():
                fail(f"catalog references missing bundled media: {local_path!r}")

    units = index.get("units")
    if not isinstance(units, list) or not units:
        fail("at least one unit is required")

    unit_ids: set[str] = set()
    lesson_ids: set[str] = set()
    lesson_files_seen: set[str] = set()
    lesson_count = 0
    exercise_count = 0
    listening_exercise_count = 0
    embedded_video_count = 0
    embedded_audio_count = 0
    bundled_image_reference_count = 0

    for unit in units:
        unit_id = unit.get("id")
        if not unit_id or unit_id in unit_ids:
            fail(f"missing or duplicate unit id: {unit_id!r}")
        unit_ids.add(unit_id)

        lesson_files = unit.get("lessonFiles")
        if not isinstance(lesson_files, list) or not lesson_files:
            fail(f"unit {unit_id!r} has no lessonFiles")

        for filename in lesson_files:
            if not isinstance(filename, str) or not filename.endswith(".json"):
                fail(f"invalid lesson filename in {unit_id!r}: {filename!r}")
            if filename in lesson_files_seen:
                fail(f"lesson file is listed more than once: {filename}")
            lesson_files_seen.add(filename)

            lesson = read_json(LESSON_DIR / filename)
            lesson_count += 1
            lesson_id = lesson.get("id")
            if not lesson_id or lesson_id in lesson_ids:
                fail(f"missing or duplicate lesson id: {lesson_id!r}")
            lesson_ids.add(lesson_id)

            if filename != f"{lesson_id}.json":
                fail(f"lesson filename {filename!r} does not match id {lesson_id!r}")
            if not lesson.get("day"):
                fail(f"lesson {lesson_id!r} is missing day")
            if not valid_url(lesson.get("sourceUrl")):
                fail(f"lesson {lesson_id!r} has an invalid sourceUrl")
            if not lesson.get("contentLicense"):
                fail(f"lesson {lesson_id!r} is missing contentLicense")

            media_ids: set[str] = set()
            for resource in lesson.get("resources", []):
                if not resource.get("title") or not valid_url(resource.get("url")):
                    fail(f"lesson {lesson_id!r} has an invalid resource")

                provider = resource.get("provider", "")
                media_id = resource.get("mediaId", "")
                if provider == "youtube":
                    if not isinstance(media_id, str) or not YOUTUBE_ID.fullmatch(media_id):
                        fail(f"lesson {lesson_id!r} has invalid YouTube mediaId {media_id!r}")
                    if media_id in media_ids:
                        fail(f"lesson {lesson_id!r} repeats mediaId {media_id!r}")
                    media_ids.add(media_id)
                    embedded_video_count += 1
                elif provider == "asset-audio":
                    asset_path = resource.get("assetPath")
                    if not isinstance(asset_path, str) or asset_path not in bundled_asset_paths:
                        fail(
                            f"lesson {lesson_id!r} references undeclared bundled audio {asset_path!r}"
                        )
                    if not (ROOT / "app/src/main/assets" / asset_path).is_file():
                        fail(f"lesson {lesson_id!r} bundled audio is missing: {asset_path}")
                    if not resource.get("fallbackText"):
                        fail(f"lesson {lesson_id!r} audio lacks TTS fallback text")
                    embedded_audio_count += 1
                elif provider or media_id:
                    fail(f"lesson {lesson_id!r} has unsupported media provider {provider!r}")

                if resource.get("kind") == PRONUNCIATION_IMAGE_KIND:
                    source_url = resource.get("url")
                    if source_url not in bundled_source_urls:
                        fail(
                            f"lesson {lesson_id!r} pronunciation image is not in media manifest: "
                            f"{source_url}"
                        )
                    filename_from_url = source_url.rsplit("/", 1)[-1].split("?", 1)[0]
                    if not (MEDIA_ROOT / "images" / filename_from_url).is_file():
                        fail(
                            f"lesson {lesson_id!r} pronunciation image was not embedded: "
                            f"{filename_from_url}"
                        )
                    bundled_image_reference_count += 1

            for line in lesson.get("transcript", []):
                media_id = line.get("mediaId", "")
                if media_id and media_id not in media_ids:
                    fail(f"lesson {lesson_id!r} transcript references unknown mediaId {media_id!r}")
                start_seconds = line.get("startSeconds")
                if start_seconds is not None and (not isinstance(start_seconds, int) or start_seconds < 0):
                    fail(f"lesson {lesson_id!r} has invalid transcript startSeconds")

            for exercise in lesson.get("exercises", []):
                exercise_count += 1
                exercise_type = exercise.get("type")
                if exercise_type not in SUPPORTED_EXERCISES:
                    fail(f"lesson {lesson_id!r} has unsupported exercise type {exercise_type!r}")
                if not exercise.get("prompt") or not exercise.get("explanation"):
                    fail(f"lesson {lesson_id!r} has an incomplete exercise")
                if exercise_type in CHOICE_EXERCISES:
                    choices = exercise.get("choices", [])
                    correct = exercise.get("correctIndex")
                    if not choices:
                        fail(f"lesson {lesson_id!r} has choice exercise without choices")
                    if not isinstance(correct, int) or not 0 <= correct < len(choices):
                        fail(f"lesson {lesson_id!r} has an invalid correctIndex")
                if exercise_type in TEXT_EXERCISES and not exercise.get("acceptedAnswers"):
                    fail(f"lesson {lesson_id!r} has text exercise without acceptedAnswers")
                if exercise_type in LISTENING_EXERCISES:
                    listening_exercise_count += 1
                    if not exercise.get("spokenText"):
                        fail(f"lesson {lesson_id!r} has listening exercise without spokenText")

    unlisted = {path.name for path in LESSON_DIR.glob("*.json")} - lesson_files_seen
    if unlisted:
        fail(f"unlisted lesson files: {sorted(unlisted)}")

    print(
        f"validated {len(unit_ids)} unit(s), {lesson_count} lesson(s), "
        f"{exercise_count} exercise(s), {listening_exercise_count} listening exercise(s), "
        f"{embedded_video_count} embedded video(s), {embedded_audio_count} bundled recording(s), "
        f"and {bundled_image_reference_count} bundled lesson-image reference(s)"
    )


if __name__ == "__main__":
    main()
