"""Turning a draft into a post this site will build.

The front matter has to match what _layouts/post.html and the klise theme
expect, and `ai_assisted: true` is not optional: charter.md promises that any
AI-assisted article says so and names the model. The theme already renders
the banner from that flag, and the disclosure line below names the models.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .judge import MODEL as JEV_MODEL

TAGS = ["AI 🤖", "Cloud ☁️", "DevOps 🔄", "Code 👨‍💻", "Architecture 🏛️", "Security 🔐"]
DEFAULT_TAG = "AI 🤖"


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
class Post:
    title: str
    description: str
    tag: str
    body: str

    def slug(self) -> str:
        folded = unicodedata.normalize("NFKD", self.title)
        folded = "".join(c for c in folded if not unicodedata.combining(c))
        folded = re.sub(r"[^a-zA-Z0-9]+", "-", folded).strip("-").lower()
        # A title with no ASCII alphanumerics folds to "", and an empty slug
        # would write the post directly into _posts/ as "<date>-.md", where
        # the next one overwrites it.
        return folded[:70].rstrip("-") or (
            "article-" + hashlib.sha1(self.title.encode()).hexdigest()[:8]
        )


def parse_draft(markdown: str) -> Post:
    """Split the three metadata lines off the front of a draft."""
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

    tag = fields.get("TAG", DEFAULT_TAG).strip()
    if tag not in TAGS:
        # A seventh tag would fragment /tags/ for no gain; fall back rather
        # than invent one.
        tag = DEFAULT_TAG

    body = markdown[body_start:].strip()
    body = _strip_model_written_disclosure(body)

    return Post(
        title=fields["TITLE"].strip().strip('"').rstrip("."),
        description=fields["DESCRIPTION"].strip(),
        tag=tag,
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


def disclosure(draft_model: str, checked: int, unsupported: int,
               judge_model: str | None = None,
               verify_model: str | None = None) -> str:
    """The line charter.md asks for: which model, and how it was used.

    `judge_model` and `verify_model` are the ids the API returned for the two
    Jev steps — selection and citation checking. They are two separate runs,
    days apart, so they are named separately rather than assumed equal. An
    archive written before this field existed supplies neither, and the
    label falls back to naming Jev without a version.
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
        f"subject was selected from a week of collected headlines by "
        f"{_jev_label(judge_model)}. "
        f"{checked_note} Reviewed and edited before publication.*\n"
    )


def render(post: Post, when: datetime, model: str, checked: int, unsupported: int,
           lang: str = "en", judge_model: str | None = None,
           verify_model: str | None = None) -> str:
    stamp = when.strftime("%Y-%m-%d %H:%M:%S %z")
    stamp = stamp[:-2] + ":" + stamp[-2:] if stamp[-5] in "+-" else stamp
    # json.dumps produces a valid YAML double-quoted scalar and escapes the
    # quotes, backslashes and control characters that would otherwise make the
    # front matter unparseable — and an unparseable front matter fails the
    # site build. A model-written description containing a colon-space is
    # enough to do it.
    return (
        "---\n"
        f"title: {json.dumps(post.title, ensure_ascii=False)}\n"
        f"date: {stamp}\n"
        f"modified: {stamp}\n"
        f"tags: [{post.tag}]\n"
        f"description: {json.dumps(post.description, ensure_ascii=False)}\n"
        "comments: false\n"
        f"lang: {lang}\n"
        "ai_assisted: true\n"
        "---\n\n"
        f"{post.body.rstrip()}\n\n"
        f"{disclosure(model, checked, unsupported, judge_model, verify_model)}"
    )


def write_post(root: Path, post: Post, when: datetime, model: str,
               checked: int, unsupported: int,
               judge_model: str | None = None,
               verify_model: str | None = None) -> Path:
    """_posts/<slug>/<date>-<slug>.md, the jekyll-postfiles layout."""
    slug = post.slug()
    directory = root / "_posts" / slug
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{when:%Y-%m-%d}-{slug}.md"
    path.write_text(
        render(post, when, model, checked, unsupported,
               judge_model=judge_model, verify_model=verify_model),
        encoding="utf-8")
    return path
