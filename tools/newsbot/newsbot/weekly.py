"""The week's stories: seven days of archives, merged, ranked, selected.

The daily collection scores each story on the day it appears. This module
reads a week of those archives back and turns them into the plan for the
weekly report: which stories get a section, which get a line under "Also
this week", and what the theme count says about the week.

Everything that is a count or a date is computed here, in Python, exactly:
how many outlets carried a story, how many days it kept appearing, how many
stories fell under each theme this week and last. Jev is documented as
unreliable at all three, so none of them is ever asked of a model.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Callable

from .judge import RUBRIC, THEMES
from .models import Item
from .normalize import canonical_url, cluster

log = logging.getLogger(__name__)

WINDOW_DAYS = 7
SECTIONS = 6             # stories that get a section of their own
ALSO = 7                 # one-line items under "Also this week"
MAX_PER_THEME = 2        # sections per theme; the also-list has no cap
MIN_SECTIONS = 3         # fewer eligible stories than this: a quiet week

# Section bar, each clause reading its own question.
MIN_SCORE = 0.30
MIN_INFORMATIVE = 0.60
MAX_INJECTION = 0.35
MIN_ACCESSIBILITY = 1.5  # on the 0-3 scale: a section has to be explainable

# The also-list bar: lower, and no accessibility clause — a one-line item can
# carry a technical story the sections would not.
ALSO_MIN_SCORE = 0.15

# A story that had a section does not get another one for this long. The
# seven-day window already keeps most repeats out; this catches the story
# that straddles two Sundays and the follow-up published under a new link.
COOLDOWN_DAYS = 21

MAX_SOURCES_PER_STORY = 3


@dataclass
class Story:
    """One story of the week: a cluster of write-ups and its best judgement."""

    item: Item                      # the representative write-up, earliest first
    judgement: dict                 # the best judgement among the write-ups
    days_seen: set[str] = field(default_factory=set)   # archive dates
    urls: set[str] = field(default_factory=set)        # canonical, every write-up
    published_last: datetime | None = None             # latest write-up

    @property
    def score(self) -> float:
        return float(self.judgement.get("score", 0.0) or 0.0)

    @property
    def theme(self) -> str | None:
        return self.judgement.get("theme")

    @property
    def gate(self) -> str | None:
        return self.judgement.get("gate")

    @property
    def scored(self) -> bool:
        """Judged under the current rubric. Older scores are not comparable."""
        return self.judgement.get("rubric") == RUBRIC

    @property
    def outlets(self) -> int:
        return 1 + len(self.item.also)

    @property
    def source_urls(self) -> list[str]:
        """The write-ups worth fetching, the representative first."""
        return [self.item.url, *self.item.also_urls][:MAX_SOURCES_PER_STORY]


@dataclass
class Selection:
    sections: list[Story]
    also: list[Story]
    rejected: list[tuple[Story, list[str]]]
    table: list[tuple[str, str, int, int | None]]   # (label, display, this, last)

    @property
    def quiet(self) -> bool:
        return len(self.sections) < MIN_SECTIONS


# --- Reading the archives ---------------------------------------------------

JUDGEMENT_KEYS = (
    "score", "gate", "flags", "rubric", "informative", "injection",
    "significance", "significance_top", "confidence", "accessibility",
    "theme", "theme_confidence", "genre", "model", "error",
)


def load_archives(archive_dir: Path, now: datetime, days: int = WINDOW_DAYS):
    """Every entry of the archives covering this week and the one before.

    Yields (archive day, item, judgement). Two weeks, because the theme table
    compares this week's count with last week's. Reaching back from the
    labelled week's start, not from `now`, because a run late in the week
    would otherwise drop the very days its own report is about.
    """
    _, _, start, _ = week_of(now, days)
    cutoff = datetime.combine(start, time.min, tzinfo=timezone.utc) - timedelta(days=days + 1)
    for path in sorted(archive_dir.glob("*.json")):
        try:
            day = datetime.strptime(path.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if day < cutoff:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for raw in payload.get("items", []):
            item = Item.from_dict(raw)
            judgement = {k: raw[k] for k in JUDGEMENT_KEYS if k in raw}
            yield path.stem, item, judgement


def _better(a: dict, b: dict) -> dict:
    """Of two judgements of the same story, the one to keep."""
    key = lambda j: (j.get("rubric") == RUBRIC, "score" in j, float(j.get("score") or 0.0))
    return a if key(a) >= key(b) else b


def merge(entries, resolve: Callable[[list[Item]], list[Item]] | None = None) -> list[Story]:
    """Fold a week of daily entries into distinct stories.

    Three steps. Entries pointing at the same document are folded first — the
    48h collection window puts nearly every story in two consecutive
    archives. Then write-ups of the same event from different outlets are
    clustered on their headlines, exactly as the daily run does, and
    `resolve` (Jev's same_story question, when a key is configured) settles
    the pairs the lexical overlap could not. Each story keeps the best
    judgement any of its write-ups received, the union of the days it was
    seen, and every URL it appeared under.
    """
    by_url: dict[str, dict] = {}
    for day, item, judgement in entries:
        key = canonical_url(item.url)
        slot = by_url.setdefault(key, {"item": item, "judgement": judgement,
                                       "days": set(), "also": set(),
                                       "also_urls": set(), "last": item.published})
        slot["days"].add(day)
        slot["also"].update(item.also)
        slot["also_urls"].update(item.also_urls)
        slot["last"] = max(slot["last"], item.published)
        if _better(judgement, slot["judgement"]) is judgement:
            slot["judgement"] = judgement
        if item.published < slot["item"].published:
            slot["item"] = item

    items = []
    for key, slot in by_url.items():
        head = slot["item"]
        head.also = sorted(slot["also"] - {head.source})
        head.also_urls = sorted(slot["also_urls"] - {head.url})
        items.append(head)

    clustered = cluster(items)
    if resolve is not None and clustered:
        clustered = resolve(clustered)

    stories = []
    for head in clustered:
        members = {canonical_url(head.url)} | {canonical_url(u) for u in head.also_urls}
        present = [by_url[m] for m in members if m in by_url]
        judgement = present[0]["judgement"]
        for slot in present[1:]:
            judgement = _better(judgement, slot["judgement"])
        stories.append(Story(
            item=head,
            judgement=judgement,
            days_seen=set().union(*(s["days"] for s in present)) if present else set(),
            urls=members,
            published_last=max(s["last"] for s in present) if present else head.published,
        ))
    return stories


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    """The instants a day range spans, inclusive of both ends."""
    return (datetime.combine(start, time.min, tzinfo=timezone.utc),
            datetime.combine(end, time.max, tzinfo=timezone.utc))


def in_week(stories: list[Story], start: date, end: date) -> list[Story]:
    """Stories whose latest write-up falls inside the days the report names.

    Windowed on the labelled week, never on `now - 7 days`. The two are not
    the same: a Sunday run admitted the previous Sunday as well, and a manual
    run on a Tuesday put stories from Monday and Tuesday into a report whose
    title said the week ended on Sunday.
    """
    lo, hi = _bounds(start, end)
    return [s for s in stories if lo <= (s.published_last or s.item.published) <= hi]


def week_before(stories: list[Story], start: date, days: int = WINDOW_DAYS) -> list[Story]:
    """The same, for the week ending the day before `start`."""
    return in_week(stories, start - timedelta(days=days), start - timedelta(days=1))


def unscored(stories: list[Story]) -> list[Story]:
    """Stories no judgement under the current rubric exists for.

    An archive written under an earlier question set, or a day the key was
    missing, leaves these. The weekly run scores them before selecting, so a
    change of rubric costs one run's worth of Jev calls rather than a week of
    silence.
    """
    return [s for s in stories if not s.scored]


# --- Counting and ranking ---------------------------------------------------

def theme_table(current: list[Story], previous: list[Story]):
    """Stories per theme, this week against last, busiest first.

    Only judged, ungated stories are counted: a promotion or an off-topic
    item is not part of the week's coverage of anything.
    """
    def counts(stories):
        out = {label: 0 for label in THEMES}
        for s in stories:
            if s.scored and not s.gate and s.theme in out:
                out[s.theme] += 1
        return out

    now_c, then_c = counts(current), counts(previous)
    has_previous = any(s.scored for s in previous)
    rows = [(label, THEMES[label], now_c[label],
             then_c[label] if has_previous else None) for label in THEMES]
    order = {label: i for i, label in enumerate(THEMES)}
    return sorted(rows, key=lambda r: (-r[2], order[r[0]]))


def trend(story: Story, now: datetime, half_life_days: float = 4.0) -> float:
    """The ranking score: Jev's merit, lifted by corroboration, recurrence and freshness.

    Corroboration is how many outlets carried the story; recurrence how many
    daily archives it appeared in; both are counted here, not asked of a
    model. A story nobody but one outlet ran, once, on Monday, still ranks —
    the multiplier bottoms out at 0.55, it never zeroes — but the story four
    outlets kept writing about all week ranks above it at equal merit.
    """
    when = story.published_last or story.item.published
    age_days = max(0.0, (now - when).total_seconds() / 86400.0)
    freshness = 0.5 ** (age_days / half_life_days)
    corroboration = min(story.outlets, 4) / 4.0
    recurrence = min(len(story.days_seen), 3) / 3.0
    return story.score * (0.55 + 0.25 * corroboration + 0.10 * recurrence + 0.10 * freshness)


# --- The cooldown -----------------------------------------------------------

def _entry_date(entry: dict) -> datetime | None:
    try:
        day = datetime.fromisoformat(str(entry.get("date", "")))
    except ValueError:
        return None
    return day if day.tzinfo else day.replace(tzinfo=timezone.utc)


def recent_coverage(covered: list[dict] | None, now: datetime,
                    days: int = COOLDOWN_DAYS) -> dict[str, str]:
    """Canonical URL -> the date it was covered, for entries inside the cooldown.

    An entry whose date will not parse is kept rather than dropped. Failing
    closed costs at most one skipped section; failing open costs a repeat.
    """
    cutoff = now - timedelta(days=days)
    out: dict[str, str] = {}
    for entry in covered or []:
        day = _entry_date(entry)
        if day is not None and day < cutoff:
            continue
        for url in [entry.get("url", ""), *entry.get("also_urls", [])]:
            if url:
                out[canonical_url(url)] = str(entry.get("date", "?"))
    return out


# --- Selection --------------------------------------------------------------

def _reasons(s: Story, covered: dict[str, str], section: bool) -> list[str]:
    """Every clause this story fails for a section (or, if not, for the also-list)."""
    j = s.judgement
    bad = []
    if not s.scored:
        bad.append("not judged under the current rubric")
        return bad
    if s.gate:
        bad.append(f"gated: {s.gate}")
    floor = MIN_SCORE if section else ALSO_MIN_SCORE
    if s.score < floor:
        bad.append(f"score {s.score:.2f}")
    if float(j.get("informative", 0.0)) < MIN_INFORMATIVE:
        bad.append("thin state")
    if float(j.get("injection", 0.0)) >= MAX_INJECTION:
        bad.append("possible injection")
    # Canonical on both sides, whoever built the Story.
    urls = {canonical_url(u) for u in (*s.urls, s.item.url, *s.item.also_urls)}
    hit = urls & set(covered)
    if hit:
        bad.append(f"covered on {covered[next(iter(hit))]}")
    if section and float(j.get("accessibility", 0.0)) < MIN_ACCESSIBILITY:
        bad.append(f"needs background ({float(j.get('accessibility', 0.0)):.1f}/3)")
    return bad


def select(stories: list[Story], now: datetime, covered: list[dict] | None = None,
           previous: list[Story] | None = None, sections: int = SECTIONS,
           also: int = ALSO, per_theme: int = MAX_PER_THEME,
           exclude: frozenset[str] = frozenset()) -> Selection:
    """Choose the sections and the also-list, and say why everything else lost.

    `exclude` holds representative URLs the caller could not fetch a source
    for: a section is written from the article, never from the headline, so
    such a story drops out and the next one moves up.
    """
    cooled = recent_coverage(covered, now)
    ordered = sorted(stories, key=lambda s: -trend(s, now))

    chosen: list[Story] = []
    per: dict[str, int] = {}
    leftovers: list[tuple[Story, list[str]]] = []
    rejected: list[tuple[Story, list[str]]] = []

    for s in ordered:
        if s.item.url in exclude:
            rejected.append((s, ["no source article could be fetched"]))
            continue
        bad = _reasons(s, cooled, section=True)
        theme = s.theme or "?"
        if not bad and per.get(theme, 0) >= per_theme:
            bad = [f"theme cap: {theme}"]
        if not bad and len(chosen) < sections:
            chosen.append(s)
            per[theme] = per.get(theme, 0) + 1
        else:
            leftovers.append((s, bad or ["no section left"]))

    # What did not get a section may still get a line. The also-list bar has
    # no accessibility clause and a lower floor, so a technical story the
    # sections would not carry can still be mentioned.
    lines: list[Story] = []
    for s, bad in leftovers:
        if len(lines) < also and not _reasons(s, cooled, section=False):
            lines.append(s)
        else:
            rejected.append((s, bad))

    return Selection(sections=chosen, also=lines, rejected=rejected,
                     table=theme_table(stories, previous or []))


# --- Naming the week --------------------------------------------------------

def week_of(now: datetime, days: int = WINDOW_DAYS) -> tuple[str, str, date, date]:
    """(week id, period label, first day, last day) for the report run at `now`.

    The report is named after the ISO week ending on the most recent Sunday,
    today included. A run on a Sunday morning labels the week that ends that
    day; a manual run on a Tuesday still labels the last complete week rather
    than the one just started. `in_week` then windows the stories on exactly
    these two days, so the contents always match the title.
    """
    end = now.date()
    if end.weekday() != 6:
        end -= timedelta(days=end.weekday() + 1)
    start = end - timedelta(days=days - 1)
    year, week, _ = end.isocalendar()
    return f"{year}-w{week:02d}", period_label(start, end), start, end


def period_label(start: date, end: date) -> str:
    if start.year != end.year:
        return f"{start:%-d %B %Y} to {end:%-d %B %Y}"
    if start.month != end.month:
        return f"{start:%-d %B} to {end:%-d %B %Y}"
    return f"{start:%-d} to {end:%-d %B %Y}"
