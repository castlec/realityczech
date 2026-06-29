from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from .archive import vendor_assets_from_documents, write_vendor_archive
from .unit1 import SEED
from .web import FIRST_PARTY_HOSTS

CRITICAL_HOSTS = FIRST_PARTY_HOSTS | {"docs.google.com", "drive.google.com"}
OBSOLETE_CROSS_REFERENCE = (
    "https://docs.google.com/document/d/e/"
    "2PACX-1vS46stE4LR7JIntCR0grGDXKpM33WinQ3YBUBRzQsQ497t71YL7uLFPN88zhaH08OhhZyRBtfduo4z9/pub"
)


def is_warning(item: dict[str, Any]) -> bool:
    return (
        item.get("url") == OBSOLETE_CROSS_REFERENCE
        and "410" in str(item.get("error", ""))
    )


def finalize(
    state: dict[str, Any],
    repository_root: Path,
    archive_path: Path | None,
    report_path: Path,
    unresolved_path: Path,
) -> dict[str, Any]:
    pages = state["pages"]
    documents = state["documents"]
    locations = state["locations"]
    if archive_path is None:
        vendor_assets = vendor_assets_from_documents(repository_root, documents)
    else:
        vendor_assets = write_vendor_archive(archive_path, repository_root, documents, SEED)

    warnings = [item for item in state["errors"] if is_warning(item)]
    unresolved: list[dict[str, Any]] = [
        item for item in state["errors"] if not is_warning(item)
    ]
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
        "publishedDocuments": len(state.get("publishedDocuments", [])),
        "googleDocuments": len(documents),
        "documentMediaOccurrences": sum(len(doc["extractedMedia"]) for doc in documents),
        "uniqueDocumentMedia": len(vendor_assets),
        "mediaLocations": len(locations),
        "warnings": len(warnings),
        "unresolved": len(unresolved),
    }
    report: dict[str, Any] = {
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
        "publishedDocuments": state.get("publishedDocuments", []),
        "documents": documents,
        "mediaLocations": sorted(locations.values(), key=lambda item: item["url"]),
        "documentVendorAssets": vendor_assets,
        "warnings": warnings,
        "unresolved": unresolved,
    }
    if archive_path is not None:
        report["documentVendorArchive"] = str(archive_path.relative_to(repository_root))

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
    for warning in warnings:
        print(
            f"WARNING {warning.get('url', '<unknown>')}: {warning.get('error', warning)}",
            file=sys.stderr,
        )
    for issue in unresolved:
        print(
            f"UNRESOLVED {issue.get('url', '<unknown>')}: {issue.get('error', issue)}",
            file=sys.stderr,
        )
    if unresolved:
        bridge_report = {
            "status": "failed",
            "assetCount": 0,
            "bundledCount": 0,
            "streamCount": 0,
            "results": [],
            "errors": [
                f"{item.get('url', '<unknown>')}: {item.get('error', item)}"
                for item in unresolved
            ],
            "unit1Discovery": report,
        }
        (repository_root / "media/sync-report.json").write_text(
            json.dumps(bridge_report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raise SystemExit(1)
    return report
