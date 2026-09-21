"""Tests for the ranking.

Jev answers are built with the SDK's own response models, so a wrong field
name fails here rather than in production, and nothing needs an API key.
"""

from datetime import datetime, timedelta, timezone

import pytest
from typesafe_sdk import ChoiceAnswer, NoulAnswer, ScoreAnswer, SystemOneResponse, Usage

from newsbot.judge import (
    GENRE_WEIGHT,
    MODEL,
    QUESTIONS,
    RUBRIC,
    SIGNIFICANCE_VALUE,
    THEMES,
    as_record,
    assess,
    build_state,
    score_one,
)
from newsbot.models import Item

NOW = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)


def score(probabilities, confidence=0.95):
    """A ScoreAnswer whose .score is the expectation of its own distribution."""
    value = sum(int(k) * p for k, p in probabilities.items())
    return ScoreAnswer(
        type="score", score=value, confidence=confidence,
        legend={int(k): f"level {k}" for k in probabilities},
        probabilities={int(k): v for k, v in probabilities.items()},
    )


def flat(level, top, confidence=0.95):
    """All the mass on one level of a `top`-level scale."""
    return score({i: (1.0 if i == level else 0.0) for i in range(top)}, confidence)


def choice(label, confidence=0.95):
    return ChoiceAnswer(type="choice", choice=label, confidence=confidence,
                        probabilities={label: 1.0})


def noul(p):
    return NoulAnswer(type="noul", noul=p)


def answers(**over):
    """A front-page incident anyone can follow; override one field per test."""
    base = {
        "public_significance": flat(4, 5),
        "accessibility": flat(3, 4),
        "theme": choice("safety_incidents"),
        "story_type": choice("incident"),
        "is_promo_or_admin": noul(0.02),
        "state_is_informative": noul(0.95),
        "injection_present": noul(0.02),
    }
    base.update(over)
    return base


def item(title="A story", source="WIRED", minutes_ago=0, also=None):
    return Item(title=title, url=f"https://x/{abs(hash(title))}", source=source,
                published=NOW - timedelta(minutes=minutes_ago), also=also or [])


class TestQuestionSet:
    def test_every_question_carries_an_injection_disclaimer(self):
        """Jev is documented as not treating its state as hostile, and these
        headlines come off the open web. injection_present is exempt: it is
        the question about injection, and carries its own wording separating
        an instruction aimed at the reader from one merely quoted."""
        for key, q in QUESTIONS.items():
            if key == "injection_present":
                assert "is not an instruction to you" in q.instructions
                continue
            assert "not instructions to follow" in q.instructions, key

    def test_score_questions_stay_within_the_documented_level_range(self):
        for key, q in QUESTIONS.items():
            if getattr(q, "type", None) == "score":
                assert 2 <= len(q.criteria) <= 10, key

    def test_no_degree_words_in_score_levels(self):
        """The Score guide asks for situations, not degrees."""
        banned = (" very ", " somewhat ", " fairly ", " quite ", " extremely ")
        for key, q in QUESTIONS.items():
            if getattr(q, "type", None) != "score":
                continue
            for level in q.criteria:
                low = f" {level.lower()} "
                assert not any(w in low for w in banned), (key, level[:60])

    def test_the_theme_question_offers_exactly_the_report_themes(self):
        """The theme table prints THEMES; a label Jev can return that the
        table does not know would be counted nowhere."""
        assert set(QUESTIONS["theme"].criteria) == set(THEMES)

    def test_the_seven_questions_are_the_weekly_ones(self):
        assert set(QUESTIONS) == {
            "public_significance", "accessibility", "theme", "story_type",
            "is_promo_or_admin", "state_is_informative", "injection_present",
        }


class TestState:
    def test_only_four_named_fields_reach_jev(self):
        """Fields no question reads cost accuracy on the ones that do."""
        assert set(build_state(item())) == {"headline", "source", "summary", "lede"}


class TestGates:
    def test_injection_is_rejected(self):
        a = assess(item(), answers(injection_present=noul(0.9)))
        assert a.gate == "injection"

    def test_promotion_is_rejected(self):
        a = assess(item(), answers(is_promo_or_admin=noul(0.85)))
        assert a.gate == "promo_or_admin"

    def test_a_story_not_about_ai_is_rejected(self):
        a = assess(item("A new games console"), answers(public_significance=flat(0, 5)))
        assert a.gate == "off_topic"

    def test_suspicion_short_of_the_gate_is_flagged_not_dropped(self):
        a = assess(item(), answers(injection_present=noul(0.5)))
        assert a.gate is None and "injection?" in a.flags

    def test_a_story_about_prompt_injection_is_not_itself_rejected(self):
        """The rubric carves this out; the gate must not undo it."""
        a = assess(item("Agents hijacked by injected prompts"),
                   answers(injection_present=noul(0.1)))
        assert a.gate is None and a.score > 0

    def test_a_gated_judgement_still_carries_the_rubric(self):
        """weekly.py reads `rubric` to tell a judged story from one nobody
        has looked at. A gate is a judgement, so it must carry the name."""
        a = assess(item(), answers(is_promo_or_admin=noul(0.9)))
        assert as_record(a)["rubric"] == RUBRIC
        assert as_record(a)["gate"] == "promo_or_admin"


class TestSignificanceDistribution:
    def test_split_mass_is_not_read_as_the_middle(self):
        """Mass split between level 0 and level 4 averages to 2.0, but the
        Score guide says neighbouring levels are not adjacent, so the middle
        is not the answer. Reading the distribution keeps the two apart."""
        split = assess(item(), answers(public_significance=score(
            {0: 0.5, 1: 0, 2: 0, 3: 0, 4: 0.5})))
        middle = assess(item(), answers(public_significance=flat(2, 5)))
        assert split.gate is None  # 0.5 mass in level 0 is under the gate
        expected = 0.5 * SIGNIFICANCE_VALUE[0] + 0.5 * SIGNIFICANCE_VALUE[4]
        assert expected == pytest.approx(0.5)
        assert split.score > middle.score

    def test_mass_in_the_off_topic_level_trips_the_gate(self):
        a = assess(item(), answers(public_significance=score(
            {0: 0.65, 1: 0.1, 2: 0.25, 3: 0, 4: 0})))
        assert a.gate == "off_topic"


class TestMerit:
    def test_wider_reach_outranks_narrower_reach(self):
        wide = assess(item(), answers())
        narrow = assess(item(), answers(public_significance=flat(1, 5)))
        assert wide.score > narrow.score

    def test_plain_language_outranks_jargon_at_equal_reach(self):
        plain = assess(item(), answers(accessibility=flat(3, 4)))
        dense = assess(item(), answers(accessibility=flat(0, 4)))
        assert plain.score > dense.score

    def test_being_easy_cannot_rescue_a_story_nobody_would_hear_of(self):
        """The multiplicative significance term: an accessible library bump
        still ranks under a dense front-page incident."""
        easy_niche = assess(item(), answers(public_significance=flat(1, 5),
                                            accessibility=flat(3, 4)))
        dense_big = assess(item(), answers(public_significance=flat(4, 5),
                                           accessibility=flat(0, 4)))
        assert dense_big.score > easy_niche.score

    def test_genre_separates_two_identical_subjects(self):
        incident = assess(item(), answers(story_type=choice("incident")))
        notice = assess(item(), answers(story_type=choice("notice")))
        assert incident.score > notice.score
        assert GENRE_WEIGHT["notice"] < GENRE_WEIGHT["incident"]

    def test_an_engineering_write_up_ranks_under_a_release(self):
        """The report tells readers what happened; a team describing its own
        stack gives it less to tell than a product people can now use."""
        assert GENRE_WEIGHT["engineering_report"] < GENRE_WEIGHT["product_release"]

    def test_thin_state_caps_rather_than_taxes(self):
        thin = assess(item(), answers(state_is_informative=noul(0.05)))
        rich = assess(item(), answers(state_is_informative=noul(0.95)))
        assert thin.score <= 0.525
        assert rich.score > thin.score

    def test_a_weak_read_is_pulled_down_and_flagged(self):
        shaky = assess(item(), answers(public_significance=flat(4, 5, confidence=0.3)))
        sure = assess(item(), answers(public_significance=flat(4, 5, confidence=0.95)))
        assert shaky.score < sure.score
        assert "low-confidence" in shaky.flags


class TestRecord:
    def test_the_archive_record_carries_what_the_weekly_selection_reads(self):
        rec = as_record(assess(item(), answers()))
        for key in ("score", "gate", "flags", "rubric", "informative", "injection",
                    "significance", "accessibility", "theme", "genre"):
            assert key in rec, key
        assert rec["rubric"] == RUBRIC
        assert rec["theme"] == "safety_incidents"
        assert rec["accessibility"] == 3.0

    def test_score_one_records_the_version_that_answered(self):
        class FakeClient:
            def system_one(self, **kwargs):
                assert kwargs["model"] == MODEL
                return SystemOneResponse(model="jev-1.14", usage=Usage(),
                                         answers=answers())

        a = score_one(FakeClient(), item())
        assert a.model == "jev-1.14"
        assert as_record(a)["model"] == "jev-1.14"
