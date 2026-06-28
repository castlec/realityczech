#!/usr/bin/env python3
"""Validate the app's structured Reality Czech course data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

COURSE_FILE = Path(__file__).resolve().parents[1] / "app/src/main/assets/course.json"


def fail(message: str) -> None:
    print(f"course validation failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    data = json.loads(COURSE_FILE.read_text(encoding="utf-8"))
    units = data.get("units")
    if not isinstance(units, list) or not units:
        fail("at least one unit is required")

    unit_ids: set[str] = set()
    lesson_ids: set[str] = set()
    lesson_count = 0

    for unit in units:
        unit_id = unit.get("id")
        if not unit_id or unit_id in unit_ids:
            fail(f"missing or duplicate unit id: {unit_id!r}")
        unit_ids.add(unit_id)

        lessons = unit.get("lessons")
        if not isinstance(lessons, list) or not lessons:
            fail(f"unit {unit_id!r} has no lessons")

        for lesson in lessons:
            lesson_count += 1
            lesson_id = lesson.get("id")
            if not lesson_id or lesson_id in lesson_ids:
                fail(f"missing or duplicate lesson id: {lesson_id!r}")
            lesson_ids.add(lesson_id)

            if not lesson.get("sourceUrl"):
                fail(f"lesson {lesson_id!r} is missing sourceUrl")

            for question in lesson.get("quiz", []):
                choices = question.get("choices", [])
                correct = question.get("correctIndex")
                if not choices:
                    fail(f"lesson {lesson_id!r} has a quiz question without choices")
                if not isinstance(correct, int) or not 0 <= correct < len(choices):
                    fail(f"lesson {lesson_id!r} has an invalid correctIndex")

    print(f"validated {len(unit_ids)} unit(s) and {lesson_count} lesson(s)")


if __name__ == "__main__":
    main()
