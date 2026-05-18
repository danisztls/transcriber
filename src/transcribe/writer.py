"""File path generation and disk writes."""

import os
import re
from typing import Any
from urllib.parse import unquote, urlparse

from .config import Config


def _safe_segment(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s).strip("_")
    return s or "unknown"


def gen_path(url: str, cfg: Config) -> list[str]:
    """Generate file path from URL preserving URL subpath."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Invalid URL")

    base = _safe_segment(parsed.netloc or "unknown")
    url_path = unquote(parsed.path or "/")

    segments = [seg for seg in url_path.split("/") if seg]
    if segments:
        last = segments[-1]
        if "." in last:
            file_seg = _safe_segment(last.rsplit(".", 1)[0]) or "index"
            subdirs = segments[:-1]
        else:
            file_seg = "index"
            subdirs = segments
    else:
        file_seg = "index"
        subdirs = []

    subdirs = [_safe_segment(s) for s in subdirs if _safe_segment(s)]
    dir_path = os.path.join(cfg.output_dir, base, *subdirs, "")
    return [dir_path, file_seg]


def save_file(path: str, data: Any, cfg: Config, *, overwrite: bool = False) -> None:
    """Save data to disk."""
    if os.path.exists(path) and not overwrite:
        cfg.err.print(f"[gray]{path}[/gray] [yellow]already exists![/yellow]")
        return

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    if isinstance(data, (bytes, bytearray)):
        with open(path, "wb") as f:
            f.write(data)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(data))
