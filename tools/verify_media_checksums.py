#!/usr/bin/env python3
"""Verify every CI-downloaded bundled media file against the reviewed hash lock."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKSUMS_FILE = ROOT / "media/checksums.json"
MEDIA_ROOT = ROOT / "app/src/main/assets/media"
CATALOG_FILE = MEDIA_ROOT / "catalog.json"


def fail(message: str) -> None:
    print(f"media checksum verification failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing file: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    lock = read_json(CHECKSUMS_FILE)
    catalog = read_json(CATALOG_FILE)

    if lock.get("version") != 1:
        fail("unsupported checksum-lock version")

    expected = lock.get("sha256")
    if not isinstance(expected, dict) or not expected:
        fail("checksum lock contains no hashes")

    bundled = {
        item.get("id"): item
        for item in catalog.get("assets", [])
        if item.get("delivery") == "bundle"
    }

    expected_ids = set(expected)
    actual_ids = set(bundled)
    missing_ids = sorted(expected_ids - actual_ids)
    unlocked_ids = sorted(actual_ids - expected_ids)
    if missing_ids:
        fail(f"locked media missing from generated catalog: {missing_ids}")
    if unlocked_ids:
        fail(f"bundled media lacks a reviewed checksum: {unlocked_ids}")

    for asset_id in sorted(expected_ids):
        expected_hash = expected[asset_id]
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            fail(f"invalid locked SHA-256 for {asset_id}: {expected_hash!r}")

        item = bundled[asset_id]
        local_path = item.get("localPath")
        if not isinstance(local_path, str) or not local_path:
            fail(f"catalog item {asset_id} has no localPath")

        media_file = MEDIA_ROOT / local_path
        if not media_file.is_file():
            fail(f"downloaded file is missing for {asset_id}: {local_path}")

        actual_hash = sha256(media_file)
        if actual_hash != expected_hash:
            fail(
                f"{asset_id} changed: expected {expected_hash}, got {actual_hash}; "
                "review the upstream change before updating media/checksums.json"
            )

        catalog_hash = item.get("sha256")
        if catalog_hash != actual_hash:
            fail(
                f"catalog hash mismatch for {asset_id}: "
                f"catalog={catalog_hash!r}, file={actual_hash}"
            )

    print(f"verified {len(expected_ids)} bundled media checksum(s)")


if __name__ == "__main__":
    main()
