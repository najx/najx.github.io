"""Reading the source articles.

Nothing fetched here is ever committed. The weekly article is written from
these texts and then they are dropped: storing other outlets' prose in a
public repository is not ours to do. What the repository keeps is what the
feeds publish — headline, link, source, date, the feed's own summary.
"""

from __future__ import annotations

import concurrent.futures as cf
import logging

import requests
import trafilatura

from .models import Item
from .sources import USER_AGENT

log = logging.getLogger(__name__)

TIMEOUT = 30
MAX_CHARS = 18_000          # per article, ~4.5k tokens
MAX_WORKERS = 5             # polite: these are article pages, not feeds


def fetch_text(url: str, session: requests.Session | None = None) -> str:
    """Main text of one article, or "" if it cannot be had.

    A source that will not load is not an error: the draft is written from
    whatever did load, and the count of what did is reported to the author.
    """
    client = session or requests
    try:
        response = client.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
        )
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - reported, never raised
        log.warning("fetch failed %s: %s", url, exc)
        return ""

    text = trafilatura.extract(
        response.text,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )
    if not text:
        log.warning("no main text extracted from %s", url)
        return ""
    return text[:MAX_CHARS]


def fetch_sources(items: list[Item]) -> dict[str, str]:
    """Fetch several articles at once. Keyed by URL; failures are absent."""
    out: dict[str, str] = {}
    with requests.Session() as session:
        with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(fetch_text, i.url, session): i for i in items}
            for future in cf.as_completed(futures):
                item = futures[future]
                text = future.result()
                if text:
                    out[item.url] = text
    return out
