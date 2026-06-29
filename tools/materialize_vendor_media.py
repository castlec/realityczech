#!/usr/bin/env python3
"""Materialize committed document-only media for implemented lessons."""

from __future__ import annotations

import hashlib
import json
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
OUTPUT_ROOT = MEDIA_ROOT / "vendor/unit1"
SUPPORTED_KINDS = {"image", "audio", "video"}


class MaterializationError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise MaterializationError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc


def implemented_lessons() -> tuple[dict[str, str], dict[str, str]]:
    index = read_json(ROOT / "app/src/main/assets/course/index.json")
    source_to_id: dict[str, str] = {}
    titles: dict[str, str] = {}
    for unit in index.get("units", []):
        for filename in unit.get("lessonFiles", []):
            lesson = read_json(LESSON_ROOT / filename)
            lesson_id = lesson["id"]
            source = lesson["sourceUrl"].rstrip("/") + "/"
            source_to_id[source] = lesson_id
            titles[lesson_id] = lesson["title"]
    return source_to_id, titles


def lesson_ids_for(asset: dict[str, Any], source_to_id: dict[str, str]) -> list[str]:
    result: set[str] = set()
    for occurrence in asset.get("occurrences", []):
        source = str(occurrence.get("documentSource", "")).rstrip("/") + "/"
        lesson_id = source_to_id.get(source)
        if lesson_id:
            result.add(lesson_id)
    return sorted(result)


def document_metadata(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["documentId"]: item for item in manifest.get("documents", [])}


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
    catalog = read_json(CATALOG_PATH)
    locked_hashes = set(read_json(CHECKSUMS_PATH).get("sha256", {}).values())
    source_to_id, titles = implemented_lessons()
    documents = document_metadata(manifest)

    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    per_shard: dict[str, list[dict[str, Any]]] = defaultdict(list)
    skipped_duplicates = 0
    skipped_unmapped = 0
    skipped_unsupported = 0
    for asset in manifest.get("assets", []):
        if asset.get("kind") not in SUPPORTED_KINDS or int(asset.get("bytes", 0)) < 1024:
            skipped_unsupported += 1
            continue
        if asset.get("sha256") in locked_hashes:
            skipped_duplicates += 1
            continue
        lesson_ids = lesson_ids_for(asset, source_to_id)
        if not lesson_ids:
            skipped_unmapped += 1
            continue
        selected = dict(asset)
        selected["lessonIds"] = lesson_ids
        per_shard[selected["shard"]].append(selected)

    generated: list[dict[str, Any]] = []
    total_bytes = 0
    for shard_name, assets in sorted(per_shard.items()):
        shard_path = VENDOR_ROOT / shard_name
        with zipfile.ZipFile(shard_path) as archive:
            for asset in assets:
                payload = archive.read(asset["archivePath"])
                digest = hashlib.sha256(payload).hexdigest()
                if digest != asset["sha256"]:
                    raise MaterializationError(f"hash mismatch for {asset['archivePath']}")
                suffix = Path(asset["archivePath"]).suffix.lower() or ".bin"
                local_path = f"vendor/unit1/{digest}{suffix}"
                destination = MEDIA_ROOT / local_path
                destination.write_bytes(payload)
                attribution, pages, inherited = attribution_for(
                    asset,
                    documents,
                    manifest.get("siteLicense", {}),
                )
                primary_lesson = asset["lessonIds"][0]
                generated.append(
                    {
                        "id": f"vendor-{digest}",
                        "kind": asset["kind"],
                        "delivery": "bundle",
                        "lessonId": primary_lesson,
                        "lessonIds": asset["lessonIds"],
                        "label": f"Source media — {titles[primary_lesson]}",
                        "sourcePage": pages[0] if pages else "https://realityczech.org/unit-1/",
                        "sourcePages": pages,
                        "sourceUrl": pages[0] if pages else "https://realityczech.org/unit-1/",
                        "localPath": local_path,
                        "assetUri": f"file:///android_asset/media/{local_path}",
                        "bytes": len(payload),
                        "sha256": digest,
                        "attribution": attribution,
                        "attributionInherited": inherited,
                        "provider": "vendor-document-media",
                    }
                )
                total_bytes += len(payload)

    catalog["assets"] = sorted(
        [item for item in catalog.get("assets", []) if item.get("provider") != "vendor-document-media"]
        + generated,
        key=lambda item: item["id"],
    )
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "materialized": len(generated),
                "bytes": total_bytes,
                "lessons": sorted({lesson for item in generated for lesson in item["lessonIds"]}),
                "skippedUrlDuplicates": skipped_duplicates,
                "skippedUnmapped": skipped_unmapped,
                "skippedUnsupportedOrTiny": skipped_unsupported,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except MaterializationError as exc:
        raise SystemExit(f"vendor media materialization failed: {exc}") from exc
