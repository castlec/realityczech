"""Expand the checked-in Unit 1 human-recording manifests."""

from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path
from typing import Any

AUDIO_MANIFESTS = (
    "media/unit1-audio-vowels-soft.json",
    "media/unit1-audio-consonants.json",
    "media/unit1-audio-objects-people.json",
)


class Unit1AudioError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Unit1AudioError(f"missing audio manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise Unit1AudioError(f"invalid audio manifest {path}: {exc}") from exc


def _asset_id(filename: str) -> str:
    stem = Path(filename).stem.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return f"unit1-audio-{slug}"


def expand_unit1_audio(repository_root: Path) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    ids: set[str] = set()
    filenames: set[str] = set()

    for relative_path in AUDIO_MANIFESTS:
        manifest_path = repository_root / relative_path
        document = _read_json(manifest_path)
        if document.get("version") != 1:
            raise Unit1AudioError(f"unsupported version in {relative_path}")

        base_url = document.get("baseUrl")
        local_root = document.get("localRoot")
        attribution = document.get("attribution")
        if not all(isinstance(value, str) and value for value in (base_url, local_root, attribution)):
            raise Unit1AudioError(f"{relative_path} needs baseUrl, localRoot, and attribution")

        for item in document.get("items", []):
            filename = item.get("filename")
            label = item.get("label")
            lesson_ids = item.get("lessonIds")
            source_pages = item.get("sourcePages")
            if not isinstance(filename, str) or not filename.endswith(".mp3"):
                raise Unit1AudioError(f"invalid filename in {relative_path}: {filename!r}")
            if filename in filenames:
                raise Unit1AudioError(f"duplicate Unit 1 audio filename: {filename}")
            filenames.add(filename)
            if not isinstance(label, str) or not label:
                raise Unit1AudioError(f"{filename} has no Czech label")
            if not isinstance(lesson_ids, list) or not lesson_ids or not all(
                isinstance(value, str) and value for value in lesson_ids
            ):
                raise Unit1AudioError(f"{filename} has invalid lessonIds")
            if not isinstance(source_pages, list) or not source_pages or not all(
                isinstance(value, str) and value.startswith("https://") for value in source_pages
            ):
                raise Unit1AudioError(f"{filename} has invalid sourcePages")

            asset_id = _asset_id(filename)
            if asset_id in ids:
                raise Unit1AudioError(f"duplicate Unit 1 audio id: {asset_id}")
            ids.add(asset_id)

            speaker = item.get("speaker", "")
            speaker_credit = (
                f" Speaker identified in the published filename as {speaker}."
                if speaker
                else " The published filename does not identify the speaker."
            )
            encoded_filename = urllib.parse.quote(filename, safe="-_.")
            assets.append(
                {
                    "id": asset_id,
                    "kind": "audio",
                    "lessonId": lesson_ids[0],
                    "lessonIds": lesson_ids,
                    "label": label,
                    "speaker": speaker,
                    "fallbackText": label,
                    "delivery": "bundle",
                    "sourcePage": source_pages[0],
                    "sourcePages": source_pages,
                    "sourceUrl": urllib.parse.urljoin(base_url, encoded_filename),
                    "localPath": f"{local_root.rstrip('/')}/{filename}",
                    "expectedContentTypes": ["audio/", "application/octet-stream"],
                    "minBytes": 500,
                    "attribution": attribution + speaker_credit,
                }
            )

    if len(assets) != 90:
        raise Unit1AudioError(f"expected 90 discovered Unit 1 recordings, found {len(assets)}")
    return assets
