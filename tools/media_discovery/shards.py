from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

MAX_SHARD_BYTES = 95 * 1024 * 1024
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o100644 << 16
    return info


def write_repository_shards(
    repository_root: Path,
    output_dir: Path,
    report: dict[str, Any],
) -> dict[str, Any]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    assets = report["documentVendorAssets"]
    groups: dict[str, list[dict[str, Any]]] = {value: [] for value in "0123456789abcdef"}
    for asset in assets:
        source_path = asset.get("sourcePath")
        if not source_path:
            raise RuntimeError(f"vendor asset lacks sourcePath: {asset['sha256']}")
        groups[asset["sha256"][0]].append(asset)

    shards: list[dict[str, Any]] = []
    for prefix, items in groups.items():
        if not items:
            continue
        filename = f"shard-{prefix}.zip"
        shard_path = output_dir / filename
        with zipfile.ZipFile(shard_path, "w") as archive:
            for asset in sorted(items, key=lambda item: item["sha256"]):
                source = repository_root / asset["sourcePath"]
                payload = source.read_bytes()
                if hashlib.sha256(payload).hexdigest() != asset["sha256"]:
                    raise RuntimeError(f"source hash changed for {asset['sha256']}")
                archive.writestr(_zip_info(asset["archivePath"]), payload)
        size = shard_path.stat().st_size
        if size > MAX_SHARD_BYTES:
            raise RuntimeError(f"{filename} is {size} bytes; exceeds GitHub file limit guard")
        shards.append(
            {
                "filename": filename,
                "bytes": size,
                "sha256": _sha256_file(shard_path),
                "assetCount": len(items),
                "assetHashes": sorted(item["sha256"] for item in items),
            }
        )

    documents = [
        {
            "documentId": document["documentId"],
            "sourcePages": document.get("sourcePages", [document.get("sourcePage", "")]),
            "exportUrl": document["exportUrl"],
            "sha256": document["sha256"],
            "attribution": document.get("attribution", {}),
            "attributionInherited": document.get("attributionInherited", False),
            "paragraphCount": len(document.get("paragraphs", [])),
            "headings": list(
                dict.fromkeys(
                    paragraph.get("heading", "")
                    for paragraph in document.get("paragraphs", [])
                    if paragraph.get("heading")
                )
            ),
            "extractedMediaCount": len(document["extractedMedia"]),
        }
        for document in report["documents"]
    ]
    classification_counts = Counter(
        occurrence.get("classification", "unclassified")
        for asset in assets
        for occurrence in asset.get("occurrences", [])
    )
    manifest = {
        "version": 2,
        "sourceUnit": report["seed"],
        "siteLicense": report["siteLicense"],
        "counts": {
            **report["counts"],
            "semanticClassifications": dict(sorted(classification_counts.items())),
        },
        "documents": documents,
        "warnings": report.get("warnings", []),
        "semanticIndex": "content-index.json",
        "shards": shards,
        "assets": [
            {
                "sha256": asset["sha256"],
                "kind": asset["kind"],
                "bytes": asset["bytes"],
                "archivePath": asset["archivePath"],
                "shard": f"shard-{asset['sha256'][0]}.zip",
                "occurrences": asset["occurrences"],
            }
            for asset in assets
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    content_index = {
        "version": 1,
        "sourceUnit": report["seed"],
        "documents": [
            {
                "documentId": document["documentId"],
                "sourcePage": document.get("sourcePage", ""),
                "sourcePages": document.get("sourcePages", []),
                "exportUrl": document["exportUrl"],
                "attribution": document.get("attribution", {}),
                "attributionInherited": document.get("attributionInherited", False),
                "paragraphs": document.get("paragraphs", []),
                "hyperlinks": document.get("hyperlinks", []),
            }
            for document in report["documents"]
        ],
    }
    (output_dir / "content-index.json").write_text(
        json.dumps(content_index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
