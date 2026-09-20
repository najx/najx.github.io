import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from newsbot.models import Item  # noqa: E402

BASE = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def make_item():
    def _make(title, url=None, source="Example", minutes_ago=0, summary=""):
        return Item(
            title=title,
            url=url or f"https://example.com/{abs(hash(title))}",
            source=source,
            published=BASE - timedelta(minutes=minutes_ago),
            summary=summary,
        )

    return _make
