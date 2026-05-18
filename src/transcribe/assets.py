"""Asset extraction, download, and URL rewriting."""

import hashlib
import os
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from . import _state
from .fetcher import get_response_data
from .writer import _safe_segment, save_file


def _pick_srcset(srcset: str) -> str | None:
    """Pick the largest candidate URL from a srcset attribute."""
    best_url: str | None = None
    best_score = -1.0
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        url = bits[0]
        score = 1.0
        if len(bits) > 1:
            descriptor = bits[1]
            try:
                if descriptor.endswith("w"):
                    score = float(descriptor[:-1])
                elif descriptor.endswith("x"):
                    score = float(descriptor[:-1]) * 1000
            except ValueError:
                pass
        if score > best_score:
            best_score = score
            best_url = url
    return best_url


def _best_asset_url(el) -> str | None:
    """Pick the best asset URL from an element: src, data-src*, then srcset."""
    for attr in ("src", "data-src", "data-original"):
        val = el.get(attr)
        if val:
            return val
    srcset = el.get("srcset")
    if srcset:
        return _pick_srcset(srcset)
    return None


def _asset_filename(parsed_url) -> str:
    """Build a collision-resistant filename from a parsed asset URL."""
    name = _safe_segment(os.path.basename(parsed_url.path) or "asset")
    digest = hashlib.sha1(parsed_url.path.encode("utf-8")).hexdigest()[:8]
    if "." in name:
        stem, ext = name.rsplit(".", 1)
        return f"{stem}-{digest}.{ext}"
    return f"{name}-{digest}"


def get_assets(dir_path: str, base_url: str, html: BeautifulSoup) -> BeautifulSoup:
    """Download linked assets and rewrite element URLs to local paths."""
    downloaded: dict[str, str] = {}
    failed: set[str] = set()

    def _download(resolved: str) -> str | None:
        if resolved in downloaded:
            return downloaded[resolved]
        if resolved in failed:
            return None
        parsed = urlparse(resolved)
        if parsed.scheme not in ("http", "https"):
            failed.add(resolved)
            return None
        if not _state.CLI_MODE:
            _state.err.print(f"\n[gray]{resolved}[/gray]")
        try:
            data = get_response_data(resolved)
        except Exception:
            failed.add(resolved)
            return None
        filename = _asset_filename(parsed)
        save_file(os.path.join(dir_path, filename), data, overwrite=True)
        downloaded[resolved] = filename
        return filename

    def _rewrite(el, local: str) -> None:
        el["src"] = f"./{local}"
        for attr in ("srcset", "data-src", "data-original"):
            if attr in el.attrs:
                del el.attrs[attr]

    for tag_name in ("img", "video", "audio"):
        for el in html.find_all(tag_name):
            raw = _best_asset_url(el)
            if not raw:
                continue
            local = _download(urljoin(base_url, raw))
            if local:
                _rewrite(el, local)

    for source in html.find_all("source"):
        raw = source.get("src")
        if not raw:
            srcset = source.get("srcset")
            if srcset:
                raw = _pick_srcset(srcset)
        if not raw:
            continue
        local = _download(urljoin(base_url, raw))
        if local:
            _rewrite(source, local)

    return html
