"""Tests for the weekly article: selection, rendering, claim extraction.

Nothing here calls an API. The drafting step's own request is exercised
against the live model in the workflow, not in the suite.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from newsbot import pick
from newsbot.models import Item
from newsbot.render import DEFAULT_TAG, TAGS, parse_draft, render, write_post
from newsbot.verify import sentences

NOW = datetime(2026, 9, 21, 12, tzinfo=timezone.utc)


def good_judgement(**over):
    base = {"score": 0.80, "gate": None, "informative": 0.95, "injection": 0.02,
            "fit_top": 0.90, "fit_confidence": 0.88, "genre_hard": 0.85}
    base.update(over)
    return base


def candidate(title="An incident worth writing about", days_ago=1, also=None, **over):
    return pick.Candidate(
        item=Item(title=title, url=f"https://x/{abs(hash(title))}", source="Ars",
                  published=NOW - timedelta(days=days_ago), also=also or []),
        judgement=good_judgement(**over),
    )


@pytest.fixture
def posts(tmp_path):
    d = tmp_path / "_posts" / "existing-post"
    d.mkdir(parents=True)
    (d / "2026-01-01-existing-post.md").write_text(
        '---\ntitle: "Multi-Agent Architectures in AI"\n---\nbody\n', encoding="utf-8")
    return tmp_path / "_posts"


class TestChoose:
    def test_the_best_qualifying_candidate_wins(self, posts):
        weak = candidate("A weaker but valid story", score=0.60)
        strong = candidate("The strongest story of the week", score=0.90)
        winner, _, strict = pick.choose([weak, strong], posts)
        assert winner.item.title == "The strongest story of the week"
        assert strict is True

    def test_a_gated_story_never_wins(self, posts):
        winner, _, _ = pick.choose([candidate(score=0.95, gate="promo_or_admin")], posts)
        assert winner is None

    def test_possible_injection_is_refused_outright(self, posts):
        winner, _, _ = pick.choose([candidate(injection=0.5)], posts)
        assert winner is None

    def test_a_subject_already_published_is_skipped(self, posts):
        winner, _, _ = pick.choose(
            [candidate("Multi-Agent Architectures in AI")], posts)
        assert winner is None

    def test_the_bar_relaxes_rather_than_publishing_nothing(self, posts):
        """A quiet week should still offer the author something to look at."""
        middling = candidate("A middling story", score=0.50, genre_hard=0.20)
        winner, _, strict = pick.choose([middling], posts)
        assert winner is not None and strict is False

    def test_a_truly_empty_week_publishes_nothing(self, posts):
        winner, _, _ = pick.choose([candidate(score=0.10)], posts)
        assert winner is None

    def test_the_report_says_why_each_one_lost(self, posts):
        _, report, _ = pick.choose([candidate(score=0.20, informative=0.1)], posts)
        reasons = report[0]["rejected_for"]
        assert any("score" in r for r in reasons)
        assert any("thin state" in r for r in reasons)

    def test_candidate_index_takes_the_runner_up(self, posts):
        a = candidate("First choice", score=0.90)
        b = candidate("Second choice", score=0.80)
        winner, _, _ = pick.choose([a, b], posts, index=1)
        assert winner.item.title == "Second choice"


class TestLoadWeek:
    def test_only_scored_and_recent_items_are_loaded(self, tmp_path):
        archive = tmp_path / "archive"
        archive.mkdir()
        recent, old = NOW - timedelta(days=2), NOW - timedelta(days=40)
        (archive / f"{recent:%Y-%m-%d}.json").write_text(json.dumps({"items": [
            {"title": "Scored", "url": "https://a/1", "source": "A",
             "published": recent.isoformat(), "score": 0.7},
            {"title": "Unscored", "url": "https://a/2", "source": "A",
             "published": recent.isoformat()},
        ]}), encoding="utf-8")
        (archive / f"{old:%Y-%m-%d}.json").write_text(json.dumps({"items": [
            {"title": "Ancient", "url": "https://a/3", "source": "A",
             "published": old.isoformat(), "score": 0.9},
        ]}), encoding="utf-8")
        titles = [c.item.title for c in pick.load_week(archive, NOW)]
        assert titles == ["Scored"]


class TestParseDraft:
    def test_metadata_is_split_off_the_body(self):
        p = parse_draft(
            "TITLE: A Title\nDESCRIPTION: A description.\nTAG: Security 🔐\n\nThe body.")
        assert p.title == "A Title"
        assert p.tag == "Security 🔐"
        assert p.body == "The body."

    def test_an_invented_tag_falls_back_rather_than_creating_a_seventh(self):
        p = parse_draft("TITLE: T\nDESCRIPTION: D.\nTAG: Robotics 🤖\n\nBody.")
        assert p.tag == DEFAULT_TAG and p.tag in TAGS

    def test_a_missing_title_is_an_error_not_a_guess(self):
        with pytest.raises(ValueError, match="TITLE"):
            parse_draft("DESCRIPTION: D.\n\nBody.")

    def test_slug_folds_accents_and_punctuation(self):
        p = parse_draft("TITLE: L'odyssée d'une requête : c'est parti !\n"
                        "DESCRIPTION: D.\n\nBody.")
        assert p.slug() == "l-odyssee-d-une-requete-c-est-parti"


class TestRender:
    def test_the_charter_flag_and_disclosure_are_both_present(self):
        """charter.md promises the model is named, and post.html renders the
        banner from ai_assisted. Neither is optional."""
        out = render(parse_draft("TITLE: T\nDESCRIPTION: D.\nTAG: AI 🤖\n\nBody."),
                     NOW, "Claude Opus 5", 30, 1)
        assert "ai_assisted: true" in out
        assert "Claude Opus 5" in out and "Jev 1.13" in out
        assert "30 claims, 1 flagged" in out

    def test_front_matter_matches_the_house_keys(self):
        out = render(parse_draft("TITLE: T\nDESCRIPTION: D.\nTAG: AI 🤖\n\nBody."),
                     NOW, "Claude Opus 5", 0, 0)
        head = out.split("---")[1]
        for key in ("title:", "date:", "modified:", "tags:", "description:",
                    "comments:", "lang:", "ai_assisted:"):
            assert key in head, key

    def test_a_quote_in_the_title_cannot_break_the_yaml(self):
        out = render(parse_draft('TITLE: The "best" model\nDESCRIPTION: D.\n\nB.'),
                     NOW, "Claude Opus 5", 0, 0)
        import yaml
        assert yaml.safe_load(out.split("---")[1])["title"] == "The 'best' model"

    def test_the_post_lands_where_jekyll_postfiles_expects(self, tmp_path):
        path = write_post(tmp_path,
                          parse_draft("TITLE: A Title\nDESCRIPTION: D.\n\nB."),
                          NOW, "Claude Opus 5", 0, 0)
        assert path.parent.name == "a-title"
        assert path.name == "2026-09-21-a-title.md"


class TestSentences:
    def test_headings_code_and_the_source_list_are_skipped(self):
        got = sentences(
            "# Heading\n\nA real sentence with enough words to be counted here.\n\n"
            "```\nthis is code that should not be checked at all\n```\n\n"
            "Sources:\n\n- **Outlet** — a source line that is not a claim\n")
        assert got == ["A real sentence with enough words to be counted here."]

    def test_links_are_unwrapped_so_the_url_is_not_checked(self):
        got = sentences("Anthropic [published a paper](https://x.com/y) about "
                        "interpretability last week.")
        assert "https://" not in got[0] and "published a paper" in got[0]
