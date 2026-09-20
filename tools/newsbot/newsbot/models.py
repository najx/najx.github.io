"""The one shape everything else passes around."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class Item:
    """A single headline, as collected from a feed."""

    title: str
    url: str
    source: str
    published: datetime
    summary: str = ""

    # Filled in by normalize.cluster(): the other sources that carried the
    # same story. Corroboration is the strongest importance signal we have,
    # and it is counted here rather than asked of a model.
    also: list[str] = field(default_factory=list)

    @property
    def corroboration(self) -> int:
        """How many distinct outlets carried this story, this one included."""
        return 1 + len(self.also)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["published"] = self.published.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Item":
        published = d["published"]
        if isinstance(published, str):
            published = datetime.fromisoformat(published)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        return cls(
            title=d["title"],
            url=d["url"],
            source=d["source"],
            published=published,
            summary=d.get("summary", ""),
            also=list(d.get("also", [])),
        )
