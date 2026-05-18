"""CLI entry point and scrape orchestration."""

import argparse
import os
import time

import yaml

from .assets import get_assets
from .config import Config
from .extract import filter_html, filter_mkdown, get_html, parse_html
from .writer import gen_path, save_file


def scrape(url: str, cfg: Config) -> None:
    """Scrape URL and save Markdown content to disk."""
    if not cfg.cli_mode:
        cfg.err.print(f"\n[purple]{url}[/purple]")

    start = time.time()
    path = gen_path(url, cfg)

    try:
        html = get_html(url, path, cfg)
    except Exception:
        return

    html_filtered = filter_html(html, path, cfg)
    html_rewritten = get_assets(path[0], url, html_filtered, cfg)

    mkdown = parse_html(html_rewritten)

    if cfg.debug_mode:
        save_file(os.path.join(path[0], path[1] + ".raw.md"), mkdown, cfg, overwrite=True)

    mkdown_filtered = filter_mkdown(mkdown)

    if cfg.debug_mode or not cfg.cli_mode:
        save_file(os.path.join(path[0], path[1] + ".md"), mkdown_filtered, cfg, overwrite=True)

    if cfg.verbose_mode or cfg.cli_mode:
        print(mkdown_filtered)

    if not cfg.cli_mode:
        cfg.err.print(f"[green]{round(time.time() - start, 2)} seconds[/green]")


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

    cfg = Config(
        cli_mode=args.cli,
        verbose_mode=args.verbose,
        debug_mode=args.debug,
    )

    if not cfg.cli_mode:
        cfg.err.print(":spider: scraping...")

    if args.target:
        for url in args.target:
            scrape(url, cfg)

    if args.list:
        with open(args.list, encoding="utf-8") as file:
            urls = yaml.safe_load(file) or []

        if not isinstance(urls, list):
            raise ValueError("YAML list file must contain a top-level list of URLs")

        for url in urls:
            if isinstance(url, str) and url.strip():
                scrape(url.strip(), cfg)

    if not args.target and not args.list:
        cfg.err.print("[red]No URL to scrape. Please input an URL or Yaml list.[/red]")
