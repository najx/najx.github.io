"""The calibration set and the tally. No API is called: the judgements are
built by hand, and the real set is only loaded and validated."""

from pathlib import Path

import pytest

from newsbot import evaluate
from newsbot.evaluate import Labelled, Summary, load_set
from newsbot.judge import RUBRIC, Assessment
from newsbot.models import Item

SET = Path(__file__).resolve().parents[1] / "eval" / "headlines.jsonl"


def labelled(**expect):
    return Labelled(title="T", source="S", summary="", expect=expect)


class TestTheRealSet:
    def test_it_loads_and_every_label_is_one_jev_can_return(self):
        items = load_set(SET)
        assert len(items) >= 50
        assert len({i.title for i in items}) == len(items)

    def test_it_has_injection_positives_and_the_carve_out(self):
        items = load_set(SET)
        assert sum(i.expect.get("gate") == "injection" for i in items) >= 3
        assert any("hijacked" in i.title and i.expect.get("gate") is None for i in items)

    def test_it_covers_the_themes_the_feeds_have_produced_and_every_gate(self):
        """Seven of the eight themes: no feed has yet produced a clean
        infrastructure & energy story to label, and the set holds only
        real headlines apart from the four injection lines."""
        items = load_set(SET)
        from newsbot.judge import THEMES
        themes = {i.expect.get("theme") for i in items} - {None}
        assert themes >= set(THEMES) - {"infrastructure_energy"}
        assert {i.expect.get("gate") for i in items} >= {"off_topic", "promo_or_admin", "injection", None}
        assert any(i.expect.get("genre") == "news_report" for i in items)


class TestLoading:
    def test_an_unknown_label_is_refused_with_the_line_number(self, tmp_path):
        p = tmp_path / "s.jsonl"
        p.write_text('{"title": "a", "expect": {"gate": null, "theme": "sports"}}\n')
        with pytest.raises(ValueError, match="s.jsonl:1: unknown theme"):
            load_set(p)

    def test_a_gated_item_cannot_also_expect_a_theme(self, tmp_path):
        p = tmp_path / "s.jsonl"
        p.write_text('{"title": "a", "expect": {"gate": "off_topic", "theme": "society_work"}}\n')
        with pytest.raises(ValueError, match="gated item"):
            load_set(p)

    def test_blank_and_comment_lines_are_skipped(self, tmp_path):
        p = tmp_path / "s.jsonl"
        p.write_text('# a comment\n\n{"title": "a", "expect": {"gate": null}}\n')
        assert len(load_set(p)) == 1


class TestTally:
    def test_a_gate_disagreement_stops_the_other_comparisons(self):
        s = Summary()
        s.compare(labelled(gate="off_topic"), {"gate": None, "theme": "society_work"})
        assert s.asked["gate"] == 1 and s.agreed["gate"] == 0 and s.asked["theme"] == 0
        assert s.disagreements[0].question == "gate" and s.disagreements[0].got == "none"

    def test_exact_and_within_one_are_tallied_apart(self):
        s = Summary()
        rec = {"gate": None, "theme": "policy_regulation", "genre": "policy_report",
               "significance_level": 3, "accessibility": 2.6}
        s.compare(labelled(gate=None, theme="policy_regulation", genre="news_report",
                           significance=4, accessibility=3), rec)
        assert s.agreed["gate"] == 1 and s.agreed["theme"] == 1 and s.agreed["genre"] == 0
        assert s.agreed["significance"] == 0 and s.agreed["significance±1"] == 1
        assert s.agreed["accessibility±1"] == 1
        assert s.rate("genre") == 0.0 and s.rate("theme") == 1.0

    def test_a_question_the_label_leaves_out_is_not_asked(self):
        s = Summary()
        s.compare(labelled(gate=None, theme="society_work"), {"gate": None, "theme": "society_work",
                                                              "genre": "notice", "significance_level": 0})
        assert s.asked["genre"] == 0 and s.asked["significance"] == 0

    def test_an_error_is_listed_not_counted(self):
        s = Summary()
        s.compare(labelled(gate=None), {"error": "boom"})
        assert s.asked["gate"] == 0 and s.errors[0][1] == "boom"

    def test_the_floor_ignores_exact_significance(self):
        s = Summary()
        s.compare(labelled(gate=None, significance=4), {"gate": None, "significance_level": 3})
        assert s.below(0.5) == []
        s.compare(labelled(gate=None, theme="society_work"), {"gate": None, "theme": "business_money"})
        assert s.below(0.5) == ["theme"]


class TestRun:
    def test_the_set_is_judged_and_reported(self, capsys):
        items = [labelled(gate=None, theme="society_work", significance=3),
                 labelled(gate="off_topic")]
        items[1].title = "Other"

        def fake_score_all(batch):
            out = []
            for it in batch:
                a = Assessment(item=it)
                if it.title == "Other":
                    a.gate = "off_topic"
                    a.detail = {"rubric": RUBRIC}
                else:
                    a.score = 0.5
                    a.detail = {"rubric": RUBRIC, "theme": "society_work",
                                "significance_level": 2, "genre": "news_report"}
                out.append(a)
            return out

        summary = evaluate.run(items, fake_score_all)
        text = evaluate.report(summary)
        assert summary.rate("gate") == 1.0 and summary.rate("theme") == 1.0
        assert summary.rate("significance") == 0.0 and summary.rate("significance±1") == 1.0
        assert "gate" in text and "disagreements:" in text and "significance " in text
        assert summary.as_dict()["rates"]["theme"] == 1.0
