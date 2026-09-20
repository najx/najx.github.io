"""Reading the feed list and fetching it.

RSS and Atom only. Every source on the list publishes one, which means no
anti-bot to work around, no selectors to maintain, and nothing to reconsider
when a site reskins. Sources without a feed are the Apify adapter's job and
sit disabled in the YAML until then.
"""

from __future__ import annotations

import concurrent.futures as cf
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
import yaml

from .models import Item

log = logging.getLogger(__name__)

USER_AGENT = "najx-newsbot/0.1 (+https://najx.dev)"
TIMEOUT = 25
MAX_WORKERS = 12


@dataclass
class Source:
    name: str
    url: str
    enabled: bool = True
    note: str = ""


def load_sources(path: Path) -> list[Source]:
    """Read _data/news-sources.yml. Disabled entries are kept out."""
    data = yaml.safe_load(path.read_text()) or {}
    out = []
    for raw in data.get("sources", []):
        source = Source(
            name=raw["name"],
            url=raw["url"],
            enabled=raw.get("enabled", True),
            note=raw.get("note", ""),
        )
        if source.enabled:
            out.append(source)
    return out


def _entry_date(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
    return None


def _entry_summary(entry, limit: int = 400) -> str:
    """Two sentences at most.

    Jev loses accuracy on state padded with detail that no question asks
    about, so the summary is trimmed here rather than passed on whole.
    """
    raw = entry.get("summary") or entry.get("description") or ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:2])[:limit].strip()


def fetch(source: Source, session: requests.Session | None = None) -> list[Item]:
    """Fetch one feed. Raises on transport or parse failure."""
    client = session or requests
    response = client.get(
        source.url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
    )
    response.raise_for_status()
    parsed = feedparser.parse(response.content)

    items = []
    for entry in parsed.entries:
        title = (entry.get("title") or "").strip()
        link = (entry.get("link") or "").strip()
        published = _entry_date(entry)
        if not title or not link or published is None:
            # Undated entries cannot be windowed or ranked on freshness,
            # and a headline with no link cannot be sourced. Skip both.
            continue
        items.append(
            Item(
                title=" ".join(title.split()),
                url=link,
                source=source.name,
                published=published,
                summary=_entry_summary(entry),
            )
        )
    return items


def collect(sources: list[Source]) -> tuple[list[Item], dict[str, str]]:
    """Fetch every source in parallel.

    A source that fails does not fail the run — the others still publish.
    Returns the items plus a map of source name to error, so the workflow log
    says which feed went dark instead of silently shrinking the list.
    """
    items: list[Item] = []
    failures: dict[str, str] = {}

    with requests.Session() as session:
        with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(fetch, s, session): s for s in sources}
            for future in cf.as_completed(futures):
                source = futures[future]
                try:
                    got = future.result()
                except Exception as exc:  # noqa: BLE001 - reported, not raised
                    failures[source.name] = f"{type(exc).__name__}: {exc}"
                    log.warning("%s failed: %s", source.name, exc)
                else:
                    items.extend(got)
                    log.info("%s: %d items", source.name, len(got))

    return items, failures
