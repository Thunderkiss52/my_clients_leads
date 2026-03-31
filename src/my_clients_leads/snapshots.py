from __future__ import annotations

import hashlib
import re
from pathlib import Path


def slugify(value: str, *, fallback: str = "page", limit: int = 80) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    if not text:
        text = fallback
    return text[:limit].strip("-") or fallback


def snapshot_path(snapshot_dir: str | None, *, bucket: str, label: str, suffix: str = ".html") -> Path | None:
    if not snapshot_dir:
        return None
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:12]
    filename = f"{slugify(label)}-{digest}{suffix}"
    path = Path(snapshot_dir) / bucket / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_snapshot(path: Path | None, content: str | bytes) -> None:
    if path is None:
        return
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
