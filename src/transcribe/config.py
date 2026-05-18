"""Runtime configuration threaded through the package."""

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console


@dataclass(frozen=True)
class Config:
    """Per-invocation knobs. Built once in cli.main and passed downstream."""

    cli_mode: bool = False
    verbose_mode: bool = False
    debug_mode: bool = False
    output_dir: str = field(default_factory=lambda: str(Path.cwd() / "output"))
    err: Console = field(default_factory=lambda: Console(stderr=True))
