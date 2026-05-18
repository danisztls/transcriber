"""HTML extraction and Markdown conversion."""

import os
import re

from bs4 import BeautifulSoup, Comment
from markdownify import MarkdownConverter

from .config import Config
from .fetcher import get_response_data
from .writer import save_file


async def get_html(url: str, path: list[str], cfg: Config) -> BeautifulSoup:
    """Fetch URL and return a best-effort content node (article/main/body)."""
    try:
        html = BeautifulSoup(await get_response_data(url, cfg), "html.parser")
    except Exception as e:
        cfg.err.print(f"[red]ERROR:[/red] {e}")
        raise RuntimeError("Failed to Get HTML") from e

    if cfg.debug_mode:
        save_file(
            os.path.join(path[0], path[1] + ".raw.html"),
            html.prettify(),
            cfg,
            overwrite=True,
        )

    content = None
    for tag in ("article", "main"):
        nodes = html.find_all(tag)
        if not nodes:
            continue
        content = (
            nodes[0] if len(nodes) == 1 else max(nodes, key=lambda n: len(n.get_text(strip=True)))
        )
        break

    if content is None:
        content = html.find("body")
        if content is not None:
            for t in content.find_all(("header", "footer")):
                t.decompose()

    if content is None:
        return html

    if cfg.debug_mode:
        save_file(
            os.path.join(path[0], path[1] + ".content.html"),
            content.prettify(),
            cfg,
            overwrite=True,
        )

    return content


def filter_html(html: BeautifulSoup, path: list[str], cfg: Config) -> BeautifulSoup:
    """Filter HTML to remove non-content."""
    removable_tags = ("style", "script", "iframe", "nav", "svg", "button")
    for el in html.find_all(removable_tags):
        el.decompose()

    for el in reversed(list(html.find_all(True))):
        if el.name is None:
            continue
        if el.name in ("img", "video", "audio"):
            continue
        if not el.get_text(strip=True) and not el.find(("img", "video", "audio")):
            el.decompose()

    for comment in html.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    if cfg.debug_mode:
        save_file(
            os.path.join(path[0], path[1] + ".filtered.html"),
            html.prettify(),
            cfg,
            overwrite=True,
        )

    return html


def parse_html(html: BeautifulSoup) -> str:
    """Parse HTML into Markdown."""
    options = {"heading_style": "ATX", "newline_style": "backslash"}
    return MarkdownConverter(**options).convert_soup(html)


def filter_mkdown(mkdown: str) -> str:
    """Filter Markdown to remove undesirables."""
    mkdown = mkdown.strip()
    mkdown = re.sub(r"\n{3,}", "\n\n", mkdown)
    mkdown = re.sub(r"^[ \t]+|[ \t]+$", "", mkdown, flags=re.MULTILINE)
    mkdown = re.sub(r"^>\s*\n", "", mkdown, flags=re.MULTILINE)

    google_pattern = re.compile(r"\(https://www.google.com/url\?q=(https?://.*?)&.*\)")
    mkdown = re.sub(google_pattern, r"(\1)", mkdown)
    return mkdown
