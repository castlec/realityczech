#!/usr/bin/env python3
"""Validate the final Unit 1 curriculum and packaged-media integration."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COURSE_ROOT = ROOT / "app/src/main/assets/course"
MEDIA_ROOT = ROOT / "app/src/main/assets/media"
CATALOG_PATH = MEDIA_ROOT / "catalog.json"
SOURCES_PATH = ROOT / "media/sources.json"
REPORT_PATH = ROOT / "media/vendor-materialization-report.json"
EXPECTED_DAYS = {f"1.{number}" for number in range(1, 12)}
LEARNER_ROLES = {"instructional", "exercise-related"}


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc


def normalize(value: str) -> str:
    return " ".join(value.strip().lower().rstrip(".!?").split())


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> None:
    errors: list[str] = []
    index = read_json(COURSE_ROOT / "index.json")
    catalog = read_json(CATALOG_PATH)
    sources = read_json(SOURCES_PATH)
    report = read_json(REPORT_PATH)

    lesson_ids: set[str] = set()
    days: set[str] = set()
    for unit in index.get("units", []):
        for filename in unit.get("lessonFiles", []):
            lesson = read_json(COURSE_ROOT / "lessons" / filename)
            lesson_id = str(lesson.get("id", ""))
            lesson_ids.add(lesson_id)
            day = str(lesson.get("day", "")).split(" ", 1)[0]
            days.add(day)
            if not str(lesson.get("sourceUrl", "")).startswith("https://realityczech.org/"):
                fail(errors, f"{lesson_id} lacks a Reality Czech source URL")
            if not str(lesson.get("sourceAttribution", "")).strip():
                fail(errors, f"{lesson_id} lacks source attribution")
            if "CC BY-SA" not in str(lesson.get("contentLicense", "")):
                fail(errors, f"{lesson_id} lacks CC BY-SA license metadata")

    missing_days = sorted(EXPECTED_DAYS - days)
    if missing_days:
        fail(errors, f"missing Unit 1 day coverage: {missing_days}")

    audio_assets: list[dict[str, Any]] = []
    vendor_assets: list[dict[str, Any]] = []
    for asset in catalog.get("assets", []):
        asset_id = str(asset.get("id", "<unknown>"))
        lesson_asset_ids = asset.get("lessonIds") or [asset.get("lessonId")]
        unknown_lessons = [value for value in lesson_asset_ids if value not in lesson_ids]
        if unknown_lessons:
            fail(errors, f"{asset_id} references unknown lessons {unknown_lessons}")
        if not str(asset.get("attribution", "")).strip():
            fail(errors, f"{asset_id} lacks attribution")
        local_path = asset.get("localPath")
        if asset.get("delivery") in {"bundle", "vendor"}:
            if not isinstance(local_path, str) or not local_path:
                fail(errors, f"{asset_id} lacks localPath")
            elif not (MEDIA_ROOT / local_path).is_file():
                fail(errors, f"{asset_id} is missing packaged file {local_path}")
        if asset.get("kind") == "audio" and asset.get("delivery") == "bundle":
            audio_assets.append(asset)
        if asset.get("provider") == "vendor-document-media":
            vendor_assets.append(asset)
            if asset.get("semanticRole") not in LEARNER_ROLES:
                fail(errors, f"{asset_id} has non-learner semantic role {asset.get('semanticRole')!r}")
            if not isinstance(asset.get("sourceOrder"), int):
                fail(errors, f"{asset_id} lacks source order")
            if not str(asset.get("sourcePage", "")).startswith("https://realityczech.org/"):
                fail(errors, f"{asset_id} lacks source lesson")

    if len(audio_assets) < 94:
        fail(errors, f"expected at least 94 bundled human recordings, found {len(audio_assets)}")
    if not vendor_assets:
        fail(errors, "no semantic document images were packaged")
    if report.get("materialized") != len(vendor_assets):
        fail(
            errors,
            f"materialization report lists {report.get('materialized')} assets but catalog has {len(vendor_assets)}",
        )
    if set(report.get("perRole", {})) - LEARNER_ROLES:
        fail(errors, f"materialization report contains invalid roles: {report.get('perRole')}")

    pronunciation_labels: set[tuple[str, str]] = set()
    for group in sources.get("imageGroups", []):
        lesson_id = str(group.get("lessonId", ""))
        for item in group.get("items", []):
            label = normalize(str(item.get("label", "")))
            if label and label != "lesson header":
                pronunciation_labels.add((lesson_id, label))
    audio_labels = {
        (lesson_id, normalize(str(asset.get("label", ""))))
        for asset in audio_assets
        for lesson_id in (asset.get("lessonIds") or [asset.get("lessonId")])
    }
    matched = pronunciation_labels & audio_labels
    if len(matched) < 30:
        fail(errors, f"only {len(matched)} pronunciation images have matching human recordings")

    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        raise SystemExit(f"integrated media validation failed with {len(errors)} error(s)")

    print(
        json.dumps(
            {
                "lessons": len(lesson_ids),
                "days": sorted(days),
                "humanRecordings": len(audio_assets),
                "semanticImages": len(vendor_assets),
                "matchedPronunciationCards": len(matched),
                "roles": report.get("perRole", {}),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
