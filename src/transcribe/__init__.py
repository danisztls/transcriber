#!/usr/bin/env python
"""
Scrape Web content into markdown
"""

__author__ = "Daniel Souza <me@posix.dev.br>"
__license__ = "GPLv3"

import argparse
import os
import pathlib
import re
import time
from typing import Any, Optional
from urllib.parse import unquote, urljoin, urlparse

import urllib3
from bs4 import BeautifulSoup, Comment
from markdownify import MarkdownConverter
from rich import print
import yaml

output_path = str(pathlib.Path().absolute() / "output")
_http = urllib3.PoolManager()

# Runtime flags (set in main())
CLI_MODE = False
VERBOSE_MODE = False
DEBUG_MODE = False


def mkdir(path: str) -> None:
    """Traverse a path and create nonexistent dirs."""
    if not path:
        return
    os.makedirs(path, exist_ok=True)


def get_response_data(
    url: str,
    *,
    timeout: urllib3.Timeout = urllib3.Timeout(connect=5.0, read=30.0),
    retries: int = 0,
) -> bytes:
    """Make a GET request and return the response body as bytes."""
    user_agents = [
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
        "Mozilla/5.0 (compatible; DuckDuckBot/1.0; +http://duckduckgo.com/duckduckbot.html)",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    if not isinstance(url, str) or not url.strip():
        raise ValueError("URL must be a non-empty string")

    url = url.strip()
    if not re.match(r"^https?://", url):
        raise ValueError("URL must start with http:// or https://")

    last_error: Optional[BaseException] = None
    last_status: Optional[int] = None
    retryable_statuses = {401, 403, 429, 503}

    for ua in user_agents:
        headers = urllib3.make_headers(user_agent=ua)
        try:
            response = _http.request(
                "GET",
                url,
                headers=headers,
                redirect=True,
                timeout=timeout,
                retries=retries,
            )

            # Avoid noisy/always-on debug output. Use DEBUG_MODE only.
            if DEBUG_MODE:
                print(f"[gray]{url}[/gray] -> {response.status} ({ua})")

            last_status = getattr(response, "status", None)

            if last_status == 200:
                return response.data

            if last_status not in retryable_statuses:
                break
        except Exception as e:
            last_error = e
            last_status = None

    if last_status is not None:
        raise ValueError(f"HTTP request failed for URL: {url}. Status: {last_status}")
    raise ValueError(f"HTTP request failed for URL: {url}. {last_error}")


def get_html(url: str, path) -> BeautifulSoup:
    """Fetch URL and return a best-effort content node (article/main/body)."""
    try:
        html = BeautifulSoup(get_response_data(url), "html.parser")
    except Exception as e:
        print(f"[red]ERROR:[/red] {e}")
        raise RuntimeError("Failed to Get HTML") from e

    if DEBUG_MODE:
        save_file(os.path.join(path[0], path[1] + ".raw.html"), html.prettify(), overwrite=True)

    for tag in ("article", "main", "body"):
        content = html.find(tag)
        if not content:
            continue

        if tag == "body":
            for t in content.find_all(("header", "footer")):
                t.decompose()

        if DEBUG_MODE:
            save_file(
                os.path.join(path[0], path[1] + ".content.html"),
                content.prettify(),
                overwrite=True,
            )

        return content

    return html


def filter_html(html: BeautifulSoup, path) -> BeautifulSoup:
    """Filter HTML to remove non-content."""
    removable_tags = ("style", "script", "iframe", "nav", "svg", "button")
    for el in html.find_all(removable_tags):
        el.decompose()

    for el in list(html.find_all(True)):
        if el.name in ("img", "video", "audio"):
            continue

        if not el.get_text(strip=True) and not el.find(("img", "video", "audio")):
            el.decompose()

    for comment in html.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    if DEBUG_MODE:
        save_file(
            os.path.join(path[0], path[1] + ".filtered.html"),
            html.prettify(),
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


def _safe_segment(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s).strip("_")
    return s or "unknown"


def gen_path(url: str):
    """Generate file path from URL preserving URL subpath."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https", "file"):
        raise ValueError("Invalid URL")

    if parsed.scheme in ("http", "https"):
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
        dir_path = os.path.join(output_path, base, *subdirs, "")
        mkdir(dir_path)
        return [dir_path, file_seg]

    local_path = unquote(parsed.path or "")
    local_path = os.path.normpath(local_path)

    parent_dir = os.path.basename(os.path.dirname(local_path)) or "unknown"
    base = os.path.join("local", _safe_segment(parent_dir))

    filename = os.path.basename(local_path) or "index"
    if "." in filename:
        file_seg = _safe_segment(filename.rsplit(".", 1)[0]) or "index"
    else:
        file_seg = _safe_segment(filename) or "index"

    dir_path = os.path.join(output_path, base, "")
    mkdir(dir_path)
    return [dir_path, file_seg]


def save_file(path: str, data: Any, overwrite: bool = False) -> None:
    """Save data to disk."""
    if os.path.exists(path) and not overwrite:
        print(f"[gray]{path}[/gray] [yellow]already exists![/yellow]")
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


def get_assets(dir_path: str, base_url: str, html: BeautifulSoup) -> BeautifulSoup:
    """Download linked assets and rewrite their URLs on BeautifulSoup object with their output paths."""
    urls: list[str] = []
    for tag in ("img", "video", "audio"):
        for el in html.find_all(tag):
            src = el.get("src")
            if src:
                urls.append(src)

    seen: set[str] = set()
    for raw in urls:
        if raw in seen:
            continue
        seen.add(raw)

        # Resolve relative URLs against the page URL
        resolved = urljoin(base_url, raw)
        parsed = urlparse(resolved)
        if parsed.scheme not in ("http", "https"):
            continue

        if not CLI_MODE:
            print(f"\n[gray]{resolved}[/gray]")

        try:
            data = get_response_data(resolved)
        except Exception:
            continue

        filename = _safe_segment(os.path.basename(parsed.path) or "asset")
        save_file(os.path.join(dir_path, filename), data, overwrite=True)

        # Rewrite references (match original raw AND resolved variants conservatively)
        for tag in ("img", "video", "audio"):
            for el in html.find_all(tag):
                src = el.get("src")
                if src == raw:
                    el["src"] = f"./{filename}"

    return html


class chronometer:
    """Measure execution time of function."""

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()

            if not CLI_MODE:
                print("[green]%s seconds[/green]" % str(round(end - start, 2)))

            return result

        return wrapper


@chronometer()
def scrape(url: str) -> None:
    """Scrape URL and save Markdown content to disk."""
    if not CLI_MODE:
        print(f"\n[purple]{url}[/purple]")

    path = gen_path(url)

    try:
        html = get_html(url, path)
    except Exception:
        return

    html_filtered = filter_html(html, path)
    html_rewritten = get_assets(path[0], url, html_filtered)

    mkdown = parse_html(html_rewritten)

    if DEBUG_MODE:
        save_file(os.path.join(path[0], path[1] + ".raw.md"), mkdown, overwrite=True)

    mkdown_filtered = filter_mkdown(mkdown)

    if DEBUG_MODE or not CLI_MODE:
        save_file(os.path.join(path[0], path[1] + ".md"), mkdown_filtered, overwrite=True)

    if VERBOSE_MODE or CLI_MODE:
        print(mkdown_filtered)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target", dest="target", help="URL to scrap")
    parser.add_argument("-l", "--list", dest="list", help="YAML list of URLs to scrap")
    parser.add_argument(
        "-c",
        "--cli-mode",
        dest="cli",
        default=False,
        help="CLI mode (only print content to STDOUT)",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        default=False,
        help="verbose mode (print content to STDOUT)",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        default=False,
        help="debug mode",
        action="store_true",
    )
    return parser


def main(argv=None) -> None:
    global CLI_MODE, VERBOSE_MODE, DEBUG_MODE

    parser = _build_parser()
    args = parser.parse_args(argv)

    CLI_MODE = args.cli
    VERBOSE_MODE = args.verbose
    DEBUG_MODE = args.debug

    if not CLI_MODE:
        print(":spider: scraping...")

    if args.target:
        scrape(args.target)

    if args.list:
        with open(args.list, "r", encoding="utf-8") as file:
            urls = yaml.safe_load(file) or []

        if not isinstance(urls, list):
            raise ValueError("YAML list file must contain a top-level list of URLs")

        for url in urls:
            if isinstance(url, str) and url.strip():
                scrape(url.strip())

    if not args.target and not args.list:
        print("[red]No URL to scrape. Please input an URL or Yaml list.[/red]")


if __name__ == "__main__":
    main()
