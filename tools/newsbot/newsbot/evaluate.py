"""Measuring Jev's judgements against a hand-labelled set.

The ranking weights in judge.py are editorial judgement, and the rubrics
were written without ever being scored against an answer key. Until now the
only way to know whether a change to a criterion helped was to read the next
report. This module reads `tools/newsbot/eval/headlines.jsonl` — real
headlines from the archives, each with the answer the author expects — asks
Jev the production questions, and prints how often the two agree, question
by question, with every disagreement listed.

What is compared, and how:

* `gate` — exact. A story the label gates that Jev lets through, or the
  reverse, is one disagreement, and nothing else is compared for it: the
  other questions were not asked of a gated story.
* `theme`, `genre` — exact, on the label Jev returned.
* `significance` — the most probable level against the labelled level,
  reported both exact and within one level. Neighbouring levels of the
  rubric are close calls by design; two levels apart is a different reading.
* `accessibility` — within one level of the labelled one, on the rounded
  expected position.

A label may leave any question out; it is then not asked of that item.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .judge import GENRE_WEIGHT, THEMES
from .models import Item

log = logging.getLogger(__name__)

GATES = {"off_topic", "promo_or_admin", "injection"}
QUESTIONS = ("gate", "theme", "genre", "significance", "significance±1", "accessibility±1")


@dataclass
class Labelled:
    title: str
    source: str
    summary: str
    expect: dict
    note: str = ""

    def item(self, n: int, now: datetime) -> Item:
        return Item(title=self.title, url=f"eval://{n}", source=self.source,
                    published=now, summary=self.summary)


def load_set(path: Path) -> list[Labelled]:
    """The JSONL file, every label checked against the questions Jev is asked."""
    out: list[Labelled] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno}: {exc}") from None
        expect = raw.get("expect") or {}
        problems = _label_problems(expect)
        if problems:
            raise ValueError(f"{path}:{lineno}: {'; '.join(problems)}")
        out.append(Labelled(title=raw["title"], source=raw.get("source", "Example"),
                            summary=raw.get("summary", ""), expect=expect,
                            note=raw.get("note", "")))
    return out


def _label_problems(expect: dict) -> list[str]:
    bad = []
    gate = expect.get("gate")
    if gate is not None and gate not in GATES:
        bad.append(f"unknown gate {gate!r}")
    if "theme" in expect and expect["theme"] not in THEMES:
        bad.append(f"unknown theme {expect['theme']!r}")
    if "genre" in expect and expect["genre"] not in GENRE_WEIGHT:
        bad.append(f"unknown genre {expect['genre']!r}")
    if "significance" in expect and expect["significance"] not in range(5):
        bad.append("significance must be 0-4")
    if "accessibility" in expect and expect["accessibility"] not in range(4):
        bad.append("accessibility must be 0-3")
    if gate is not None and any(k in expect for k in ("theme", "genre", "significance", "accessibility")):
        bad.append("a gated item cannot also expect a theme, genre or level")
    return bad


@dataclass
class Disagreement:
    question: str
    expected: object
    got: object
    labelled: Labelled


@dataclass
class Summary:
    asked: dict[str, int] = field(default_factory=lambda: {q: 0 for q in QUESTIONS})
    agreed: dict[str, int] = field(default_factory=lambda: {q: 0 for q in QUESTIONS})
    disagreements: list[Disagreement] = field(default_factory=list)
    errors: list[tuple[Labelled, str]] = field(default_factory=list)

    def rate(self, question: str) -> float | None:
        n = self.asked[question]
        return self.agreed[question] / n if n else None

    def _tally(self, question: str, expected, got, labelled: Labelled, ok: bool) -> None:
        self.asked[question] += 1
        if ok:
            self.agreed[question] += 1
        else:
            self.disagreements.append(Disagreement(question, expected, got, labelled))

    def compare(self, labelled: Labelled, record: dict) -> None:
        """Score one item's judgement against its label."""
        if record.get("error"):
            self.errors.append((labelled, record["error"]))
            return
        expect = labelled.expect
        got_gate = record.get("gate")
        want_gate = expect.get("gate")
        self._tally("gate", want_gate or "none", got_gate or "none", labelled,
                    got_gate == want_gate)
        if got_gate is not None or want_gate is not None:
            return
        if "theme" in expect:
            self._tally("theme", expect["theme"], record.get("theme"), labelled,
                        record.get("theme") == expect["theme"])
        if "genre" in expect:
            self._tally("genre", expect["genre"], record.get("genre"), labelled,
                        record.get("genre") == expect["genre"])
        if "significance" in expect and record.get("significance_level") is not None:
            level = int(record["significance_level"])
            want = expect["significance"]
            self._tally("significance", want, level, labelled, level == want)
            self._tally("significance±1", want, level, labelled, abs(level - want) <= 1)
        if "accessibility" in expect and record.get("accessibility") is not None:
            level = int(round(float(record["accessibility"])))
            want = expect["accessibility"]
            self._tally("accessibility±1", want, level, labelled, abs(level - want) <= 1)

    def below(self, floor: float) -> list[str]:
        """The questions whose agreement is under `floor`; ±1 rates count,
        exact `significance` does not, since neighbouring levels are close
        calls by design."""
        return [q for q in ("gate", "theme", "genre", "significance±1", "accessibility±1")
                if self.rate(q) is not None and self.rate(q) < floor]

    def as_dict(self) -> dict:
        return {
            "asked": dict(self.asked),
            "agreed": dict(self.agreed),
            "rates": {q: self.rate(q) for q in QUESTIONS},
            "disagreements": [
                {"question": d.question, "expected": d.expected, "got": d.got,
                 "title": d.labelled.title, "source": d.labelled.source,
                 "note": d.labelled.note}
                for d in self.disagreements
            ],
            "errors": [{"title": l.title, "error": e} for l, e in self.errors],
        }


def run(labelled: list[Labelled], score_all) -> Summary:
    """Judge every item with `score_all` (judge.score_all in production,
    anything with the same shape in a test) and tally the agreement."""
    from .judge import as_record

    now = datetime.now(timezone.utc)
    items = [l.item(n, now) for n, l in enumerate(labelled)]
    by_url = {a.item.url: as_record(a) for a in score_all(items)}
    summary = Summary()
    for l, item in zip(labelled, items):
        summary.compare(l, by_url.get(item.url, {"error": "not judged"}))
    return summary


def report(summary: Summary) -> str:
    lines = ["question              agreed / asked"]
    for q in QUESTIONS:
        n = summary.asked[q]
        if not n:
            continue
        rate = summary.rate(q)
        lines.append(f"  {q:20s} {summary.agreed[q]:3d} / {n:<3d}  {rate:6.1%}")
    if summary.disagreements:
        lines.append("")
        lines.append("disagreements:")
        for d in summary.disagreements:
            if d.question in ("significance±1",):
                continue  # already listed under the exact question
            lines.append(f"  {d.question:14s} expected {str(d.expected):16s} "
                         f"got {str(d.got):16s} [{d.labelled.source}] {d.labelled.title[:70]}")
            if d.labelled.note:
                lines.append(f"  {'':14s} note: {d.labelled.note}")
    if summary.errors:
        lines.append("")
        lines.append("not judged:")
        for l, e in summary.errors:
            lines.append(f"  {l.title[:70]}: {e}")
    return "\n".join(lines)
