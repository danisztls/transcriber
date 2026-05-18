"""HTTP fetching with UA rotation and Retry-After backoff."""

import asyncio
from urllib.parse import urlparse

import httpx

from .config import Config

_USER_AGENTS = [
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; DuckDuckBot/1.0; +http://duckduckgo.com/duckduckbot.html)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def _parse_retry_after(value: str | None) -> float:
    """Parse a Retry-After header value into seconds, capped."""
    if not value:
        return 0.0
    try:
        return min(max(float(value), 0.0), 60.0)
    except ValueError:
        return 5.0


async def get_response_data(url: str, cfg: Config) -> bytes:
    """Fetch URL and return the response body as bytes.

    Rotates through user agents on retryable failures and honors
    Retry-After. Concurrency is bounded by cfg.semaphore.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("URL must be a non-empty string")
    url = url.strip()
    if urlparse(url).scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://")

    last_error: BaseException | None = None
    last_status: int | None = None
    retryable_statuses = {401, 403, 429, 503}

    for attempt, ua in enumerate(_USER_AGENTS):
        try:
            async with cfg.semaphore:
                response = await cfg.client.get(url, headers={"User-Agent": ua})

            if cfg.debug_mode:
                cfg.err.print(f"[gray]{url}[/gray] -> {response.status_code} ({ua})")

            last_status = response.status_code

            if last_status == 200:
                return response.content

            if last_status not in retryable_statuses:
                break

            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            await asyncio.sleep(retry_after if retry_after > 0 else min(2**attempt, 30))
        except httpx.HTTPError as e:
            last_error = e
            last_status = None

    if last_status is not None:
        raise ValueError(f"HTTP request failed for URL: {url}. Status: {last_status}")
    raise ValueError(f"HTTP request failed for URL: {url}. {last_error}")
