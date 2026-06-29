#!/usr/bin/env python3
"""Verify committed document-only media shards without re-crawling sources."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR_ROOT = ROOT / "media/vendor/unit1-document-media"
MANIFEST_PATH = VENDOR_ROOT / "manifest.json"


def fail(message: str) -> None:
    print(f"vendor media verification failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not MANIFEST_PATH.exists():
        print("no committed document-media manifest yet; ingestion has not been merged")
        return

    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid manifest JSON: {exc}")
    if manifest.get("version") != 1:
        fail("unsupported manifest version")

    assets = manifest.get("assets")
    shards = manifest.get("shards")
    if not isinstance(assets, list) or not assets:
        fail("manifest contains no assets")
    if not isinstance(shards, list) or not shards:
        fail("manifest contains no shards")

    expected_by_shard: dict[str, dict[str, dict]] = {}
    hashes: set[str] = set()
    for asset in assets:
        digest = asset.get("sha256")
        shard = asset.get("shard")
        archive_path = asset.get("archivePath")
        if not isinstance(digest, str) or len(digest) != 64:
            fail(f"invalid asset hash: {digest!r}")
        if digest in hashes:
            fail(f"duplicate asset hash: {digest}")
        hashes.add(digest)
        if not isinstance(shard, str) or not isinstance(archive_path, str):
            fail(f"asset {digest} lacks shard or archivePath")
        expected_by_shard.setdefault(shard, {})[archive_path] = asset

    seen_paths: set[str] = set()
    for shard in shards:
        filename = shard.get("filename")
        if not isinstance(filename, str):
            fail("shard lacks filename")
        path = VENDOR_ROOT / filename
        if not path.is_file():
            fail(f"missing shard: {filename}")
        if path.stat().st_size != shard.get("bytes"):
            fail(f"size mismatch for {filename}")
        if sha256_file(path) != shard.get("sha256"):
            fail(f"SHA-256 mismatch for {filename}")

        expected = expected_by_shard.get(filename, {})
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if names != set(expected):
                fail(f"archive membership mismatch for {filename}")
            for archive_path, asset in expected.items():
                payload = archive.read(archive_path)
                if len(payload) != asset.get("bytes"):
                    fail(f"asset size mismatch: {archive_path}")
                if hashlib.sha256(payload).hexdigest() != asset["sha256"]:
                    fail(f"asset hash mismatch: {archive_path}")
                seen_paths.add(archive_path)

    if len(seen_paths) != len(assets):
        fail(f"verified {len(seen_paths)} of {len(assets)} assets")
    print(f"verified {len(assets)} document-media asset(s) across {len(shards)} shard(s)")


if __name__ == "__main__":
    main()
