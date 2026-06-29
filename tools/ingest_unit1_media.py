#!/usr/bin/env python3
"""Run the expensive Unit 1 crawl and write durable repository media shards."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from media_discovery.part2 import finalize
from media_discovery.shards import write_repository_shards
from media_discovery.unit1 import collect

ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_ROOT = ROOT / "media/discovery/unit1"
REPORT_PATH = ROOT / "media/discovery/unit1-report.json"
UNRESOLVED_PATH = ROOT / "media/discovery/unit1-unresolved.json"
SHARD_ROOT = ROOT / "media/vendor/unit1-document-media"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    if DISCOVERY_ROOT.exists():
        shutil.rmtree(DISCOVERY_ROOT)
    DISCOVERY_ROOT.mkdir(parents=True)

    state = collect(ROOT, DISCOVERY_ROOT, args.workers)
    report = finalize(
        state,
        ROOT,
        None,
        REPORT_PATH,
        UNRESOLVED_PATH,
    )
    manifest = write_repository_shards(ROOT, SHARD_ROOT, report)
    print(
        json.dumps(
            {
                "documents": len(manifest["documents"]),
                "assets": len(manifest["assets"]),
                "shards": len(manifest["shards"]),
                "bytes": sum(shard["bytes"] for shard in manifest["shards"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
