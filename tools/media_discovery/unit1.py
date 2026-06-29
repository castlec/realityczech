from __future__ import annotations

import concurrent.futures
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from .office import extract_docx
from .web import (
    FIRST_PARTY_HOSTS,
    classify_url,
    doc_id_from_url,
    docx_export_url,
    fetch,
    normalize_url,
    parse_html_page,
    relevant_unit_link,
    sha256,
    source_attribution,
)

SEED = "https://realityczech.org/unit-1/"
UNIT_ACTIVITY = re.compile(r"\b1\.(?:[1-9]|1[01])\b")


def add_location(
    inventory: dict[str, dict[str, Any]],
    url: str,
    source_page: str,
    label: str = "",
    method: str = "link",
    attribution: dict[str, Any] | None = None,
) -> None:
    normalized = normalize_url(url)
    if urllib.parse.urlsplit(normalized).scheme not in {"http", "https"}:
        return
    current = inventory.setdefault(
        normalized,
        {
            "url": normalized,
            "kind": classify_url(normalized),
            "sourcePages": [],
            "labels": [],
            "discoveredBy": [],
            "attribution": attribution or {},
        },
    )
    if source_page not in current["sourcePages"]:
        current["sourcePages"].append(source_page)
    if label and label not in current["labels"]:
        current["labels"].append(label)
    if method not in current["discoveredBy"]:
        current["discoveredBy"].append(method)
    if attribution and not current.get("attribution"):
        current["attribution"] = attribution


def crawl_page(anchor: dict[str, str]) -> dict[str, Any]:
    result = fetch(anchor["url"])
    page = parse_html_page(result.final_url, result.data)
    page["tocLabel"] = anchor["label"]
    page["finalUrl"] = result.final_url
    page["contentType"] = result.content_type
    page["bytes"] = len(result.data)
    page["sha256"] = sha256(result.data)
    page["attribution"] = source_attribution(page)
    return page


def is_unit1_activity(item: dict[str, str]) -> bool:
    label = item["label"]
    host = urllib.parse.urlsplit(item["url"]).netloc
    if UNIT_ACTIVITY.search(label):
        return True
    return host in {"docs.google.com", "drive.google.com"} and "unit 1" in label.lower()


def collect(repository_root: Path, output_root: Path, workers: int = 8) -> dict[str, Any]:
    seed_result = fetch(SEED)
    seed = parse_html_page(SEED, seed_result.data)
    seed["attribution"] = source_attribution(seed)
    toc = {
        item["url"]: item
        for item in seed["anchors"]
        if relevant_unit_link(item) and is_unit1_activity(item)
    }

    first_party = [
        item
        for item in toc.values()
        if urllib.parse.urlsplit(item["url"]).netloc in FIRST_PARTY_HOSTS
    ]
    external = [
        {
            "url": item["url"],
            "label": item["label"],
            "kind": classify_url(item["url"]),
            "delivery": "external-link",
            "attribution": {
                "text": "External course resource linked by the Reality Czech Unit 1 table of contents; not redistributed.",
                "links": [{"label": item["label"], "url": item["url"]}],
            },
        }
        for item in toc.values()
        if item not in first_party
    ]
    pages: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(crawl_page, item): item for item in first_party}
        for future in concurrent.futures.as_completed(futures):
            item = futures[future]
            try:
                page = future.result()
                pages.append(page)
                print(f"page {page['url']}")
            except Exception as exc:  # noqa: BLE001
                errors.append({"url": item["url"], "label": item["label"], "error": str(exc)})
                print(f"ERROR page {item['url']}: {exc}", file=sys.stderr)

    documents_by_id: dict[str, set[str]] = {}
    locations: dict[str, dict[str, Any]] = {}
    for page in [seed, *pages]:
        attribution = source_attribution(page)
        for anchor in page.get("anchors", []):
            doc_id = doc_id_from_url(anchor["url"])
            if doc_id:
                documents_by_id.setdefault(doc_id, set()).add(page["url"])
            if classify_url(anchor["url"]) != "link":
                add_location(
                    locations,
                    anchor["url"],
                    page["url"],
                    anchor.get("label", ""),
                    "anchor",
                    attribution,
                )
        for media in page.get("media", []):
            add_location(
                locations,
                media["url"],
                page["url"],
                method=media["discoveredBy"],
                attribution=attribution,
            )

    documents: list[dict[str, Any]] = []
    for doc_id, source_pages in sorted(documents_by_id.items()):
        export_url = docx_export_url(doc_id)
        try:
            result = fetch(export_url)
            if not result.data.startswith(b"PK"):
                raise RuntimeError(f"DOCX export returned {result.content_type}")
            document = extract_docx(
                doc_id,
                sorted(source_pages)[0],
                export_url,
                result.final_url,
                result.data,
                output_root / "documents" / doc_id,
                repository_root,
            )
            document["sourcePages"] = sorted(source_pages)
            documents.append(document)
            print(f"document {doc_id}: {len(document['extractedMedia'])} embedded item(s)")
            for link in document["hyperlinks"]:
                add_location(
                    locations,
                    link["url"],
                    sorted(source_pages)[0],
                    link.get("context", ""),
                    "docx-hyperlink",
                    document["attribution"],
                )
        except Exception as exc:  # noqa: BLE001
            errors.append({"url": export_url, "label": doc_id, "error": str(exc)})
            print(f"ERROR document {doc_id}: {exc}", file=sys.stderr)

    return {
        "seed": seed,
        "toc": toc,
        "pages": pages,
        "external": external,
        "documents": documents,
        "locations": locations,
        "errors": errors,
    }
