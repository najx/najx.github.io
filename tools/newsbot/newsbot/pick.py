"""Choosing the week's subject.

The home page and the weekly article read the same scores but apply very
different bars. A mis-ordered row on the home page is cheap and gets replaced
tomorrow; a badly chosen weekly subject wastes the week's article. The
confidence guide says thresholds scale with the cost of being wrong, so every
gate here is stricter than the list's.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import Item
from .normalize import canonical_url, jaccard, title_tokens

log = logging.getLogger(__name__)

WINDOW_DAYS = 7

# The weekly bar, each clause reading its own question.
MIN_SCORE = 0.55
MIN_INFORMATIVE = 0.60
MAX_INJECTION = 0.35
# Corroboration was a hard requirement here — the reasoning being that one
# fetched page should not be able to decide the week. Running it showed the
# reasoning was borrowed from a different source list: with aggregators in the
# mix, stories arrived two and three times over, but twenty curated outlets on
# distinct beats almost never carry the same item, and the gate rejected every
# candidate including a 0.758 incident report. The intent survives in a better
# place: cmd_article refuses to write when no source article could be fetched,
# and verify.py reads every factual claim of the draft back against the text
# that was fetched. Corroboration stays a ranking signal in judge.rank.
MIN_CORROBORATION = 1
MIN_FIT_TOP = 0.70         # probability mass in domain_fit's two best levels
MIN_FIT_CONFIDENCE = 0.50  # hard here; soft on the home page
MIN_GENRE_HARD = 0.55      # incident + engineering_report + research_result
MAX_ARCHIVE_OVERLAP = 0.40 # against titles already published

# A relaxed bar, used only when nothing clears the one above.
FALLBACK_SCORE = 0.45

# Do not return to a subject already written about within this many days.
COOLDOWN_DAYS = 60


@dataclass
class Candidate:
    item: Item
    judgement: dict

    @property
    def score(self) -> float:
        return self.judgement.get("score", 0.0)


def load_week(archive_dir: Path, now: datetime, days: int = WINDOW_DAYS) -> list[Candidate]:
    """Every scored story from the last `days` archives."""
    cutoff = now - timedelta(days=days)
    out: list[Candidate] = []
    for path in sorted(archive_dir.glob("*.json")):
        try:
            day = datetime.strptime(path.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if day < cutoff - timedelta(days=1):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for raw in payload.get("items", []):
            item = Item.from_dict(raw)
            if item.published < cutoff:
                continue
            # "model" joined this list after the fact, so archives written
            # before it exist and simply do not carry the key.
            judgement = {k: raw[k] for k in
                         ("score", "gate", "informative", "injection",
                          "fit_top", "fit_confidence", "genre_hard", "model")
                         if k in raw}
            if "score" in judgement:
                out.append(Candidate(item=item, judgement=judgement))

    # The daily collection keeps a 48h window, so almost every story lands in
    # two consecutive archives — without this, a week reads as thirteen days
    # and --candidate 1 returns the same story as --candidate 0.
    best: dict[str, Candidate] = {}
    for c in out:
        key = canonical_url(c.item.url)
        if key not in best or c.score > best[key].score:
            best[key] = c
    return sorted(best.values(), key=lambda c: -c.score)


def _archive_overlap(title: str, published_titles: list[str]) -> float:
    tokens = title_tokens(title)
    return max((jaccard(tokens, title_tokens(t)) for t in published_titles),
               default=0.0)


def _entry_date(entry: dict) -> datetime | None:
    """The day an entry of `covered` was written, or None if unreadable."""
    try:
        day = datetime.fromisoformat(str(entry.get("date", "")))
    except ValueError:
        return None
    return day if day.tzinfo else day.replace(tzinfo=timezone.utc)


def recent_coverage(covered: list[dict] | None, now: datetime,
                    days: int = COOLDOWN_DAYS) -> tuple[set[str], list[str]]:
    """What the blog already wrote about within `days`: URLs, and source titles.

    Both halves matter. The URL set catches the follow-up published by one of
    the outlets in `also_urls`, which the title check cannot see. The titles
    are the ones the *feed* used, not the ones Claude wrote: comparing a new
    headline against the rewritten title measured 0.00 overlap on a story we
    had just covered, so that check alone lets the sequel straight through.

    An entry whose date will not parse is kept rather than dropped. Failing
    closed costs at most one skipped subject; failing open costs a duplicate
    article.
    """
    cutoff = now - timedelta(days=days)
    urls: set[str] = set()
    titles: list[str] = []
    for entry in covered or []:
        day = _entry_date(entry)
        if day is not None and day < cutoff:
            continue
        for url in [entry.get("url", ""), *entry.get("also_urls", [])]:
            if url:
                urls.add(canonical_url(url))
        if entry.get("title"):
            titles.append(entry["title"])
    return urls, titles


def _reasons(c: Candidate, published_titles: list[str], covered_urls: set[str],
             strict: bool) -> list[str]:
    """Every clause this candidate fails. Empty means it qualifies."""
    j = c.judgement
    bad = []
    if j.get("gate"):
        bad.append(f"gated: {j['gate']}")
    if c.score < (MIN_SCORE if strict else FALLBACK_SCORE):
        bad.append(f"score {c.score:.2f}")
    if j.get("informative", 0.0) < MIN_INFORMATIVE:
        bad.append("thin state")
    if j.get("injection", 0.0) >= MAX_INJECTION:
        bad.append("possible injection")
    if c.item.corroboration < MIN_CORROBORATION:
        bad.append(f"corroboration {c.item.corroboration}")
    urls = {canonical_url(u) for u in [c.item.url, *c.item.also_urls]}
    if urls & covered_urls:
        bad.append(f"same story as an article under {COOLDOWN_DAYS} days old")
    overlap = _archive_overlap(c.item.title, published_titles)
    if overlap >= MAX_ARCHIVE_OVERLAP:
        bad.append(f"already covered ({overlap:.2f})")
    if strict:
        if j.get("fit_top", 0.0) < MIN_FIT_TOP:
            bad.append("subject not squarely on topic")
        if j.get("fit_confidence", 0.0) < MIN_FIT_CONFIDENCE:
            bad.append("low confidence on subject")
        if j.get("genre_hard", 0.0) < MIN_GENRE_HARD:
            bad.append("genre not reportable")
    return bad


def published_titles(posts_dir: Path) -> list[str]:
    out = []
    for path in posts_dir.glob("*/*.md"):
        m = re.search(r'^title:\s*"?(.+?)"?\s*$', path.read_text(encoding="utf-8"), re.M)
        if m:
            out.append(m.group(1))
    return out


def choose(candidates: list[Candidate], posts_dir: Path, index: int = 0,
           covered: list[dict] | None = None, now: datetime | None = None):
    """Pick the week's subject, and say why everything else lost.

    Returns (winner or None, report). The report lists every candidate with
    the clauses it failed, so the pull request can show the reasoning rather
    than just an outcome.

    `covered` is the `covered` list of .newsbot/state.json — the subjects
    already written about, with the URLs and the feed titles they arrived
    under. It is what makes COOLDOWN_DAYS mean anything.
    """
    now = now or datetime.now(timezone.utc)
    cooled_urls, cooled_titles = recent_coverage(covered, now)
    titles = published_titles(posts_dir) + cooled_titles
    report = []
    for strict in (True, False):
        eligible = []
        for c in sorted(candidates, key=lambda c: -c.score):
            bad = _reasons(c, titles, cooled_urls, strict)
            if strict:
                report.append({"title": c.item.title, "source": c.item.source,
                               "score": round(c.score, 3), "rejected_for": bad})
            if not bad:
                eligible.append(c)
        if len(eligible) > index:
            return eligible[index], report, strict
        if strict:
            log.info("nothing cleared the weekly bar; relaxing to the fallback")
    return None, report, False
