"""Where the pipeline keeps what it knows.

Two destinations, deliberately separate:

  _data/news.json      the short list the site renders. Jekyll reads every
                       file under _data/ on every build, so this is the only
                       thing that belongs there.
  .newsbot/            the full archive, the rolling shortlist and the seen
                       set. A leading dot keeps Jekyll out of it, so a year
                       of daily files never touches build time.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .models import Item
from .normalize import canonical_url

HOME_ITEMS = 15


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
    def news_json(self) -> Path:
        return self.data / "news.json"

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
        """Write via a temporary file, so a crash never leaves _data/ broken.

        A malformed news.json would fail the Jekyll build and take the site
        down, which is a steep price for a feed hiccup.
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
        """Which stories already became an article, and when.

        Deliberately not a record of every URL ever seen: the feeds return
        ~2500 entries a day, and persisting them produced a quarter-megabyte
        file rewritten on every run for no benefit. Re-proposal is guarded by
        `covered` and by the posts already in _posts/, both of which are
        small and exact.
        """
        if not self.state_json.is_file():
            return {"covered": [], "last_article": None}
        return json.loads(self.state_json.read_text(encoding="utf-8"))

    def save_state(self, state: dict) -> None:
        self._write_json(self.state_json, state)

    def record_covered(self, item: Item, slug: str, when: datetime) -> Path:
        """Note that this story became an article, so pick can refuse it later.

        The canonical URL and every `also_urls` write-up of the same story go
        in, because the week after, the follow-up arrives from whichever of
        those outlets was not the representative. The source title goes in
        too: Claude rewrites the headline, so the published title is not a
        usable handle on the subject — the Gemini break-in was written up as
        "When the Model Stopped", which shares no word with the feed title.
        """
        state = self.load_state()
        covered = [c for c in state.get("covered", []) if c.get("slug") != slug]
        covered.append({
            "url": canonical_url(item.url),
            "also_urls": [canonical_url(u) for u in item.also_urls],
            "title": item.title,
            "slug": slug,
            "date": when.date().isoformat(),
        })
        state["covered"] = covered
        state["last_article"] = when.date().isoformat()
        self.save_state(state)
        return self.state_json

    def save_archive(
        self,
        day: datetime,
        items: list[Item],
        failures: dict,
        scores: dict[str, dict] | None = None,
    ) -> Path:
        """Keep the day's distinct stories, summaries and judgements included.

        This is what the weekly article ranks over — seven days of it — so it
        holds the windowed and deduplicated set with each story's score and
        the reason it was gated, not the raw feed haul and not just the
        fifteen that reached the home page.
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

    def save_home(self, items: list[Item], limit: int = HOME_ITEMS) -> Path:
        """Write the list the home page renders.

        Only the fields the template touches, so a change of ranking never
        reshapes what Liquid has to deal with.
        """
        self._write_json(
            self.news_json,
            {
                "generated_at": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
                "items": [
                    {
                        "title": i.title,
                        "url": i.url,
                        "source": i.source,
                        "date": i.published.isoformat(),
                        "corroboration": i.corroboration,
                    }
                    for i in items[:limit]
                ],
            },
        )
        return self.news_json
