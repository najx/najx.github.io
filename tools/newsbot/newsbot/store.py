"""Where the pipeline keeps what it knows.

  .newsbot/archive/    one file per day: the day's distinct stories with
                       their judgements. A leading dot keeps Jekyll out of
                       it, so a year of daily files never touches build time.
  .newsbot/state.json  which stories already had a section in a report.
  _ai_news/            the reports themselves, a Jekyll collection.

Nothing under _data/ any more: Jekyll reads every file there on every build,
and the site no longer renders anything the daily run writes.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .models import Item
from .normalize import canonical_url

def count_by_source(items: list[Item]) -> dict[str, int]:
    """How many of these items came from each feed.

    Used for the `-v` log line during a run and, unchanged, for the
    `per_source` field written into the day's archive — so a feed's share of
    the 48h window can be read back across many days (issue #15 asks for a
    two-week measurement) instead of being re-derived from raw items later,
    or only existing for the length of one run's terminal output.
    """
    counts: dict[str, int] = {}
    for item in items:
        counts[item.source] = counts.get(item.source, 0) + 1
    return counts


def repo_root(start: Path | None = None) -> Path:
    """Walk up from the working directory to the one holding _config.yml.

    Anchored on where newsbot was *invoked*, not on where its code lives. The
    workflow installs the package with a plain `pip install ./tools/newsbot`,
    so __file__ sits in site-packages and walking up from there reaches / and
    finds nothing — which made every scheduled run die before fetching a feed.
    NEWSBOT_ROOT overrides, for running from outside the checkout.
    """
    override = os.environ.get("NEWSBOT_ROOT")
    here = Path(override).resolve() if override else (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "_config.yml").is_file():
            return candidate
    raise RuntimeError(
        f"no _config.yml at or above {here} — run newsbot from inside the "
        f"Jekyll site, or set NEWSBOT_ROOT to it"
    )


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.data = root / "_data"
        self.work = root / ".newsbot"
        self.archive = self.work / "archive"

    # --- paths ----------------------------------------------------------
    @property
    def reports(self) -> Path:
        return self.root / "_ai_news"

    @property
    def sources_yml(self) -> Path:
        return self.data / "news-sources.yml"

    @property
    def state_json(self) -> Path:
        return self.work / "state.json"

    def archive_for(self, day: datetime) -> Path:
        return self.archive / f"{day:%Y-%m-%d}.json"

    # --- io -------------------------------------------------------------
    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        """Write via a temporary file, so a crash never leaves a half file.

        The archive is what next Sunday's report is built from, and a
        truncated JSON there would fail the run that reads it.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        json.loads(text)  # parse what we are about to commit
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            # ensure_ascii=False means the payload carries real non-ASCII, so
            # the encoding cannot be left to the platform default.
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)

    def load_state(self) -> dict:
        """Which stories already had a section in a report, and when.

        Deliberately not a record of every URL ever seen: the feeds return
        ~2500 entries a day, and persisting them produced a quarter-megabyte
        file rewritten on every run for no benefit. Repeats are guarded by
        `covered`, which is small and exact.
        """
        if not self.state_json.is_file():
            return {"covered": [], "last_report": None}
        return json.loads(self.state_json.read_text(encoding="utf-8"))

    def save_state(self, state: dict) -> None:
        self._write_json(self.state_json, state)

    def record_covered(self, item: Item, slug: str, when: datetime) -> Path:
        """Note that this story had a section, so the next report skips it.

        The canonical URL and every `also_urls` write-up of the same story go
        in, because the week after, the follow-up arrives from whichever of
        those outlets was not the representative. The source title goes in
        too, for a human reading the file. Keyed on the URL: a report has
        several sections, so several entries share one slug, and rerunning
        the same week rewrites its entries rather than duplicating them.
        """
        state = self.load_state()
        url = canonical_url(item.url)
        covered = [c for c in state.get("covered", []) if c.get("url") != url]
        covered.append({
            "url": url,
            "also_urls": [canonical_url(u) for u in item.also_urls],
            "title": item.title,
            "slug": slug,
            "date": when.date().isoformat(),
        })
        state["covered"] = covered
        state["last_report"] = when.date().isoformat()
        state.pop("last_article", None)
        self.save_state(state)
        return self.state_json

    def latest_report(self) -> Path | None:
        """The most recent report file, by name — names are ISO week ids."""
        files = sorted(self.reports.glob("*.md")) if self.reports.is_dir() else []
        return files[-1] if files else None

    def save_archive(
        self,
        day: datetime,
        items: list[Item],
        failures: dict,
        scores: dict[str, dict] | None = None,
    ) -> Path:
        """Keep the day's distinct stories, summaries and judgements included.

        This is what the weekly report is built from — seven days of it — so
        it holds the windowed and deduplicated set with each story's score
        and the reason it was gated, not the raw feed haul.
        """
        scores = scores or {}
        path = self.archive_for(day)
        self._write_json(
            path,
            {
                "collected_at": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
                "failures": failures,
                "per_source": count_by_source(items),
                "items": [{**i.to_dict(), **scores.get(i.url, {})} for i in items],
            },
        )
        return path
