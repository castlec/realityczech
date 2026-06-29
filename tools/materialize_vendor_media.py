#!/usr/bin/env python3
"""Materialize semantically placed document-only images for implemented lessons."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LESSON_ROOT = ROOT / "app/src/main/assets/course/lessons"
MEDIA_ROOT = ROOT / "app/src/main/assets/media"
CATALOG_PATH = MEDIA_ROOT / "catalog.json"
MANIFEST_PATH = ROOT / "media/vendor/unit1-document-media/manifest.json"
VENDOR_ROOT = MANIFEST_PATH.parent
CHECKSUMS_PATH = ROOT / "media/checksums.json"
REPORT_PATH = ROOT / "media/vendor-materialization-report.json"
OUTPUT_ROOT = MEDIA_ROOT / "vendor/unit1"
SUPPORTED_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
LEARNER_ROLES = {"instructional", "exercise-related"}
FILENAME_RE = re.compile(r"^(image|picture|graphic)\s*\d*(\.[a-z0-9]+)?$", re.IGNORECASE)


class MaterializationError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise MaterializationError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc


def normalize_page(value: str) -> str:
    return value.strip().rstrip("/") + "/" if value.strip() else ""


def implemented_lessons() -> tuple[dict[str, set[str]], dict[str, str]]:
    index = read_json(ROOT / "app/src/main/assets/course/index.json")
    source_to_ids: dict[str, set[str]] = defaultdict(set)
    titles: dict[str, str] = {}
    for unit in index.get("units", []):
        for filename in unit.get("lessonFiles", []):
            lesson = read_json(LESSON_ROOT / filename)
            lesson_id = lesson["id"]
            titles[lesson_id] = lesson["title"]
            pages = [lesson.get("sourceUrl", "")]
            pages.extend(
                resource.get("url", "")
                for resource in lesson.get("resources", [])
                if isinstance(resource, dict)
            )
            for page in pages:
                normalized = normalize_page(str(page))
                if normalized.startswith("https://realityczech.org/"):
                    source_to_ids[normalized].add(lesson_id)
    return source_to_ids, titles


def mapped_occurrences(
    asset: dict[str, Any],
    source_to_ids: dict[str, set[str]],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for occurrence in asset.get("occurrences", []):
        source = normalize_page(str(occurrence.get("documentSource", "")))
        for lesson_id in source_to_ids.get(source, set()):
            result[lesson_id].append(occurrence)
    return result


def appearance_for(occurrence: dict[str, Any]) -> dict[str, Any]:
    appearances = occurrence.get("appearances", [])
    if not isinstance(appearances, list) or not appearances:
        return {}
    preferred_role = occurrence.get("classification", "")
    candidates = [
        item for item in appearances
        if isinstance(item, dict) and item.get("classification") == preferred_role
    ] or [item for item in appearances if isinstance(item, dict)]
    return min(candidates, key=lambda item: int(item.get("paragraphIndex", 2**31 - 1)))


def semantic_record(occurrences: list[dict[str, Any]]) -> dict[str, Any]:
    ranked: list[tuple[int, int, dict[str, Any], dict[str, Any]]] = []
    role_rank = {"instructional": 0, "exercise-related": 1}
    for occurrence in occurrences:
        appearance = appearance_for(occurrence)
        role = str(appearance.get("classification") or occurrence.get("classification") or "")
        if role not in LEARNER_ROLES:
            continue
        order = int(
            appearance.get("paragraphIndex")
            if appearance.get("paragraphIndex") is not None
            else occurrence.get("sourceOrder")
            if occurrence.get("sourceOrder") is not None
            else 2**31 - 1
        )
        ranked.append((role_rank[role], order, occurrence, appearance))
    if not ranked:
        return {}
    _, order, occurrence, appearance = min(ranked, key=lambda item: (item[0], item[1]))
    return {
        "role": str(appearance.get("classification") or occurrence.get("classification")),
        "sourceOrder": order,
        "placementHeading": str(appearance.get("heading", "")).strip(),
        "caption": str(appearance.get("caption", "")).strip(),
        "contextText": str(appearance.get("contextText", "")).strip(),
        "text": str(appearance.get("text", "")).strip(),
        "previousText": str(appearance.get("previousText", "")).strip(),
        "nextText": str(appearance.get("nextText", "")).strip(),
        "altText": [
            str(value).strip()
            for value in appearance.get("altText", [])
            if str(value).strip()
        ],
        "sourcePage": str(occurrence.get("documentSource", "")).strip(),
    }


def concise(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def image_label(semantic: dict[str, Any], lesson_title: str) -> str:
    candidates = [
        semantic.get("caption", ""),
        semantic.get("text", ""),
        *semantic.get("altText", []),
        semantic.get("previousText", ""),
        semantic.get("nextText", ""),
    ]
    for candidate in candidates:
        text = concise(str(candidate), 90)
        if not text or FILENAME_RE.match(text):
            continue
        if text.lower().startswith(("images used", "image used", "source:", "credit:")):
            continue
        return text
    return f"Illustration — {lesson_title}"


def context_note(semantic: dict[str, Any], label: str) -> str:
    for candidate in (
        semantic.get("caption", ""),
        semantic.get("text", ""),
        semantic.get("previousText", ""),
        semantic.get("nextText", ""),
        semantic.get("contextText", ""),
    ):
        text = concise(str(candidate), 240)
        if text and text != label and not FILENAME_RE.match(text):
            return text
    return ""


def attribution_for(
    asset: dict[str, Any],
    documents: dict[str, dict[str, Any]],
    site_license: dict[str, Any],
) -> tuple[str, list[str], bool]:
    texts: list[str] = []
    pages: set[str] = set()
    inherited = False
    for occurrence in asset.get("occurrences", []):
        document = documents.get(str(occurrence.get("documentId", "")), {})
        pages.update(page for page in document.get("sourcePages", []) if page)
        text = str(document.get("attribution", {}).get("text", "")).strip()
        if text and text not in texts:
            texts.append(text)
        inherited = inherited or bool(document.get("attributionInherited", False))
    if not texts:
        texts.append(str(site_license.get("attribution", "Reality Czech")))
        inherited = True
    return "\n\n".join(texts), sorted(pages), inherited


def main() -> None:
    manifest = read_json(MANIFEST_PATH)
    if manifest.get("version") != 2:
        raise MaterializationError("semantic manifest version 2 is required")
    catalog = read_json(CATALOG_PATH)
    locked_hashes = set(read_json(CHECKSUMS_PATH).get("sha256", {}).values())
    source_to_ids, titles = implemented_lessons()
    documents = {item["documentId"]: item for item in manifest.get("documents", [])}

    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    per_shard: dict[str, list[tuple[dict[str, Any], dict[str, dict[str, Any]]]]] = defaultdict(list)
    skipped = {
        "urlDuplicate": 0,
        "unmapped": 0,
        "unsupportedOrTiny": 0,
        "nonLearnerRole": 0,
    }
    for asset in manifest.get("assets", []):
        extension = Path(str(asset.get("archivePath", ""))).suffix.lower()
        if (
            asset.get("kind") != "image"
            or extension not in SUPPORTED_EXTENSIONS
            or int(asset.get("bytes", 0)) < 1024
        ):
            skipped["unsupportedOrTiny"] += 1
            continue
        if asset.get("sha256") in locked_hashes:
            skipped["urlDuplicate"] += 1
            continue
        occurrences_by_lesson = mapped_occurrences(asset, source_to_ids)
        if not occurrences_by_lesson:
            skipped["unmapped"] += 1
            continue
        semantic_by_lesson = {
            lesson_id: semantic_record(occurrences)
            for lesson_id, occurrences in occurrences_by_lesson.items()
        }
        semantic_by_lesson = {
            lesson_id: semantic
            for lesson_id, semantic in semantic_by_lesson.items()
            if semantic
        }
        if not semantic_by_lesson:
            skipped["nonLearnerRole"] += 1
            continue
        per_shard[asset["shard"]].append((asset, semantic_by_lesson))

    generated: list[dict[str, Any]] = []
    total_bytes = 0
    per_lesson: dict[str, int] = defaultdict(int)
    per_role: dict[str, int] = defaultdict(int)
    written_hashes: set[str] = set()
    for shard_name, assets in sorted(per_shard.items()):
        shard_path = VENDOR_ROOT / shard_name
        if not shard_path.is_file():
            raise MaterializationError(f"missing shard {shard_name}")
        with zipfile.ZipFile(shard_path) as archive:
            for asset, semantic_by_lesson in assets:
                payload = archive.read(asset["archivePath"])
                digest = hashlib.sha256(payload).hexdigest()
                if digest != asset["sha256"]:
                    raise MaterializationError(f"hash mismatch for {asset['archivePath']}")
                suffix = Path(asset["archivePath"]).suffix.lower()
                local_path = f"vendor/unit1/{digest}{suffix}"
                if digest not in written_hashes:
                    (MEDIA_ROOT / local_path).write_bytes(payload)
                    total_bytes += len(payload)
                    written_hashes.add(digest)
                attribution, pages, inherited = attribution_for(
                    asset,
                    documents,
                    manifest.get("siteLicense", {}),
                )
                for lesson_id, semantic in sorted(semantic_by_lesson.items()):
                    label = image_label(semantic, titles[lesson_id])
                    source_page = semantic["sourcePage"] or (
                        pages[0] if pages else "https://realityczech.org/unit-1/"
                    )
                    generated.append(
                        {
                            "id": f"vendor-{digest}-{lesson_id}",
                            "kind": "image",
                            "delivery": "vendor",
                            "lessonId": lesson_id,
                            "lessonIds": [lesson_id],
                            "label": label,
                            "sourcePage": source_page,
                            "sourcePages": pages,
                            "sourceUrl": source_page,
                            "localPath": local_path,
                            "assetUri": f"file:///android_asset/media/{local_path}",
                            "bytes": len(payload),
                            "sha256": digest,
                            "attribution": attribution,
                            "attributionInherited": inherited,
                            "provider": "vendor-document-media",
                            "semanticRole": semantic["role"],
                            "placementHeading": semantic["placementHeading"],
                            "caption": semantic["caption"],
                            "contextText": context_note(semantic, label),
                            "sourceOrder": semantic["sourceOrder"],
                        }
                    )
                    per_lesson[lesson_id] += 1
                    per_role[semantic["role"]] += 1

    catalog["assets"] = sorted(catalog.get("assets", []) + generated, key=lambda item: item["id"])
    CATALOG_PATH.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = {
        "materialized": len(generated),
        "uniqueFiles": len(written_hashes),
        "bytes": total_bytes,
        "perLesson": dict(sorted(per_lesson.items())),
        "perRole": dict(sorted(per_role.items())),
        "skipped": skipped,
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except MaterializationError as exc:
        raise SystemExit(f"vendor media materialization failed: {exc}") from exc
