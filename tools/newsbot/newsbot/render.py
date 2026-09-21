"""Turning a draft into a report this site will build.

The front matter has to match what _layouts/post.html, the home page and the
/ai-news index expect, and `ai_assisted: true` is not optional: charter.md
promises that any AI-assisted piece says so and names the model. The theme
already renders the banner from that flag, and the disclosure line below
names the models.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .judge import MODEL as JEV_MODEL

REPORTS_DIR = "_ai_news"

# Headings that are parts of the report rather than stories.
FIXED_HEADINGS = {"trends", "also this week", "sources"}


def _jev_label(model_id: str | None = None) -> str:
    """How to name, in prose, the Jev that actually answered.

    `model_id` is what the API itself returned in `SystemOneResponse.model`
    for the call being disclosed. Only a version found in that id is printed:
    the id we *send* is the floating alias `judge.MODEL`, and writing a
    version we merely believe is current is how the disclosure became false
    in the first place. An alias, or nothing at all, names no version.
    """
    ident = (model_id or JEV_MODEL).strip()
    m = re.fullmatch(r"jev[-_](\d[\w.]*)", ident, re.IGNORECASE)
    return f"Jev {m.group(1)}" if m else "Jev"


@dataclass
class Report:
    title: str
    description: str
    body: str


def parse_draft(markdown: str) -> Report:
    """Split the metadata lines off the front of a draft."""
    fields = {}
    body_start = 0
    for line in markdown.splitlines():
        m = re.match(r"^\s*(TITLE|DESCRIPTION|TAG):\s*(.+?)\s*$", line)
        if m:
            fields[m.group(1)] = m.group(2)
            body_start += len(line) + 1
        elif not line.strip() and fields:
            body_start += len(line) + 1
        elif fields:
            break
        else:
            body_start += len(line) + 1

    missing = {"TITLE", "DESCRIPTION"} - set(fields)
    if missing:
        raise ValueError(f"draft is missing {', '.join(sorted(missing))}")

    body = markdown[body_start:].strip()
    body = _strip_model_written_disclosure(body)

    return Report(
        title=fields["TITLE"].strip().strip('"').rstrip("."),
        description=fields["DESCRIPTION"].strip(),
        body=body,
    )


def _strip_model_written_disclosure(body: str) -> str:
    """Drop a trailing "Drafted with ..." paragraph the model wrote itself.

    style.md tells the model not to write one — `render()` appends the real
    disclosure, naming the actual model, after the body — but a draft cannot
    be trusted to always comply, and a model does not reliably know its own
    name. Belt and suspenders: if the last paragraph starts with "Drafted
    with", it is dropped here before the generated block is added, along with
    a lone trailing `---` rule left behind once that paragraph is gone.
    """
    paragraphs = re.split(r"\n\s*\n", body)
    if paragraphs and paragraphs[-1].strip().startswith("Drafted with"):
        paragraphs.pop()
        if paragraphs and paragraphs[-1].strip() == "---":
            paragraphs.pop()
    return "\n\n".join(paragraphs).rstrip()


# --- Anchors ----------------------------------------------------------------

def heading_id(text: str) -> str:
    """The id kramdown gives a heading, so the home page can link to it.

    Jekyll's default markdown engine generates header ids itself (auto_ids),
    and _includes/anchor_headings.html keeps the id it finds. kramdown's rule,
    reproduced: drop everything up to the first ASCII letter, drop every
    character that is not an ASCII letter, digit, space or hyphen, turn spaces
    into hyphens, lowercase. "Meta's Muse, nearly a million" therefore becomes
    "metas-muse-nearly-a-million" — the apostrophe and the comma vanish
    without leaving a hyphen, which is not what a generic slugify would do.
    """
    s = re.sub(r"^[^a-zA-Z]+", "", text)
    s = re.sub(r"[^a-zA-Z0-9 -]", "", s)
    return s.replace(" ", "-").lower() or "section"


def sections(body: str) -> list[tuple[str, str]]:
    """(anchor, heading) for every story section of the body."""
    out = []
    seen: dict[str, int] = {}
    for m in re.finditer(r"^##\s+(.+?)\s*$", body, re.M):
        title = m.group(1).strip()
        if title.rstrip(":").lower() in FIXED_HEADINGS:
            continue
        anchor = heading_id(title)
        # kramdown suffixes a repeated id with -1, -2, ...
        if anchor in seen:
            seen[anchor] += 1
            anchor = f"{anchor}-{seen[anchor]}"
        else:
            seen[anchor] = 0
        out.append((anchor, title))
    return out


# --- The theme table --------------------------------------------------------

def theme_table_markdown(rows: list[tuple[str, str, int, int | None]]) -> str:
    lines = ["| Theme | Stories this week | Last week |", "|---|---|---|"]
    for _, display, now_c, then_c in rows:
        last = str(then_c) if then_c is not None else "–"
        lines.append(f"| {display} | {now_c} | {last} |")
    return "\n".join(lines)


def insert_table(body: str, rows) -> str:
    """Put the theme table under `## Trends`, creating the section if need be.

    The counts are the pipeline's, not the model's: the prompt tells the
    model not to write a table, and this puts the real one in whatever it
    did. If the model wrote a table anyway it stays; a reviewer will see
    two and remove one, which beats silently trusting a model's arithmetic.
    """
    table = theme_table_markdown(rows)
    m = re.search(r"^##[ \t]+Trends[ \t]*$", body, re.M)
    if m:
        return body[:m.end()] + "\n\n" + table + body[m.end():]
    # No Trends section: add one before "Also this week", else before the
    # Sources rule, else at the end.
    for pattern in (r"^##[ \t]+Also this week[ \t]*$", r"^---[ \t]*$\n+\s*Sources:"):
        m = re.search(pattern, body, re.M)
        if m:
            return body[:m.start()] + "## Trends\n\n" + table + "\n\n" + body[m.start():]
    return body.rstrip() + "\n\n## Trends\n\n" + table + "\n"


# --- The file ---------------------------------------------------------------

def disclosure(draft_model: str, checked: int, unsupported: int,
               judge_model: str | None = None,
               verify_model: str | None = None) -> str:
    """The line charter.md asks for: which model, and how it was used.

    `judge_model` and `verify_model` are the ids the API returned for the two
    Jev steps — selection and citation checking. They are separate runs, so
    they are named separately rather than assumed equal. An archive written
    before this field existed supplies neither, and the label falls back to
    naming Jev without a version.
    """
    checked_note = (
        f"Every factual claim was checked back against those sources by "
        f"{_jev_label(verify_model)} ({checked} claims, {unsupported} flagged "
        f"for review)."
        if checked
        else "Citation checking did not run on this draft."
    )
    return (
        "---\n\n"
        f"*Drafted with {draft_model} from the sources listed above; the "
        f"stories were selected from a week of collected headlines by "
        f"{_jev_label(judge_model)}. "
        f"{checked_note} Reviewed and edited before publication.*\n"
    )


def _stamp(when: datetime) -> str:
    stamp = when.strftime("%Y-%m-%d %H:%M:%S %z")
    return stamp[:-2] + ":" + stamp[-2:] if stamp[-5] in "+-" else stamp


def render(report: Report, when: datetime, week_id: str, period: str,
           model: str, checked: int, unsupported: int,
           rows: list[tuple[str, str, int, int | None]] | None = None,
           judge_model: str | None = None, verify_model: str | None = None,
           lang: str = "en") -> str:
    body = insert_table(report.body, rows) if rows else report.body
    # json.dumps produces a valid YAML double-quoted scalar and escapes the
    # quotes, backslashes and control characters that would otherwise make the
    # front matter unparseable — and an unparseable front matter fails the
    # site build. A model-written description containing a colon-space is
    # enough to do it.
    stories = "".join(
        f"  - id: {anchor}\n    title: {json.dumps(title, ensure_ascii=False)}\n"
        for anchor, title in sections(body)
    )
    stamp = _stamp(when)
    return (
        "---\n"
        f"title: {json.dumps(report.title, ensure_ascii=False)}\n"
        f"date: {stamp}\n"
        f"modified: {stamp}\n"
        f"week: {week_id}\n"
        f"period: {json.dumps(period, ensure_ascii=False)}\n"
        f"description: {json.dumps(report.description, ensure_ascii=False)}\n"
        f"stories:\n{stories}"
        "comments: false\n"
        f"lang: {lang}\n"
        "ai_assisted: true\n"
        "---\n\n"
        f"{body.rstrip()}\n\n"
        f"{disclosure(model, checked, unsupported, judge_model, verify_model)}"
    )


def write_report(root: Path, report: Report, when: datetime, week_id: str,
                 period: str, model: str, checked: int, unsupported: int,
                 rows=None, judge_model: str | None = None,
                 verify_model: str | None = None) -> Path:
    """_ai_news/<week id>.md — one file per week, the collection layout."""
    directory = root / REPORTS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{week_id}.md"
    path.write_text(
        render(report, when, week_id, period, model, checked, unsupported,
               rows=rows, judge_model=judge_model, verify_model=verify_model),
        encoding="utf-8")
    return path
