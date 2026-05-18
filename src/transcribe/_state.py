"""Runtime flags and shared diagnostic console.

Stopgap module for state shared across the package while the
single-file module is split up. A later commit replaces these
globals with a Config dataclass threaded through call sites.
"""

import pathlib

from rich.console import Console

CLI_MODE = False
VERBOSE_MODE = False
DEBUG_MODE = False

err = Console(stderr=True)

_output_path: str | None = None


def get_output_dir() -> str:
    """Resolve the output directory lazily from CWD at first use."""
    global _output_path
    if _output_path is None:
        _output_path = str(pathlib.Path.cwd() / "output")
    return _output_path
