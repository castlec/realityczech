#!/usr/bin/env python3
"""Validate the modular Reality Czech course assets."""

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
SUPPORTED_EXERCISES = {"multiple_choice", "text_entry"}
YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


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
    units = index.get("units")
    if not isinstance(units, list) or not units:
        fail("at least one unit is required")

    unit_ids: set[str] = set()
    lesson_ids: set[str] = set()
    lesson_files_seen: set[str] = set()
    lesson_count = 0
    exercise_count = 0
    embedded_video_count = 0

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
                if provider or media_id:
                    if provider != "youtube":
                        fail(f"lesson {lesson_id!r} has unsupported media provider {provider!r}")
                    if not isinstance(media_id, str) or not YOUTUBE_ID.fullmatch(media_id):
                        fail(f"lesson {lesson_id!r} has invalid YouTube mediaId {media_id!r}")
                    if media_id in media_ids:
                        fail(f"lesson {lesson_id!r} repeats mediaId {media_id!r}")
                    media_ids.add(media_id)
                    embedded_video_count += 1

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
                if exercise_type == "multiple_choice":
                    choices = exercise.get("choices", [])
                    correct = exercise.get("correctIndex")
                    if not choices:
                        fail(f"lesson {lesson_id!r} has multiple choice without choices")
                    if not isinstance(correct, int) or not 0 <= correct < len(choices):
                        fail(f"lesson {lesson_id!r} has an invalid correctIndex")
                if exercise_type == "text_entry" and not exercise.get("acceptedAnswers"):
                    fail(f"lesson {lesson_id!r} has text entry without acceptedAnswers")

    unlisted = {path.name for path in LESSON_DIR.glob("*.json")} - lesson_files_seen
    if unlisted:
        fail(f"unlisted lesson files: {sorted(unlisted)}")

    print(
        f"validated {len(unit_ids)} unit(s), {lesson_count} lesson(s), "
        f"{exercise_count} exercise(s), and {embedded_video_count} embedded video(s)"
    )


if __name__ == "__main__":
    main()
