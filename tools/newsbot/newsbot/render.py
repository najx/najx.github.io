"""Turning a draft into a post this site will build.

The front matter has to match what _layouts/post.html and the klise theme
expect, and `ai_assisted: true` is not optional: charter.md promises that any
AI-assisted article says so and names the model. The theme already renders
the banner from that flag, and the disclosure line below names the models.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

TAGS = ["AI 🤖", "Cloud ☁️", "DevOps 🔄", "Code 👨‍💻", "Architecture 🏛️", "Security 🔐"]
DEFAULT_TAG = "AI 🤖"


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
        return folded[:70].rstrip("-")


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

    return Post(
        title=fields["TITLE"].strip().strip('"').rstrip("."),
        description=fields["DESCRIPTION"].strip(),
        tag=tag,
        body=markdown[body_start:].strip(),
    )


def disclosure(draft_model: str, checked: int, unsupported: int) -> str:
    """The line charter.md asks for: which model, and how it was used."""
    checked_note = (
        f"Every factual claim was checked back against those sources by "
        f"Jev 1.13 ({checked} claims, {unsupported} flagged for review)."
        if checked
        else "Citation checking did not run on this draft."
    )
    return (
        "---\n\n"
        f"*Drafted with {draft_model} from the sources listed above; the "
        f"subject was selected from a week of collected headlines by Jev 1.13. "
        f"{checked_note} Reviewed and edited before publication.*\n"
    )


def render(post: Post, when: datetime, model: str, checked: int, unsupported: int,
           lang: str = "en") -> str:
    stamp = when.strftime("%Y-%m-%d %H:%M:%S %z")
    stamp = stamp[:-2] + ":" + stamp[-2:] if stamp[-5] in "+-" else stamp
    title = post.title.replace('"', "'")
    return (
        "---\n"
        f'title: "{title}"\n'
        f"date: {stamp}\n"
        f"modified: {stamp}\n"
        f"tags: [{post.tag}]\n"
        f"description: {post.description}\n"
        "comments: false\n"
        f"lang: {lang}\n"
        "ai_assisted: true\n"
        "---\n\n"
        f"{post.body.rstrip()}\n\n"
        f"{disclosure(model, checked, unsupported)}"
    )


def write_post(root: Path, post: Post, when: datetime, model: str,
               checked: int, unsupported: int) -> Path:
    """_posts/<slug>/<date>-<slug>.md, the jekyll-postfiles layout."""
    slug = post.slug()
    directory = root / "_posts" / slug
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{when:%Y-%m-%d}-{slug}.md"
    path.write_text(render(post, when, model, checked, unsupported), encoding="utf-8")
    return path
