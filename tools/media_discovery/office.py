from __future__ import annotations

import hashlib
import posixpath
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from .web import ATTRIBUTION_MARKERS

NAMESPACES = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "v": "urn:schemas-microsoft-com:vml",
}
HEADING_RE = re.compile(r"^(heading|nadpis|title|subtitle)", re.IGNORECASE)
CAPTION_RE = re.compile(r"^(caption|popisek)", re.IGNORECASE)
EXERCISE_MARKERS = (
    "exercise",
    "practice",
    "activity",
    "worksheet",
    "quiz",
    "match",
    "choose",
    "complete",
    "fill in",
    "write",
    "listen",
    "answer",
    "cvičení",
    "aktivita",
    "doplň",
    "vyber",
    "napiš",
    "poslech",
    "odpověz",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def detect_media(data: bytes, name: str) -> tuple[str, str]:
    suffix = Path(name).suffix.lower()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image", ".jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image", ".gif"
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image", ".webp"
    if data.startswith(b"ID3") or data[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}:
        return "audio", ".mp3"
    if data.startswith(b"OggS"):
        return "audio", ".ogg"
    if data.startswith(b"RIFF") and b"WAVE" in data[:16]:
        return "audio", ".wav"
    if len(data) > 12 and data[4:8] == b"ftyp":
        return ("audio" if suffix in {".m4a", ".aac"} else "video"), suffix or ".mp4"
    if data.lstrip().startswith(b"<svg") or b"<svg" in data[:500].lower():
        return "image", ".svg"
    if suffix in {".m4a", ".mp3", ".ogg", ".wav"}:
        return "audio", suffix
    if suffix in {".mp4", ".webm"}:
        return "video", suffix
    if suffix in {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}:
        return "image", suffix
    return "binary", suffix or ".bin"


def relationship_map(archive: zipfile.ZipFile) -> dict[str, str]:
    path = "word/_rels/document.xml.rels"
    if path not in archive.namelist():
        return {}
    root = ElementTree.fromstring(archive.read(path))
    return {
        node.attrib["Id"]: node.attrib["Target"]
        for node in root
        if node.attrib.get("Id") and node.attrib.get("Target")
    }


def media_member(target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join("word", target))


def paragraph_style(paragraph: ElementTree.Element) -> str:
    style = paragraph.find("./w:pPr/w:pStyle", NAMESPACES)
    return style.attrib.get(f"{{{NAMESPACES['w']}}}val", "") if style is not None else ""


def image_relationship_ids(paragraph: ElementTree.Element) -> list[str]:
    ids: list[str] = []
    for blip in paragraph.findall(".//a:blip", NAMESPACES):
        for attribute in ("embed", "link"):
            value = blip.attrib.get(f"{{{NAMESPACES['r']}}}{attribute}")
            if value and value not in ids:
                ids.append(value)
    for image in paragraph.findall(".//v:imagedata", NAMESPACES):
        value = image.attrib.get(f"{{{NAMESPACES['r']}}}id")
        if value and value not in ids:
            ids.append(value)
    return ids


def image_alt_text(paragraph: ElementTree.Element) -> list[str]:
    result: list[str] = []
    for node in paragraph.findall(".//wp:docPr", NAMESPACES):
        for key in ("descr", "title", "name"):
            value = node.attrib.get(key, "").strip()
            if value and value not in result and not value.lower().startswith("picture "):
                result.append(value)
    return result


def is_heading(style: str, text: str) -> bool:
    if HEADING_RE.search(style):
        return True
    stripped = text.strip()
    return bool(stripped and len(stripped) <= 90 and stripped.endswith(":") and not stripped.endswith("?:"))


def is_caption(style: str) -> bool:
    return bool(CAPTION_RE.search(style))


def classification(context: str, attribution_section: bool, has_text: bool) -> str:
    lowered = context.lower()
    if attribution_section or any(marker in lowered for marker in ATTRIBUTION_MARKERS):
        return "attribution-only"
    if any(marker in lowered for marker in EXERCISE_MARKERS):
        return "exercise-related"
    if has_text:
        return "instructional"
    return "decorative"


def paragraph_records(archive: zipfile.ZipFile, relationships: dict[str, str]) -> list[dict[str, Any]]:
    path = "word/document.xml"
    if path not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read(path))
    records: list[dict[str, Any]] = []
    current_heading = ""
    attribution_section = False

    for index, paragraph in enumerate(root.findall(".//w:p", NAMESPACES)):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", NAMESPACES)).strip()
        style = paragraph_style(paragraph)
        links: list[str] = []
        for hyperlink in paragraph.findall(".//w:hyperlink", NAMESPACES):
            rel_id = hyperlink.attrib.get(f"{{{NAMESPACES['r']}}}id")
            if rel_id and rel_id in relationships:
                links.append(relationships[rel_id])
        members = [
            media_member(relationships[rel_id])
            for rel_id in image_relationship_ids(paragraph)
            if rel_id in relationships and not relationships[rel_id].startswith(("http://", "https://"))
        ]
        alt_text = image_alt_text(paragraph)
        if is_heading(style, text):
            current_heading = text
        lowered = text.lower()
        if any(marker in lowered for marker in ATTRIBUTION_MARKERS):
            attribution_section = True
        if text or links or members:
            records.append(
                {
                    "index": index,
                    "style": style,
                    "text": text,
                    "heading": current_heading,
                    "links": links,
                    "mediaMembers": members,
                    "altText": alt_text,
                    "attributionSection": attribution_section,
                }
            )

    for position, record in enumerate(records):
        previous_text = next(
            (records[i]["text"] for i in range(position - 1, -1, -1) if records[i]["text"]),
            "",
        )
        next_text = next(
            (records[i]["text"] for i in range(position + 1, len(records)) if records[i]["text"]),
            "",
        )
        caption = record["text"] if record["mediaMembers"] and record["text"] else ""
        if not caption and position + 1 < len(records) and is_caption(records[position + 1]["style"]):
            caption = records[position + 1]["text"]
        context_parts = [record["heading"], previous_text, record["text"], next_text, *record["altText"]]
        context_text = "\n".join(dict.fromkeys(part for part in context_parts if part))
        record["previousText"] = previous_text
        record["nextText"] = next_text
        record["caption"] = caption
        record["contextText"] = context_text
        record["classification"] = classification(
            context_text,
            bool(record["attributionSection"]),
            bool(context_text),
        )
    return records


def attribution_from_paragraphs(paragraphs: list[dict[str, Any]]) -> dict[str, Any]:
    all_text = "\n".join(record["text"] for record in paragraphs)
    lowered = all_text.lower()
    positions = [lowered.find(marker) for marker in ATTRIBUTION_MARKERS if marker in lowered]
    start = min(positions) if positions else -1
    text = all_text[start:start + 16000] if start >= 0 else ""
    links = [
        {"url": link, "context": record["text"]}
        for record in paragraphs
        for link in record["links"]
        if start >= 0 or any(marker in record["text"].lower() for marker in ATTRIBUTION_MARKERS)
    ]
    return {"text": text, "links": links}


def media_appearances(member: str, paragraphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "paragraphIndex": record["index"],
            "style": record["style"],
            "heading": record["heading"],
            "text": record["text"],
            "previousText": record["previousText"],
            "nextText": record["nextText"],
            "caption": record["caption"],
            "altText": record["altText"],
            "contextText": record["contextText"],
            "classification": record["classification"],
        }
        for record in paragraphs
        if member in record["mediaMembers"]
    ]


def aggregate_classification(appearances: list[dict[str, Any]]) -> str:
    values = {item["classification"] for item in appearances}
    for preferred in ("exercise-related", "instructional", "decorative", "attribution-only"):
        if preferred in values:
            return preferred
    return "decorative"


def extract_docx(
    doc_id: str,
    source_page: str,
    export_url: str,
    final_url: str,
    data: bytes,
    destination: Path,
    repository_root: Path,
) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=True)
    docx_path = destination / f"{doc_id}.docx"
    docx_path.write_bytes(data)
    extracted: list[dict[str, Any]] = []

    with zipfile.ZipFile(docx_path) as archive:
        relationships = relationship_map(archive)
        paragraphs = paragraph_records(archive, relationships)
        for member in archive.namelist():
            if not member.startswith("word/media/") or member.endswith("/"):
                continue
            payload = archive.read(member)
            kind, extension = detect_media(payload, member)
            digest = _sha256(payload)
            output = destination / f"{digest[:16]}{extension}"
            output.write_bytes(payload)
            appearances = media_appearances(member, paragraphs)
            extracted.append(
                {
                    "documentId": doc_id,
                    "documentSource": source_page,
                    "docxMember": member,
                    "kind": kind,
                    "localPath": str(output.relative_to(repository_root)),
                    "bytes": len(payload),
                    "sha256": digest,
                    "sourceOrder": appearances[0]["paragraphIndex"] if appearances else None,
                    "classification": aggregate_classification(appearances),
                    "appearances": appearances,
                }
            )

    hyperlinks = [
        {"url": link, "context": record["text"]}
        for record in paragraphs
        for link in record["links"]
    ]
    return {
        "documentId": doc_id,
        "sourcePage": source_page,
        "exportUrl": export_url,
        "finalUrl": final_url,
        "bytes": len(data),
        "sha256": _sha256(data),
        "paragraphs": paragraphs,
        "hyperlinks": hyperlinks,
        "attribution": attribution_from_paragraphs(paragraphs),
        "extractedMedia": extracted,
    }
