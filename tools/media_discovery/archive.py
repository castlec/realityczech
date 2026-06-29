from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any


def vendor_assets_from_documents(
    repository_root: Path,
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_hash: dict[str, list[dict[str, Any]]] = {}
    for document in documents:
        for item in document["extractedMedia"]:
            by_hash.setdefault(item["sha256"], []).append(item)

    assets: list[dict[str, Any]] = []
    for digest, occurrences in sorted(by_hash.items()):
        first = occurrences[0]
        source = repository_root / first["localPath"]
        assets.append(
            {
                "sha256": digest,
                "kind": first["kind"],
                "bytes": first["bytes"],
                "archivePath": f"media/{digest}{source.suffix}",
                "sourcePath": first["localPath"],
                "occurrences": occurrences,
            }
        )
    return assets


def write_vendor_archive(
    archive_path: Path,
    repository_root: Path,
    documents: list[dict[str, Any]],
    source_unit: str,
) -> list[dict[str, Any]]:
    assets = vendor_assets_from_documents(repository_root, documents)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for asset in assets:
            archive.write(
                repository_root / asset["sourcePath"],
                asset["archivePath"],
            )
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "sourceUnit": source_unit,
                    "license": "CC BY-SA; preserve item-level attribution records",
                    "assets": assets,
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
        )
    return assets
