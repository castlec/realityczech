from __future__ import annotations

import concurrent.futures
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from . import web as web_module
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
PUBLISHED_DOC_MARKER = "/document/d/e/"
DOCUMENT_MAX_BYTES = 600 * 1024 * 1024
SITE_LICENSE_URL = "https://realityczech.org/about/"


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


def inherited_attribution(source_page: str, page_attributions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    inherited = dict(page_attributions.get(source_page, {}))
    links = list(inherited.get("links", []))
    links.extend(
        [
            {"label": "Reality Czech source page", "url": source_page},
            {"label": "Reality Czech licensing declaration", "url": SITE_LICENSE_URL},
        ]
    )
    inherited["links"] = links
    inherited["text"] = (
        inherited.get("text")
        or "Reality Czech by Christian Hilchey and COERLL; Creative Commons."
    )
    inherited["scope"] = "site-level inherited; no narrower item-specific credits found in document"
    return inherited


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

    page_attributions = {
        page["url"]: source_attribution(page)
        for page in [seed, *pages]
    }
    documents_by_id: dict[str, set[str]] = {}
    published_documents_by_url: dict[str, set[str]] = {}
    locations: dict[str, dict[str, Any]] = {}
    for page in [seed, *pages]:
        attribution = source_attribution(page)
        for anchor in page.get("anchors", []):
            anchor_url = anchor["url"]
            if PUBLISHED_DOC_MARKER in urllib.parse.urlsplit(anchor_url).path:
                published_documents_by_url.setdefault(anchor_url, set()).add(page["url"])
            else:
                doc_id = doc_id_from_url(anchor_url)
                if doc_id and doc_id != "e":
                    documents_by_id.setdefault(doc_id, set()).add(page["url"])
            if classify_url(anchor_url) != "link":
                add_location(
                    locations,
                    anchor_url,
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

    published_documents: list[dict[str, Any]] = []
    for published_url, source_pages in sorted(published_documents_by_url.items()):
        try:
            result = fetch(published_url)
            published = parse_html_page(result.final_url, result.data)
            source_page = sorted(source_pages)[0]
            published["sourcePages"] = sorted(source_pages)
            published["finalUrl"] = result.final_url
            published["bytes"] = len(result.data)
            published["sha256"] = sha256(result.data)
            published["attribution"] = source_attribution(published)
            if not published["attribution"].get("text") and not published["attribution"].get("links"):
                published["attribution"] = inherited_attribution(source_page, page_attributions)
            published_documents.append(published)
            for anchor in published.get("anchors", []):
                add_location(
                    locations,
                    anchor["url"],
                    published_url,
                    anchor.get("label", ""),
                    "published-document-anchor",
                    published["attribution"],
                )
            for media in published.get("media", []):
                add_location(
                    locations,
                    media["url"],
                    published_url,
                    method="published-document-media",
                    attribution=published["attribution"],
                )
            print(f"published document {published_url}")
        except Exception as exc:  # noqa: BLE001
            errors.append({"url": published_url, "label": published_url, "error": str(exc)})
            print(f"ERROR published document {published_url}: {exc}", file=sys.stderr)

    documents: list[dict[str, Any]] = []
    original_max_bytes = web_module.MAX_BYTES
    web_module.MAX_BYTES = DOCUMENT_MAX_BYTES
    try:
        for doc_id, source_pages in sorted(documents_by_id.items()):
            export_url = docx_export_url(doc_id)
            try:
                result = fetch(export_url)
                if not result.data.startswith(b"PK"):
                    raise RuntimeError(f"DOCX export returned {result.content_type}")
                source_page = sorted(source_pages)[0]
                document = extract_docx(
                    doc_id,
                    source_page,
                    export_url,
                    result.final_url,
                    result.data,
                    output_root / "documents" / doc_id,
                    repository_root,
                )
                document["sourcePages"] = sorted(source_pages)
                if document["extractedMedia"] and not (
                    document["attribution"].get("text")
                    or document["attribution"].get("links")
                ):
                    document["attribution"] = inherited_attribution(source_page, page_attributions)
                    document["attributionInherited"] = True
                else:
                    document["attributionInherited"] = False
                documents.append(document)
                print(f"document {doc_id}: {len(document['extractedMedia'])} embedded item(s)")
                for link in document["hyperlinks"]:
                    add_location(
                        locations,
                        link["url"],
                        source_page,
                        link.get("context", ""),
                        "docx-hyperlink",
                        document["attribution"],
                    )
            except Exception as exc:  # noqa: BLE001
                errors.append({"url": export_url, "label": doc_id, "error": str(exc)})
                print(f"ERROR document {doc_id}: {exc}", file=sys.stderr)
    finally:
        web_module.MAX_BYTES = original_max_bytes

    return {
        "seed": seed,
        "toc": toc,
        "pages": pages,
        "external": external,
        "publishedDocuments": published_documents,
        "documents": documents,
        "locations": locations,
        "errors": errors,
    }
