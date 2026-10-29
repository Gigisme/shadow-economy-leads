"""Polite HTTP downloads with retries, payload validation and a per-run manifest for traceability."""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shadow_leads.config import RAW_DIR, USER_AGENT

log = logging.getLogger(__name__)

MANIFEST = "manifest.json"
MIN_BYTES = 1_000_000  # every file we fetch is tens of MB; anything tiny is an error page


@dataclass(frozen=True)
class FileSpec:
    url: str
    name: str
    magic: bytes  # the payload must start with these bytes (zip signature, CSV header, ...)
    optional: bool = False  # a 404 is a warning, not a failure


def session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    retry = Retry(total=4, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def _sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            sha.update(chunk)
    return sha.hexdigest()


def download(s: requests.Session, spec: FileSpec, dest: Path, *, timeout: int = 300) -> dict:
    """Fetch `spec` to `dest` and return a manifest entry.

    The payload is validated before it is allowed to replace anything. An existing file is
    only overwritten when its SHA-256 differs from the new download.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    sha = hashlib.sha256()
    size = 0
    started = time.monotonic()
    try:
        with s.get(spec.url, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            content_type = r.headers.get("Content-Type", "")
            expected = r.headers.get("Content-Length")
            compressed = "Content-Encoding" in r.headers
            first = b""
            with tmp.open("wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    if not first:
                        first = chunk[: len(spec.magic)]
                    f.write(chunk)
                    sha.update(chunk)
                    size += len(chunk)

        # Registrų centras answers unknown files with an HTML page and status 200.
        if first != spec.magic:
            raise ValueError(f"{spec.url}: unexpected payload start {first!r} (content-type {content_type!r})")
        if size < MIN_BYTES:
            raise ValueError(f"{spec.url}: only {size} bytes, expected at least {MIN_BYTES}")
        if expected and not compressed and int(expected) != size:
            raise ValueError(f"{spec.url}: truncated, got {size} of {expected} bytes")

        digest = sha.hexdigest()
        if dest.exists() and _sha256(dest) == digest:
            status = "unchanged"
        else:
            status = "updated" if dest.exists() else "new"
            tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)

    log.info("%s %s (%.1f MB, %.1fs)", status, dest, size / 1e6, time.monotonic() - started)
    return {
        "url": spec.url,
        "file": dest.name,
        "status": status,
        "bytes": size,
        "sha256": digest,
        "content_type": content_type,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def fetch_files(source: str, run_id: str, specs: list[FileSpec]) -> Path:
    """Download all `specs` into data/raw/<source>/<run_id>/ and write the manifest.

    The manifest is written even if a download fails, with `complete: false`, so a partial
    run is always described.
    """
    run_dir = RAW_DIR / source / run_id
    s = session()
    entries: list[dict] = []
    complete = False
    try:
        for spec in specs:
            try:
                entries.append(download(s, spec, run_dir / spec.name))
            except requests.HTTPError as e:
                if spec.optional and e.response is not None and e.response.status_code == 404:
                    log.warning("optional file not available yet: %s", spec.url)
                    continue
                raise
        complete = True
    finally:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / MANIFEST).write_text(
            json.dumps({"source": source, "run_id": run_id, "complete": complete, "files": entries},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return run_dir
