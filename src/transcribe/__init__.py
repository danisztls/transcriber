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
from urllib.parse import urlparse, unquote

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

    last_error = None
    last_status = None
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

    def _error_html(error: Exception) -> BeautifulSoup:
        _data = "<strong>No page for you.</strong>"
        _data += f"\n<p>{error}</p>"
        return BeautifulSoup(_data, "html.parser")

    try:
        html = BeautifulSoup(get_response_data(url), "html.parser")
    except Exception as error:
        print(f"[red]ERROR:[/red] {error}")
        return _error_html(error)

    if DEBUG_MODE:
        save_file(path[0] + path[1] + ".raw.html", html.prettify(), overwrite=True)

    for tag in ("article", "main", "body"):
        content = html.find(tag)
        if not content:
            continue

        if tag == "body":
            for t in content.find_all(("header", "footer")):
                t.decompose()

        if DEBUG_MODE:
            save_file(
                path[0] + path[1] + ".content.html", content.prettify(), overwrite=True
            )

        return content

    return html


def filter_html(html: BeautifulSoup, path) -> BeautifulSoup:
    """Filter HTML to remove non-content."""
    removable_tags = ["style", "script", "iframe", "nav", "svg", "button"]
    for tag_name in removable_tags:
        for tag in html.find_all(tag_name):
            tag.decompose()

    for tag in html.find_all(True):
        if "style" in tag.attrs:
            del tag["style"]

        if tag.name in ("img", "video", "audio"):
            continue

        if not tag.get_text(strip=True) and not tag.find_all(("img", "video", "audio")):
            tag.decompose()

    for comment in html.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    if DEBUG_MODE:
        save_file(
            path[0] + path[1] + ".filtered.html", html.prettify(), overwrite=True
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
    google_pattern = re.compile(
        r"\(https://www.google.com/url\?q=(https?://.*?)&.*\)"
    )
    mkdown = re.sub(google_pattern, r"(\1)", mkdown)
    return mkdown


def _safe_segment(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s).strip("_")
    return s or "unknown"


def gen_path(url: str):
    """Generate file path from URL."""
    m = re.match(r"^(https?|file)://(.*)$", url)
    if not m:
        raise ValueError("Invalid URL")

    scheme = m.group(1)
    remainder = m.group(2)
    tree = remainder.split("/")

    if scheme in ("http", "https"):
        if tree and tree[-1] == "":
            tree.pop()
        base = _safe_segment(tree[0] if tree else "unknown")
    else:
        parent = tree[-2] if len(tree) >= 2 else "unknown"
        base = "local/" + _safe_segment(parent)

    path = output_path + "/" + base + "/"
    mkdir(path)

    last = tree[-1] if tree else "index"
    last = last.split("?", 1)[0].split("#", 1)[0]
    last = unquote(last)

    file_stem = re.sub(r"\..*", "", last) or "index"
    file_stem = _safe_segment(file_stem)

    return [path, file_stem]


def save_file(path: str, data, overwrite: bool = False) -> None:
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
            f.write(data)

def get_assets(dir_path: str, html: BeautifulSoup) -> str:
    """Download linked assets and rewrite their URLs on BeautifulSoup object with their output paths."""
    urls: list[str] = []
    for tag in ("img", "video", "audio"):
        for el in html.find_all(tag):
            src = el.get("src")
            urls.append(src)

    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)

        if not CLI_MODE:
            print(f"\n:paperclip: [gray]{url}[/gray]")

        try:
            data = get_response_data(url)
        except Exception:
            continue

        parsedPath = urlparse(url).path
        filename = os.path.basename(parsedPath)
        filename = unquote(filename)
        filename = _safe_segment(filename)

        save_file(os.path.join(dir_path, filename), data, overwrite=True)

        for tag in ("img", "video", "audio"):
            for el in html.find_all(tag):
                src = el.get("src")
                if src == url:
                    el["src"] = f"./{filename}"

    return str(html)


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
        print(f"\n:page_facing_up: [purple]{url}[/purple]")

    path = gen_path(url)
    html = get_html(url, path)
    html = filter_html(html, path)
    mkdown = parse_html(html)

    if DEBUG_MODE:
        save_file(path[0] + path[1] + ".raw.md", mkdown, overwrite=True)

    mkdown = filter_mkdown(mkdown)

    if not CLI_MODE:
        mkdown = get_assets(path[0], html)

    if DEBUG_MODE or not CLI_MODE:
        save_file(path[0] + path[1] + ".md", mkdown, overwrite=True)

    if VERBOSE_MODE or CLI_MODE:
        print(mkdown)


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
        "-d", "--debug", dest="debug", default=False, help="debug mode", action="store_true"
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

        for url in urls:
            scrape(url)

    if not args.target and not args.list:
        print("[red]No URL to scrape. Please input an URL or Yaml list.[/red]")


if __name__ == "__main__":
    main()

