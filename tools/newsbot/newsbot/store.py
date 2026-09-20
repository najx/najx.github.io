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
from datetime import datetime, timezone
from pathlib import Path

from .models import Item

HOME_ITEMS = 15


def repo_root(start: Path | None = None) -> Path:
    """Walk up to the directory holding _config.yml."""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "_config.yml").is_file():
            return candidate
    raise RuntimeError("not inside the Jekyll site (no _config.yml found)")


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
        tmp.write_text(text)
        tmp.replace(path)

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
        return json.loads(self.state_json.read_text())

    def save_state(self, state: dict) -> None:
        self._write_json(self.state_json, state)

    def save_archive(self, day: datetime, items: list[Item], failures: dict) -> Path:
        """Keep the day's distinct stories, summaries included.

        This is what the weekly article ranks over, so it holds the windowed
        and deduplicated set — not the raw feed haul.
        """
        path = self.archive_for(day)
        self._write_json(
            path,
            {
                "collected_at": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
                "failures": failures,
                "items": [i.to_dict() for i in items],
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
