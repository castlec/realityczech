from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from .archive import write_vendor_archive
from .unit1 import SEED
from .web import FIRST_PARTY_HOSTS

CRITICAL_HOSTS = FIRST_PARTY_HOSTS | {"docs.google.com", "drive.google.com"}


def finalize(
    state: dict[str, Any],
    repository_root: Path,
    archive_path: Path,
    report_path: Path,
    unresolved_path: Path,
) -> dict[str, Any]:
    pages = state["pages"]
    documents = state["documents"]
    locations = state["locations"]
    vendor_assets = write_vendor_archive(archive_path, repository_root, documents, SEED)

    unresolved: list[dict[str, Any]] = list(state["errors"])
    for page in pages:
        attribution = page.get("attribution", {})
        if not attribution.get("text") and not attribution.get("links"):
            unresolved.append(
                {"url": page["url"], "error": "first-party page has no attribution record"}
            )
    for document in documents:
        attribution = document.get("attribution", {})
        if document["extractedMedia"] and not (
            attribution.get("text") or attribution.get("links")
        ):
            unresolved.append(
                {
                    "url": document["exportUrl"],
                    "error": "embedded document media has no attribution section",
                }
            )
    for item in locations.values():
        host = urllib.parse.urlsplit(item["url"]).netloc
        if host in CRITICAL_HOSTS and not item.get("attribution"):
            unresolved.append(
                {"url": item["url"], "error": "critical media location lacks attribution"}
            )

    counts = {
        "tocLinks": len(state["toc"]),
        "firstPartyPages": len(pages),
        "externalCourseLinks": len(state["external"]),
        "googleDocuments": len(documents),
        "documentMediaOccurrences": sum(len(doc["extractedMedia"]) for doc in documents),
        "uniqueDocumentMedia": len(vendor_assets),
        "mediaLocations": len(locations),
        "unresolved": len(unresolved),
    }
    report = {
        "version": 1,
        "seed": SEED,
        "siteLicense": {
            "name": "Creative Commons",
            "source": "https://realityczech.org/",
            "attribution": "Reality Czech, Christian Hilchey, and COERLL",
        },
        "counts": counts,
        "pages": sorted(pages, key=lambda item: item["url"]),
        "externalCourseLinks": sorted(state["external"], key=lambda item: item["url"]),
        "documents": documents,
        "mediaLocations": sorted(locations.values(), key=lambda item: item["url"]),
        "documentVendorArchive": str(archive_path.relative_to(repository_root)),
        "documentVendorAssets": vendor_assets,
        "unresolved": unresolved,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    unresolved_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    unresolved_path.write_text(
        json.dumps(unresolved, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for issue in unresolved:
        print(
            f"UNRESOLVED {issue.get('url', '<unknown>')}: {issue.get('error', issue)}",
            file=sys.stderr,
        )
    return report
