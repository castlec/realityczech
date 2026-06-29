#!/usr/bin/env python3
"""Download, validate, discover, and package Reality Czech media.

Declared direct media is written into app/src/main/assets/media so Gradle packages
it in the APK. Streaming media is availability-checked but is not downloaded.
The Unit 1 source graph and public document exports are also audited; embedded
media is extracted into a vendor archive and unresolved attribution causes CI to
fail.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from media_discovery.part2 import finalize as finalize_unit1_discovery
from media_discovery.unit1 import collect as collect_unit1_media
from unit1_audio import Unit1AudioError, expand_unit1_audio

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "media/sources.json"
REPORT_PATH = ROOT / "media/sync-report.json"
UNIT1_OUTPUT_ROOT = ROOT / "media/discovery/unit1"
UNIT1_REPORT_PATH = ROOT / "media/discovery/unit1-report.json"
UNIT1_UNRESOLVED_PATH = ROOT / "media/discovery/unit1-unresolved.json"
UNIT1_VENDOR_ARCHIVE = ROOT / "media/vendor/unit1-document-media.zip"
USER_AGENT = "RealityCzechAndroidMediaSync/1.0 (+https://github.com/castlec/realityczech)"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
CATALOG_FIELDS = (
    "id",
    "kind",
    "lessonId",
    "lessonIds",
    "label",
    "sourcePage",
    "sourcePages",
    "sourceUrl",
    "attribution",
    "speaker",
    "fallbackText",
)


class MediaError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MediaError(f"missing manifest: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise MediaError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc


def expand_manifest(document: dict[str, Any]) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []

    for group in document.get("imageGroups", []):
        required = (
            "id",
            "lessonId",
            "sourcePage",
            "urlTemplate",
            "localPathTemplate",
            "items",
        )
        for key in required:
            if not group.get(key):
                raise MediaError(f"image group is missing {key}: {group.get('id')!r}")

        for item in group["items"]:
            try:
                number = item["number"]
                extension = item["extension"]
                label = item["label"]
            except KeyError as exc:
                raise MediaError(f"incomplete image item in group {group['id']}") from exc

            values = {"number": number, "extension": extension}
            expanded.append(
                {
                    "id": f"{group['id']}-{number}",
                    "kind": group.get("kind", "image"),
                    "lessonId": group["lessonId"],
                    "lessonIds": [group["lessonId"]],
                    "label": label,
                    "delivery": group.get("delivery", "bundle"),
                    "sourcePage": group["sourcePage"],
                    "sourcePages": [group["sourcePage"]],
                    "sourceUrl": group["urlTemplate"].format(**values),
                    "localPath": group["localPathTemplate"].format(**values),
                    "expectedContentTypes": group.get("expectedContentTypes", ["image/"]),
                    "minBytes": group.get("minBytes", 1),
                    "attribution": group.get(
                        "attribution",
                        "Reality Czech; CC BY-SA 3.0",
                    ),
                }
            )

    expanded.extend(document.get("assets", []))
    try:
        expanded.extend(expand_unit1_audio(ROOT))
    except Unit1AudioError as exc:
        raise MediaError(str(exc)) from exc
    return expanded


def validate_manifest(document: dict[str, Any], assets: list[dict[str, Any]]) -> Path:
    if document.get("version") != 1:
        raise MediaError("unsupported media manifest version")

    root_text = document.get("generatedAssetsRoot")
    if not isinstance(root_text, str) or not root_text:
        raise MediaError("generatedAssetsRoot is required")

    output_root = (ROOT / root_text).resolve()
    if ROOT.resolve() not in output_root.parents:
        raise MediaError("generatedAssetsRoot must remain inside the repository")

    ids: set[str] = set()
    local_paths: set[str] = set()
    for asset in assets:
        asset_id = asset.get("id")
        if not isinstance(asset_id, str) or not asset_id:
            raise MediaError("every media item needs an id")
        if asset_id in ids:
            raise MediaError(f"duplicate media id: {asset_id}")
        ids.add(asset_id)

        if asset.get("delivery") not in {"bundle", "stream"}:
            raise MediaError(f"unsupported delivery for {asset_id}: {asset.get('delivery')!r}")
        for field in (
            "kind",
            "lessonId",
            "label",
            "sourcePage",
            "sourceUrl",
            "attribution",
        ):
            if not asset.get(field):
                raise MediaError(f"{asset_id} is missing {field}")

        lesson_ids = asset.get("lessonIds", [asset["lessonId"]])
        if not isinstance(lesson_ids, list) or not lesson_ids or not all(
            isinstance(value, str) and value for value in lesson_ids
        ):
            raise MediaError(f"{asset_id} has invalid lessonIds")

        if asset["delivery"] == "bundle":
            local_path = asset.get("localPath")
            if not isinstance(local_path, str) or not local_path:
                raise MediaError(f"bundled media {asset_id} needs localPath")
            candidate = (output_root / local_path).resolve()
            if output_root not in candidate.parents:
                raise MediaError(f"localPath escapes media root: {local_path}")
            if local_path in local_paths:
                raise MediaError(f"duplicate localPath: {local_path}")
            local_paths.add(local_path)
        elif not asset.get("checkUrl"):
            raise MediaError(f"streaming media {asset_id} needs checkUrl")

    return output_root


def request_bytes(url: str, attempts: int = 3) -> tuple[bytes, str, str]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "*/*",
                },
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                status = getattr(response, "status", 200)
                if status < 200 or status >= 300:
                    raise MediaError(f"HTTP {status} for {url}")
                content_type = response.headers.get_content_type().lower()
                final_url = response.geturl()
                data = response.read(MAX_DOWNLOAD_BYTES + 1)
                if len(data) > MAX_DOWNLOAD_BYTES:
                    raise MediaError(f"download exceeds {MAX_DOWNLOAD_BYTES} bytes: {url}")
                return data, content_type, final_url
        except (urllib.error.URLError, TimeoutError, MediaError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt * 2)
    raise MediaError(f"failed to fetch {url}: {last_error}")


def validate_payload(asset: dict[str, Any], data: bytes, content_type: str) -> None:
    asset_id = asset["id"]
    minimum = int(asset.get("minBytes", 1))
    if len(data) < minimum:
        raise MediaError(f"{asset_id} returned only {len(data)} bytes; expected at least {minimum}")

    expected = asset.get("expectedContentTypes", [])
    if expected and not any(content_type.startswith(prefix) for prefix in expected):
        raise MediaError(
            f"{asset_id} returned content type {content_type!r}; expected one of {expected}"
        )

    kind = asset["kind"]
    if kind == "image":
        is_png = data.startswith(b"\x89PNG\r\n\x1a\n")
        is_jpeg = data.startswith(b"\xff\xd8\xff")
        is_gif = data.startswith((b"GIF87a", b"GIF89a"))
        is_webp = len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
        if not any((is_png, is_jpeg, is_gif, is_webp)):
            raise MediaError(f"{asset_id} did not return a recognized image file")
    elif kind == "audio":
        html_prefix = data[:256].lower()
        if b"<html" in html_prefix or b"<!doctype html" in html_prefix:
            raise MediaError(f"{asset_id} returned HTML instead of audio")
        is_mp3 = data.startswith(b"ID3") or data[:2] in {
            b"\xff\xfb",
            b"\xff\xf3",
            b"\xff\xf2",
        }
        if asset.get("localPath", "").lower().endswith(".mp3") and not is_mp3:
            raise MediaError(f"{asset_id} did not return a recognized MP3 file")

    expected_hash = asset.get("sha256")
    if expected_hash:
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != expected_hash:
            raise MediaError(
                f"{asset_id} SHA-256 changed: expected {expected_hash}, got {actual_hash}"
            )


def catalog_metadata(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        key: asset[key]
        for key in CATALOG_FIELDS
        if key in asset and asset[key] not in (None, "", [])
    }


def sync_asset(asset: dict[str, Any], output_root: Path) -> dict[str, Any]:
    metadata = catalog_metadata(asset)
    if asset["delivery"] == "stream":
        data, content_type, final_url = request_bytes(asset["checkUrl"])
        if not data:
            raise MediaError(f"stream check returned no data: {asset['id']}")
        return {
            **metadata,
            "delivery": "stream",
            "checkUrl": asset["checkUrl"],
            "contentType": content_type,
            "bytes": len(data),
            "finalUrl": final_url,
        }

    download_url = asset.get("downloadUrl") or asset["sourceUrl"]
    data, content_type, final_url = request_bytes(download_url)
    validate_payload(asset, data, content_type)

    destination = output_root / asset["localPath"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()

    return {
        **metadata,
        "delivery": "bundle",
        "downloadUrl": download_url,
        "localPath": asset["localPath"],
        "assetUri": f"file:///android_asset/media/{asset['localPath']}",
        "contentType": content_type,
        "bytes": len(data),
        "sha256": digest,
        "finalUrl": final_url,
    }


def write_report(status: str, results: list[dict[str, Any]], errors: list[str]) -> None:
    report = {
        "status": status,
        "assetCount": len(results),
        "bundledCount": sum(item.get("delivery") == "bundle" for item in results),
        "streamCount": sum(item.get("delivery") == "stream" for item in results),
        "results": sorted(results, key=lambda item: item["id"]),
        "errors": errors,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_unit1_discovery(workers: int) -> dict[str, Any]:
    if UNIT1_OUTPUT_ROOT.exists():
        shutil.rmtree(UNIT1_OUTPUT_ROOT)
    UNIT1_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    state = collect_unit1_media(ROOT, UNIT1_OUTPUT_ROOT, workers)
    return finalize_unit1_discovery(
        state,
        ROOT,
        UNIT1_VENDOR_ARCHIVE,
        UNIT1_REPORT_PATH,
        UNIT1_UNRESOLVED_PATH,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--no-clean", action="store_true")
    parser.add_argument("--skip-unit1-discovery", action="store_true")
    args = parser.parse_args()

    results: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        document = read_json(MANIFEST_PATH)
        assets = expand_manifest(document)
        output_root = validate_manifest(document, assets)

        if not args.no_clean and output_root.exists():
            shutil.rmtree(output_root)
        output_root.mkdir(parents=True, exist_ok=True)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {executor.submit(sync_asset, asset, output_root): asset for asset in assets}
            for future in concurrent.futures.as_completed(futures):
                asset = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(
                        f"ok {asset['id']}: {result.get('bytes', 0)} bytes "
                        f"({result['delivery']})"
                    )
                except Exception as exc:  # noqa: BLE001 - aggregate all failures for CI
                    message = f"{asset['id']}: {exc}"
                    errors.append(message)
                    print(f"ERROR {message}", file=sys.stderr)

        if errors:
            write_report("failed", results, errors)
            raise MediaError(f"{len(errors)} media item(s) failed")

        catalog = {
            "version": document["version"],
            "license": document.get("license", ""),
            "assets": sorted(results, key=lambda item: item["id"]),
        }
        (output_root / "catalog.json").write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        missing = [
            result["localPath"]
            for result in results
            if result["delivery"] == "bundle"
            and not (output_root / result["localPath"]).is_file()
        ]
        if missing:
            raise MediaError(f"generated media files are missing: {missing}")

        if not args.skip_unit1_discovery:
            unit1_report = run_unit1_discovery(args.workers)
            unresolved = unit1_report.get("unresolved", [])
            if unresolved:
                raise MediaError(
                    f"Unit 1 media discovery has {len(unresolved)} unresolved item(s); "
                    f"see {UNIT1_UNRESOLVED_PATH.relative_to(ROOT)}"
                )

        write_report("ok", results, [])
        print(
            f"synchronized {len(results)} media item(s): "
            f"{sum(item['delivery'] == 'bundle' for item in results)} bundled, "
            f"{sum(item['delivery'] == 'stream' for item in results)} streaming"
        )
    except MediaError as exc:
        if not REPORT_PATH.exists():
            write_report("failed", results, [str(exc)])
        else:
            write_report("failed", results, [str(exc), *errors])
        print(f"media sync failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
