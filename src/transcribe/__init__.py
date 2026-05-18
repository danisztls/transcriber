"""Scrape Web content into markdown."""

__author__ = "Daniel Souza <me@posix.dev.br>"
__license__ = "GPLv3"

from .cli import main

__all__ = ["main"]


if __name__ == "__main__":
    main()
