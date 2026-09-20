"""Tests for the ranking.

Jev answers are built with the SDK's own response models, so a wrong field
name fails here rather than in production, and nothing needs an API key.
"""

from datetime import datetime, timedelta, timezone

import pytest
from typesafe_sdk import ChoiceAnswer, NoulAnswer, ScoreAnswer

from newsbot.judge import (
    DOMAIN_FIT_VALUE,
    GENRE_WEIGHT,
    MAX_PER_SOURCE,
    PUBLISH_FLOOR,
    QUESTIONS,
    assess,
    build_state,
    rank,
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
    """A solidly on-topic incident report; override one field per test."""
    base = {
        "domain_fit": flat(4, 5),
        "story_type": choice("incident"),
        "mechanism_depth": flat(4, 5),
        "practitioner_stakes": flat(3, 4),
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


class TestState:
    def test_only_four_named_fields_reach_jev(self):
        """Fields no question reads cost accuracy on the ones that do."""
        assert set(build_state(item())) == {"headline", "source", "summary", "lede"}


class TestGates:
    def test_injection_is_rejected(self):
        a = assess(item(), answers(injection_present=noul(0.9)))
        assert a.gate == "injection" and not a.published

    def test_promotion_is_rejected(self):
        a = assess(item(), answers(is_promo_or_admin=noul(0.85)))
        assert a.gate == "promo_or_admin"

    def test_off_beat_subject_is_rejected(self):
        a = assess(item(), answers(domain_fit=flat(0, 5)))
        assert a.gate == "off_beat"

    def test_suspicion_short_of_the_gate_is_flagged_not_dropped(self):
        a = assess(item(), answers(injection_present=noul(0.5)))
        assert a.gate is None and "injection?" in a.flags

    def test_a_story_about_prompt_injection_is_not_itself_rejected(self):
        """The rubric carves this out; the gate must not undo it."""
        a = assess(item("Agents hijacked by injected prompts"),
                   answers(injection_present=noul(0.1)))
        assert a.gate is None and a.published


class TestDomainFitDistribution:
    def test_split_mass_is_not_read_as_the_middle(self):
        """Mass split between level 0 and level 4 averages to 2.0, but the
        Score guide says neighbouring levels are not adjacent, so the middle
        is not the answer. Reading the distribution keeps the two apart."""
        split = assess(item(), answers(domain_fit=score({0: 0.5, 1: 0, 2: 0, 3: 0, 4: 0.5})))
        middle = assess(item(), answers(domain_fit=flat(2, 5)))
        assert split.gate is None  # 0.5 mass in levels 0-1 is under the gate
        expected = 0.5 * DOMAIN_FIT_VALUE[0] + 0.5 * DOMAIN_FIT_VALUE[4]
        assert expected == pytest.approx(0.5)
        assert split.score > middle.score

    def test_mass_in_the_reject_levels_trips_the_gate(self):
        a = assess(item(), answers(domain_fit=score({0: 0.35, 1: 0.3, 2: 0.35, 3: 0, 4: 0})))
        assert a.gate == "off_beat"


class TestMerit:
    def test_on_topic_incident_outranks_off_topic_incident(self):
        on = assess(item(), answers())
        off = assess(item(), answers(domain_fit=flat(3, 5)))
        assert on.score > off.score

    def test_genre_separates_two_identical_subjects(self):
        incident = assess(item(), answers(story_type=choice("incident")))
        notice = assess(item(), answers(story_type=choice("notice")))
        assert incident.score > notice.score
        assert GENRE_WEIGHT["notice"] < GENRE_WEIGHT["incident"]

    def test_thin_state_caps_rather_than_taxes(self):
        """A ceiling stops a bare title taking a top slot without moving every
        terse outlet down as a class."""
        thin = assess(item(), answers(state_is_informative=noul(0.05)))
        rich = assess(item(), answers(state_is_informative=noul(0.95)))
        assert thin.score <= 0.525
        assert rich.score > thin.score

    def test_a_weak_read_is_pulled_down_and_flagged(self):
        shaky = assess(item(), answers(domain_fit=flat(4, 5, confidence=0.3)))
        sure = assess(item(), answers(domain_fit=flat(4, 5, confidence=0.95)))
        assert shaky.score < sure.score
        assert "low-confidence" in shaky.flags


class TestRank:
    def test_one_outlet_cannot_take_the_whole_page(self):
        assessed = [assess(item(f"Story {n}", source="WIRED"), answers())
                    for n in range(6)]
        assert len(rank(assessed, NOW, limit=15)) == MAX_PER_SOURCE

    def test_slots_are_not_backfilled_with_gated_stories(self):
        good = [assess(item("Real story"), answers())]
        junk = [assess(item(f"Promo {n}", source=f"S{n}"),
                       answers(is_promo_or_admin=noul(0.9))) for n in range(20)]
        assert len(rank(good + junk, NOW, limit=15)) == 1

    def test_corroboration_breaks_a_tie(self):
        alone = assess(item("Solo", source="A"), answers())
        backed = assess(item("Backed", source="B", also=["C", "D", "E"]), answers())
        assert rank([alone, backed], NOW)[0].item.title == "Backed"

    def test_fresher_wins_all_else_equal(self):
        old = assess(item("Old", source="A", minutes_ago=60 * 40), answers())
        new = assess(item("New", source="B"), answers())
        assert rank([old, new], NOW)[0].item.title == "New"

    def test_below_the_floor_is_not_published(self):
        weak = assess(item(), answers(domain_fit=flat(2, 5),
                                      mechanism_depth=flat(0, 5),
                                      practitioner_stakes=flat(0, 4),
                                      story_type=choice("digest")))
        assert weak.score < PUBLISH_FLOOR
        assert rank([weak], NOW) == []
