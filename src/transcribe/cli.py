"""CLI entry point and scrape orchestration."""

import argparse
import os
import time

import yaml
from rich import print

from . import _state
from .assets import get_assets
from .extract import filter_html, filter_mkdown, get_html, parse_html
from .writer import gen_path, save_file


def chronometer(func):
    """Measure and report the execution time of a function."""

    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()

        if not _state.CLI_MODE:
            _state.err.print(f"[green]{round(end - start, 2)} seconds[/green]")

        return result

    return wrapper


@chronometer
def scrape(url: str) -> None:
    """Scrape URL and save Markdown content to disk."""
    if not _state.CLI_MODE:
        _state.err.print(f"\n[purple]{url}[/purple]")

    path = gen_path(url)

    try:
        html = get_html(url, path)
    except Exception:
        return

    html_filtered = filter_html(html, path)
    html_rewritten = get_assets(path[0], url, html_filtered)

    mkdown = parse_html(html_rewritten)

    if _state.DEBUG_MODE:
        save_file(os.path.join(path[0], path[1] + ".raw.md"), mkdown, overwrite=True)

    mkdown_filtered = filter_mkdown(mkdown)

    if _state.DEBUG_MODE or not _state.CLI_MODE:
        save_file(os.path.join(path[0], path[1] + ".md"), mkdown_filtered, overwrite=True)

    if _state.VERBOSE_MODE or _state.CLI_MODE:
        print(mkdown_filtered)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--target",
        dest="target",
        action="append",
        help="URL to scrap (repeatable)",
    )
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
    parser = _build_parser()
    args = parser.parse_args(argv)

    _state.CLI_MODE = args.cli
    _state.VERBOSE_MODE = args.verbose
    _state.DEBUG_MODE = args.debug

    if not _state.CLI_MODE:
        _state.err.print(":spider: scraping...")

    if args.target:
        for url in args.target:
            scrape(url)

    if args.list:
        with open(args.list, encoding="utf-8") as file:
            urls = yaml.safe_load(file) or []

        if not isinstance(urls, list):
            raise ValueError("YAML list file must contain a top-level list of URLs")

        for url in urls:
            if isinstance(url, str) and url.strip():
                scrape(url.strip())

    if not args.target and not args.list:
        _state.err.print("[red]No URL to scrape. Please input an URL or Yaml list.[/red]")
