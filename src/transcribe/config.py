"""Runtime configuration threaded through the package."""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from rich.console import Console


@dataclass(frozen=True)
class Config:
    """Per-invocation knobs. Built once in cli._run inside an event loop."""

    client: httpx.AsyncClient
    semaphore: asyncio.Semaphore
    cli_mode: bool = False
    verbose_mode: bool = False
    debug_mode: bool = False
    delay: float = 0.0
    output_dir: str = field(default_factory=lambda: str(Path.cwd() / "output"))
    err: Console = field(default_factory=lambda: Console(stderr=True))
