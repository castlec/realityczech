from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from .web import ATTRIBUTION_MARKERS


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


def paragraph_records(archive: zipfile.ZipFile, relationships: dict[str, str]) -> list[dict[str, Any]]:
    path = "word/document.xml"
    if path not in archive.namelist():
        return []
    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    root = ElementTree.fromstring(archive.read(path))
    records: list[dict[str, Any]] = []
    for paragraph in root.findall(".//w:p", ns):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns)).strip()
        links: list[str] = []
        for hyperlink in paragraph.findall(".//w:hyperlink", ns):
            rel_id = hyperlink.attrib.get(f"{{{ns['r']}}}id")
            if rel_id and rel_id in relationships:
                links.append(relationships[rel_id])
        if text or links:
            records.append({"text": text, "links": links})
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
            extracted.append(
                {
                    "documentId": doc_id,
                    "documentSource": source_page,
                    "docxMember": member,
                    "kind": kind,
                    "localPath": str(output.relative_to(repository_root)),
                    "bytes": len(payload),
                    "sha256": digest,
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
