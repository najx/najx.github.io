"""Tests for the week: merging archives, counting themes, choosing stories.

Nothing here calls an API. Judgements are the dicts the archives hold.
"""

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from newsbot import weekly
from newsbot.judge import RUBRIC
from newsbot.models import Item
from newsbot.store import Store

NOW = datetime(2026, 9, 20, 6, 17, tzinfo=timezone.utc)   # a Sunday morning


def judgement(**over):
    base = {"score": 0.70, "gate": None, "flags": [], "rubric": RUBRIC,
            "informative": 0.95, "injection": 0.02, "significance": 0.8,
            "significance_top": 0.9, "confidence": 0.9, "accessibility": 3.0,
            "theme": "safety_incidents", "theme_confidence": 0.9,
            "genre": "incident", "model": "jev-1.14"}
    base.update(over)
    return base


def story(title="A story", url=None, source="The Verge", days_ago=1.0, also=None,
          also_urls=None, days_seen=None, **over):
    it = Item(title=title, url=url or f"https://x/{abs(hash(title))}", source=source,
              published=NOW - timedelta(days=days_ago), also=also or [],
              also_urls=also_urls or [])
    return weekly.Story(item=it, judgement=judgement(**over),
                        days_seen=set(days_seen or {"2026-09-19"}),
                        urls={it.url, *it.also_urls}, published_last=it.published)


def entry(day, title, url, source="A", days_ago=1.0, **over):
    it = Item(title=title, url=url, source=source, published=NOW - timedelta(days=days_ago))
    return day, it, judgement(**over)


class TestMerge:
    def test_the_same_url_in_two_archives_is_one_story_with_two_days(self):
        stories = weekly.merge([
            entry("2026-09-18", "One story", "https://a/1?utm_source=rss", score=0.6),
            entry("2026-09-19", "One story", "https://a/1", score=0.7),
        ])
        assert len(stories) == 1
        assert stories[0].days_seen == {"2026-09-18", "2026-09-19"}
        assert stories[0].score == 0.7          # the better read of the two wins

    def test_two_outlets_on_one_event_become_one_story_with_two_outlets(self):
        stories = weekly.merge([
            entry("2026-09-19", "OpenAI releases GPT-6 model weights",
                  "https://a/1", source="WIRED", days_ago=1.5),
            entry("2026-09-19", "OpenAI releases the GPT-6 model weights today",
                  "https://b/2", source="The Verge", days_ago=1.0),
        ])
        assert len(stories) == 1
        assert stories[0].outlets == 2
        assert stories[0].item.source == "WIRED"            # earliest is the representative
        assert stories[0].urls == {"https://a/1", "https://b/2"}

    def test_the_best_judgement_of_the_cluster_is_kept(self):
        stories = weekly.merge([
            entry("2026-09-19", "OpenAI releases GPT-6 model weights",
                  "https://a/1", source="WIRED", days_ago=1.5, score=0.3),
            entry("2026-09-19", "OpenAI releases the GPT-6 model weights today",
                  "https://b/2", source="The Verge", days_ago=1.0, score=0.8),
        ])
        assert stories[0].score == 0.8

    def test_a_judgement_under_the_current_rubric_beats_an_older_higher_one(self):
        old = judgement(score=0.95)
        old["rubric"] = "technical-0"
        stories = weekly.merge([
            ("2026-09-18", Item("One story", "https://a/1", "A", NOW - timedelta(days=1)), old),
            entry("2026-09-19", "One story", "https://a/1", score=0.4),
        ])
        assert stories[0].scored and stories[0].score == 0.4

    def test_unrelated_stories_stay_apart(self):
        stories = weekly.merge([
            entry("2026-09-19", "Anthropic publishes interpretability research", "https://a/1"),
            entry("2026-09-19", "Kubernetes 1.40 reaches general availability", "https://a/2"),
        ])
        assert len(stories) == 2

    def test_corroboration_read_from_the_archive_survives_the_re_cluster(self):
        """The daily run already clustered the day and wrote `also`; the
        weekly re-cluster used to overwrite it with an empty list, so a story
        two outlets ran ranked as one and the prompt said "no other outlet"."""
        it = Item("Trump announces an AI Force", "https://d/1", "The Decoder",
                  NOW - timedelta(days=1), also=["The Verge"],
                  also_urls=["https://v/1"])
        stories = weekly.merge([("2026-09-19", it, judgement())])
        assert stories[0].outlets == 2
        assert stories[0].item.also == ["The Verge"]
        assert "https://v/1" in stories[0].urls

    def test_resolve_is_applied_to_the_clustered_list(self):
        seen = {}

        def resolve(items):
            seen["n"] = len(items)
            return items

        weekly.merge([entry("2026-09-19", "A", "https://a/1"),
                      entry("2026-09-19", "B", "https://a/2")], resolve=resolve)
        assert seen["n"] == 2


class TestWeeks:
    def test_the_two_weeks_split_on_the_latest_write_up(self):
        _, _, start, end = weekly.week_of(NOW)
        current = story("New", days_ago=2)
        older = story("Old", days_ago=10)
        ancient = story("Ancient", days_ago=20)
        assert weekly.in_week([current, older, ancient], start, end) == [current]
        assert weekly.week_before([current, older, ancient], start) == [older]

    @pytest.mark.parametrize("offset", range(8))
    def test_the_window_is_always_the_days_the_title_names(self, offset):
        """A Sunday run used to admit the Sunday before as well, and a manual
        run on a Tuesday put Monday and Tuesday into a report whose title said
        the week ended on Sunday."""
        now = NOW + timedelta(days=offset)
        _, _, start, end = weekly.week_of(now)
        # `story` dates from NOW, so place each one by its distance from NOW.
        on = lambda day: (NOW.date() - day).days
        stories = [story("first day", days_ago=on(start)),
                   story("last day", days_ago=on(end)),
                   story("the day before", days_ago=on(start) + 1),
                   story("the day after", days_ago=on(end) - 1)]
        got = [s.item.title for s in weekly.in_week(stories, start, end)]
        assert sorted(got) == ["first day", "last day"]

    def test_the_two_windows_do_not_overlap_and_leave_no_gap(self):
        _, _, start, end = weekly.week_of(NOW)
        every_day = [story(f"day -{n}", days_ago=n) for n in range(15)]
        this = {s.item.title for s in weekly.in_week(every_day, start, end)}
        prev = {s.item.title for s in weekly.week_before(every_day, start)}
        assert this & prev == set()
        assert len(this) == 7 and len(prev) == 7

    def test_unscored_lists_what_the_current_rubric_never_judged(self):
        s = story("Scored")
        u = story("Unscored")
        u.judgement = {"score": 0.9, "rubric": "technical-0"}
        n = story("Never")
        n.judgement = {}
        assert weekly.unscored([s, u, n]) == [u, n]


class TestThemeTable:
    def test_counts_this_week_against_last_busiest_first(self):
        current = [story("A", theme="policy_regulation"),
                   story("B", theme="policy_regulation"),
                   story("C", theme="models_products")]
        previous = [story("D", days_ago=9, theme="models_products")]
        rows = weekly.theme_table(current, previous)
        assert rows[0] == ("policy_regulation", "Policy & regulation", 2, 0)
        assert rows[1] == ("models_products", "Models & products", 1, 1)
        assert len(rows) == 8

    def test_gated_and_unscored_stories_are_not_counted(self):
        g = story("Promo", gate="promo_or_admin")
        u = story("Unjudged")
        u.judgement = {}
        rows = weekly.theme_table([g, u], [])
        assert all(r[2] == 0 for r in rows)

    def test_no_previous_week_prints_no_number(self):
        rows = weekly.theme_table([story("A")], [])
        assert all(r[3] is None for r in rows)


class TestTrend:
    def test_corroboration_lifts_a_story(self):
        alone = story("Solo")
        backed = story("Backed", also=["WIRED", "Ars", "Decoder"])
        assert weekly.trend(backed, NOW) > weekly.trend(alone, NOW)

    def test_recurrence_over_days_lifts_a_story(self):
        once = story("Once", days_seen={"2026-09-19"})
        thrice = story("Thrice", days_seen={"2026-09-17", "2026-09-18", "2026-09-19"})
        assert weekly.trend(thrice, NOW) > weekly.trend(once, NOW)

    def test_fresher_wins_all_else_equal(self):
        assert weekly.trend(story("New", days_ago=0.5), NOW) > \
            weekly.trend(story("Old", days_ago=6), NOW)

    def test_the_multiplier_never_zeroes_a_story(self):
        assert weekly.trend(story("Lonely", days_ago=6.9), NOW) > 0.5 * 0.70


class TestSelect:
    def test_the_best_stories_get_the_sections_in_trend_order(self):
        sel = weekly.select([story("Weak", score=0.4), story("Strong", score=0.9)], NOW)
        assert [s.item.title for s in sel.sections] == ["Strong", "Weak"]

    def test_no_more_sections_than_asked(self):
        stories = [story(f"S{n}", theme=t) for n, t in
                   enumerate(["a", "b", "c", "d", "e", "f", "g", "h"])]
        sel = weekly.select(stories, NOW, sections=6)
        assert len(sel.sections) == 6
        assert len(sel.also) == 2

    def test_a_theme_takes_at_most_two_sections(self):
        stories = [story(f"Policy {n}", theme="policy_regulation") for n in range(4)]
        sel = weekly.select(stories, NOW, sections=6)
        assert len(sel.sections) == 2
        assert len(sel.also) == 2        # the capped ones still get a line

    def test_a_gated_story_gets_nothing(self):
        sel = weekly.select([story("Promo", gate="promo_or_admin")], NOW)
        assert sel.sections == [] and sel.also == []
        assert sel.rejected[0][1] == ["gated: promo_or_admin"]

    def test_a_dense_story_gets_a_line_but_not_a_section(self):
        """The also-list is where the technical items go."""
        sel = weekly.select([story("Dense", accessibility=0.5)], NOW)
        assert sel.sections == []
        assert [s.item.title for s in sel.also] == ["Dense"]

    def test_possible_injection_is_refused_everywhere(self):
        sel = weekly.select([story("Hostile", injection=0.5)], NOW)
        assert sel.sections == [] and sel.also == []

    def test_thin_state_is_refused(self):
        sel = weekly.select([story("Bare", informative=0.2)], NOW)
        assert sel.sections == [] and sel.also == []

    def test_below_the_section_floor_but_above_the_line_floor(self):
        sel = weekly.select([story("Minor", score=0.2)], NOW)
        assert sel.sections == [] and [s.item.title for s in sel.also] == ["Minor"]

    def test_below_both_floors_is_out(self):
        sel = weekly.select([story("Nothing", score=0.05)], NOW)
        assert sel.sections == [] and sel.also == []

    def test_an_unscored_story_cannot_be_chosen(self):
        s = story("Unjudged")
        s.judgement = {"score": 0.9}
        sel = weekly.select([s], NOW)
        assert sel.sections == [] and sel.also == []
        assert "rubric" in sel.rejected[0][1][0]

    def test_a_story_with_no_fetchable_source_drops_and_the_next_moves_up(self):
        a, b = story("A", score=0.9, url="https://a/1"), story("B", score=0.5)
        sel = weekly.select([a, b], NOW, exclude=frozenset({"https://a/1"}))
        assert [s.item.title for s in sel.sections] == ["B"]
        assert all(s.item.title != "A" for s in sel.also)

    def test_fewer_than_three_sections_is_a_quiet_week(self):
        assert weekly.select([story("Only one")], NOW).quiet
        three = [story(f"S{n}", theme=t) for n, t in
                 enumerate(["policy_regulation", "models_products", "society_work"])]
        assert not weekly.select(three, NOW).quiet


class TestCooldown:
    def covered(self, url="https://x/subject", also_urls=None, days_ago=3):
        return [{"url": url, "also_urls": also_urls or [], "title": "t",
                 "slug": "2026-w37", "date": (NOW - timedelta(days=days_ago)).date().isoformat()}]

    def test_a_story_covered_recently_gets_no_section_and_no_line(self):
        sel = weekly.select([story("Again", url="https://x/subject")], NOW,
                            covered=self.covered())
        assert sel.sections == [] and sel.also == []
        assert "covered on" in sel.rejected[0][1][0]

    def test_past_the_cooldown_it_is_allowed_again(self):
        sel = weekly.select([story("Again", url="https://x/subject")], NOW,
                            covered=self.covered(days_ago=weekly.COOLDOWN_DAYS + 1))
        assert len(sel.sections) == 1

    def test_the_follow_up_from_another_outlet_is_caught(self):
        sel = weekly.select([story("Sequel", url="https://ars/part-two")], NOW,
                            covered=self.covered(url="https://verge/1",
                                                 also_urls=["https://ars/part-two"]))
        assert sel.sections == []

    def test_a_candidates_own_also_urls_are_matched_too(self):
        sel = weekly.select([story("New angle", url="https://new/1",
                                   also_urls=["https://x/subject"])], NOW,
                            covered=self.covered())
        assert sel.sections == []

    def test_tracking_parameters_do_not_defeat_the_match(self):
        sel = weekly.select([story("Again", url="https://www.x.com/subject/?utm_source=rss")],
                            NOW, covered=self.covered(url="https://x.com/subject"))
        assert sel.sections == []

    def test_an_unreadable_date_is_treated_as_recent(self):
        entry = self.covered()[0]
        entry["date"] = "last Sunday"
        sel = weekly.select([story("Again", url="https://x/subject")], NOW, covered=[entry])
        assert sel.sections == []


class TestPublishedCoverage:
    """The blog's own back catalogue closes the door on its own subjects."""

    @pytest.fixture
    def site(self, tmp_path):
        post = tmp_path / "_posts" / "when-the-model-stopped"
        post.mkdir(parents=True)
        (post / "2026-09-21-when-the-model-stopped.md").write_text(
            '---\ntitle: "When \\"The Model Stopped\\" Becomes a Safety Control"\n---\n\n'
            "The Verge [reported](https://www.theverge.com/997795/gemini-hack) this week.\n\n"
            "Sources:\n\n- **The Verge — Gemini went rogue**: "
            "[theverge.com/997795/gemini-hack](https://www.theverge.com/997795/gemini-hack)\n",
            encoding="utf-8")
        reports = tmp_path / "_ai_news"
        reports.mkdir()
        (reports / "2026-w37.md").write_text(
            '---\ntitle: "AI Weekly #37"\n---\n\nText. (https://wired.com/last-week)\n',
            encoding="utf-8")
        return tmp_path

    def test_links_and_titles_are_read_from_posts_and_reports(self, site):
        urls, titles = weekly.published_coverage(site)
        assert "https://theverge.com/997795/gemini-hack" in urls
        assert "https://wired.com/last-week" in urls
        assert any("Model Stopped" in t for t in titles)
        assert "AI Weekly #37" in titles

    def test_the_weeks_own_report_is_skipped(self, site):
        urls, titles = weekly.published_coverage(site, skip="2026-w37")
        assert "https://wired.com/last-week" not in urls
        assert "AI Weekly #37" not in titles
        assert "https://theverge.com/997795/gemini-hack" in urls

    def test_a_site_with_neither_directory_reads_as_empty(self, tmp_path):
        assert weekly.published_coverage(tmp_path) == (set(), [])

    def test_a_story_the_blog_already_wrote_from_gets_no_section(self, site):
        """The case that proves the URL check: the published article is
        titled "When the Model Stopped", which shares no word with the feed
        headline, so a title comparison alone let the digest re-cover it."""
        candidate = story("Gemini went rogue, hacked three companies, and Google hid it",
                          url="https://www.theverge.com/997795/gemini-hack")
        sel = weekly.select([candidate], NOW,
                            published=weekly.published_coverage(site))
        assert sel.sections == [] and sel.also == []
        assert "already cited" in sel.rejected[0][1][0]

    def test_the_title_check_still_catches_a_different_link(self, site):
        candidate = story("When The Model Stopped Becomes a Safety Control",
                          url="https://elsewhere.example/other")
        sel = weekly.select([candidate], NOW,
                            published=weekly.published_coverage(site))
        assert sel.sections == []
        assert "already published" in sel.rejected[0][1][0]

    def test_an_unrelated_story_still_gets_through(self, site):
        candidate = story("Amazon blocks Meta's shopping agent",
                          url="https://www.theverge.com/998078/amazon-muse")
        sel = weekly.select([candidate], NOW,
                            published=weekly.published_coverage(site))
        assert len(sel.sections) == 1

    def test_tracking_parameters_do_not_defeat_the_match(self, site):
        candidate = story("A rewrite of the same story",
                          url="https://theverge.com/997795/gemini-hack/?utm_source=rss")
        sel = weekly.select([candidate], NOW,
                            published=weekly.published_coverage(site))
        assert sel.sections == []

    def test_a_candidates_other_write_ups_are_matched_too(self, site):
        candidate = story("Another outlet on it", url="https://ars.example/1",
                          also_urls=["https://www.theverge.com/997795/gemini-hack"])
        sel = weekly.select([candidate], NOW,
                            published=weekly.published_coverage(site))
        assert sel.sections == []

    def test_no_published_coverage_changes_nothing(self):
        assert len(weekly.select([story("Anything")], NOW, published=None).sections) == 1

    def test_the_outlets_own_headline_is_harvested_from_the_sources_block(self, site):
        """Claude rewrites the title, so the article's own headline is a poor
        handle on the subject. The Sources block keeps the feed's."""
        _, titles = weekly.published_coverage(site)
        assert "Gemini went rogue" in " ".join(titles)


class TestSameEventAnotherOutlet:
    """A second outlet's write-up of a story the blog already covered has a
    different link and a rewritten headline, so neither exact check sees it."""

    REWRITE = "You too Google! Google Confirms Gemini Breached 3 Companies in May Test"
    PUBLISHED = "Gemini went rogue, hacked three companies, and Google hid it"

    def test_the_pair_lands_in_the_band_rather_than_above_it(self):
        from newsbot.normalize import jaccard, title_tokens
        score = jaccard(title_tokens(self.REWRITE), title_tokens(self.PUBLISHED))
        assert 0.20 <= score < weekly.MAX_TITLE_OVERLAP
        pairs = weekly.band_against_published([story(self.REWRITE)], [self.PUBLISHED])
        assert len(pairs) == 1

    def test_an_unrelated_headline_is_not_even_asked(self):
        assert weekly.band_against_published(
            [story("Kubernetes 1.40 reaches general availability")],
            [self.PUBLISHED]) == []

    def test_jev_saying_yes_excludes_the_story(self):
        matched = weekly.already_published([story(self.REWRITE, url="https://mk/1")],
                                           [self.PUBLISHED], ask=lambda a, b: True)
        assert matched == {"https://mk/1"}
        sel = weekly.select([story(self.REWRITE, url="https://mk/1")], NOW,
                            published=(matched, [self.PUBLISHED]))
        assert sel.sections == [] and sel.also == []

    def test_jev_saying_no_leaves_it_alone(self):
        assert weekly.already_published([story(self.REWRITE)], [self.PUBLISHED],
                                        ask=lambda a, b: False) == set()

    def test_the_url_is_canonicalised_so_the_exclusion_matches(self):
        matched = weekly.already_published(
            [story(self.REWRITE, url="https://www.mk.com/1/?utm_source=rss")],
            [self.PUBLISHED], ask=lambda a, b: True)
        assert matched == {"https://mk.com/1"}

    def test_one_story_is_asked_about_once_however_many_titles_match(self):
        asked = []
        weekly.already_published([story(self.REWRITE, url="https://mk/1")],
                                 [self.PUBLISHED, self.PUBLISHED + " today"],
                                 ask=lambda a, b: asked.append(b) or True)
        assert len(asked) == 1


class TestWeekOf:
    def test_a_sunday_run_names_the_week_ending_that_day(self):
        week_id, period, start, end = weekly.week_of(NOW)
        assert week_id == "2026-w38"
        assert (start, end) == (date(2026, 9, 14), date(2026, 9, 20))
        assert period == "14 to 20 September 2026"

    def test_a_tuesday_run_names_the_last_complete_week(self):
        week_id, _, _, end = weekly.week_of(NOW + timedelta(days=2))
        assert week_id == "2026-w38" and end == date(2026, 9, 20)

    def test_a_saturday_run_names_the_previous_week(self):
        week_id, _, _, end = weekly.week_of(NOW - timedelta(days=1))
        assert week_id == "2026-w37" and end == date(2026, 9, 13)

    def test_the_label_and_the_window_agree_on_every_weekday(self):
        for offset in range(8):
            now = NOW + timedelta(days=offset)
            _, _, start, end = weekly.week_of(now)
            assert (end - start).days == weekly.WINDOW_DAYS - 1
            assert end.weekday() == 6, now

    def test_period_labels_across_a_month_and_a_year(self):
        assert weekly.period_label(date(2026, 9, 28), date(2026, 10, 4)) == \
            "28 September to 4 October 2026"
        assert weekly.period_label(date(2025, 12, 29), date(2026, 1, 4)) == \
            "29 December 2025 to 4 January 2026"


class TestLoadArchives:
    def test_reads_two_weeks_of_archives_and_the_judgement_keys(self, tmp_path):
        store = Store(tmp_path)
        recent = NOW - timedelta(days=2)
        old = NOW - timedelta(days=40)
        item = Item("Recent", "https://a/1", "A", recent)
        store.save_archive(recent, [item], {}, {item.url: judgement()})
        store.save_archive(old, [Item("Ancient", "https://a/3", "A", old)], {},
                           {"https://a/3": judgement()})
        got = list(weekly.load_archives(store.archive, NOW))
        assert [i.title for _, i, _ in got] == ["Recent"]
        assert got[0][2]["theme"] == "safety_incidents"
        assert got[0][2]["model"] == "jev-1.14"

    def test_an_archive_without_judgements_loads_as_unscored(self, tmp_path):
        store = Store(tmp_path)
        item = Item("Bare", "https://a/1", "A", NOW - timedelta(days=1))
        store.save_archive(NOW, [item], {})
        got = list(weekly.load_archives(store.archive, NOW))
        assert got[0][2] == {}
        assert weekly.unscored(weekly.merge(got))
