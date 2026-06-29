from __future__ import annotations

import hashlib
import html
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

USER_AGENT = "RealityCzechMediaDiscovery/1.0 (+https://github.com/castlec/realityczech)"
MAX_BYTES = 150 * 1024 * 1024
FIRST_PARTY_HOSTS = {"realityczech.org", "www.realityczech.org"}
COURSE_HOSTS = FIRST_PARTY_HOSTS | {
    "docs.google.com", "drive.google.com", "drive.usercontent.google.com",
    "utexas.instructure.com", "quizlet.com", "www.quizlet.com",
    "youtube.com", "www.youtube.com", "youtu.be", "english.radio.cz", "www.radio.cz",
}
AUDIO_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".oga", ".ogg", ".opus", ".wav"}
VIDEO_EXTENSIONS = {".m4v", ".mp4", ".webm"}
IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
ATTRIBUTION_MARKERS = (
    "images used in this document", "image credits", "photo credits", "audio credits",
    "media credits", "sources", "attribution", "creative commons", "forvo",
)
DOC_ID_RE = re.compile(r"/document/(?:u/\d+/)?d/([A-Za-z0-9_-]+)")
YOUTUBE_ID_RE = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/))([A-Za-z0-9_-]{11})")
DAY_RE = re.compile(r"\b1\.(?:[1-9]|1[01])\b")

class DiscoveryError(RuntimeError):
    pass

@dataclass
class FetchResult:
    data: bytes
    content_type: str
    final_url: str

@dataclass
class Anchor:
    href: str
    text: str = ""
    images: list[str] = field(default_factory=list)

class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._anchor: Anchor | None = None
        self.anchors: list[Anchor] = []
        self.media_urls: list[tuple[str, str]] = []
        self.text_parts: list[str] = []
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "title": self._in_title = True
        if tag == "meta":
            key = values.get("name") or values.get("property")
            if key and values.get("content"): self.meta[key.lower()] = values["content"]
        if tag == "a" and values.get("href"): self._anchor = Anchor(values["href"])
        if tag == "img":
            alt = values.get("alt", "").strip()
            if self._anchor is not None and alt: self._anchor.images.append(alt)
        for attribute in ("src", "data-src", "data-lazy-src", "data-audio", "data-video", "poster"):
            if values.get(attribute): self.media_urls.append((values[attribute], f"{tag}:{attribute}"))
        if tag in {"audio", "video", "source", "track", "iframe", "embed", "object"}:
            for attribute in ("src", "data", "href"):
                if values.get(attribute): self.media_urls.append((values[attribute], f"{tag}:{attribute}"))

    def handle_endtag(self, tag: str) -> None:
        if tag == "title": self._in_title = False
        if tag == "a" and self._anchor is not None:
            self._anchor.text = " ".join(self._anchor.text.split())
            self.anchors.append(self._anchor)
            self._anchor = None

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if not cleaned: return
        self.text_parts.append(cleaned)
        if self._in_title: self.title = f"{self.title} {cleaned}".strip()
        if self._anchor is not None: self._anchor.text = f"{self._anchor.text} {cleaned}".strip()

def fetch(url: str, attempts: int = 3) -> FetchResult:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            with urllib.request.urlopen(request, timeout=60) as response:
                status = getattr(response, "status", 200)
                if not 200 <= status < 300: raise DiscoveryError(f"HTTP {status}")
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES: raise DiscoveryError(f"response exceeds {MAX_BYTES} bytes")
                return FetchResult(data, response.headers.get_content_type().lower(), response.geturl())
        except (urllib.error.URLError, TimeoutError, DiscoveryError) as exc:
            last_error = exc
            if attempt < attempts: time.sleep(attempt * 2)
    raise DiscoveryError(f"failed to fetch {url}: {last_error}")

def sha256(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def absolute(base: str, value: str) -> str: return urllib.parse.urljoin(base, html.unescape(value.strip()))

def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, urllib.parse.urlencode(query), ""))

def doc_id_from_url(url: str) -> str | None:
    match = DOC_ID_RE.search(url)
    return match.group(1) if match else None

def docx_export_url(doc_id: str) -> str: return f"https://docs.google.com/document/d/{doc_id}/export?format=docx"

def classify_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix in AUDIO_EXTENSIONS: return "audio"
    if suffix in VIDEO_EXTENSIONS: return "video"
    if suffix in IMAGE_EXTENSIONS: return "image"
    if parsed.netloc in {"youtube.com", "www.youtube.com", "youtu.be"} or YOUTUBE_ID_RE.search(url): return "youtube"
    if parsed.netloc in {"drive.google.com", "drive.usercontent.google.com"}: return "google-drive"
    if parsed.netloc == "docs.google.com": return "google-document"
    if parsed.netoc == "utexas.instructure.com": return "canvas"
    if "quizlet.com" in parsed.netloc: return "quizlet"
    return "link"

def attribution_context(text_parts: list[str], anchors: list[Anchor]) -> dict[str, Any]:
    full_text = "\n".join(text_parts)
    lowered = full_text.lower()
    positions = [lowered.find(marker) for marker in ATTRIBUTION_MARKERS if marker in lowered]
    start = min(positions) if positions else -1
    excerpt = full_text[start:start + 12000] if start >= 0 else ""
    links = []
    for anchor in anchors:
        label = " ".join([anchor.text, *anchor.images]).strip()
        if start >= 0 or any(token in label.lower() for token in ("credit", "source", "license", "creative commons", "forvo")):
            links.append({"label": label, "url": anchor.href})
    return {"text": excerpt, "links": links}

def parse_html_page(url: str, data: bytes) -> dict[str, Any]:
    parser = PageParser(); parser.feed(data.decode("utf-8", errors="replace"))
    anchors = [
        {"url": normalize_url(absolute(url, a.href)), "label": " ".join([a.text, *a.images]).strip()}
        for a in parser.anchors if a.href and not a.href.startswith(("mailto:", "javascript:", "#"))
    ]
    media = [
        {"url": normalize_url(absolute(url, value)), "discoveredBy": method}
        for value, method in parser.media_urls if value and not value.startswith(("data:", "javascript:"))
    ]
    return {
        "url": url, "title": parser.title or parser.meta.get("og:title", ""),
        "description": parser.meta.get("description") or parser.meta.get("og:description", ""),
        "text": parser.text_parts, "anchors": anchors, "media": media,
        "attribution": attribution_context(parser.text_parts, parser.anchors),
    }

def relevant_unit_link(anchor: dict[str, str]) -> bool:
    url, label = anchor["url"], anchor["label"]
    parsed = urllib.parse.urlsplit(url)
    if parsed.netloc not in COURSE_HOSTS: return False
    if parsed.netloc in FIRST_PARTY_HOSTS:
        if parsed.path in {"/", "/unit-1/", "/units/"}: return False
        return bool(DAY_RE.search(label)) or parsed.path.startswith("/videos/")
    return bool(DAY_RE.search(label)) or parsed.netloc in {"docs.google.com", "drive.google.com"}

def source_attribution(page: dict[str, Any]) -> dict[str, Any]:
    attribution = page.get("attribution", {})
    text, links = attribution.get("text", ""), attribution.get("links", [])
    if not text and urllib.parse.urlsplit(page["url"]).netloc in FIRST_PARTY_HOSTS:
        text = "Reality Czech by Christian Hilchey and COERLL; Creative Commons. Preserve item-level credits from the source page or document."
    return {"text": text, "links": links}
