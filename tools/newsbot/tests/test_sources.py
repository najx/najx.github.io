import calendar
from datetime import datetime, timedelta, timezone

from newsbot.sources import Source, _entry_date, _entry_summary, load_sources


def _struct(dt):
    return calendar.timegm(dt.utctimetuple()) and dt.utctimetuple()


class TestEntryDate:
    def test_normal_date_is_kept(self):
        when = datetime.now(timezone.utc) - timedelta(hours=3)
        assert _entry_date({"published_parsed": _struct(when)}) is not None

    def test_far_future_date_is_rejected(self):
        """A single bad pubDate would otherwise pin an item to the top of the
        home page until a human noticed."""
        when = datetime(2034, 1, 1, tzinfo=timezone.utc)
        assert _entry_date({"published_parsed": _struct(when)}) is None

    def test_small_clock_skew_is_tolerated(self):
        when = datetime.now(timezone.utc) + timedelta(hours=1)
        assert _entry_date({"published_parsed": _struct(when)}) is not None

    def test_undated_entry_returns_none(self):
        assert _entry_date({}) is None


class TestEntrySummary:
    def test_html_entities_are_decoded(self):
        got = _entry_summary({"summary": "Anthropic&#8217;s model &amp; its limits [&#8230;]"})
        assert "&#8217;" not in got and "&amp;" not in got
        assert "Anthropic’s model & its limits" in got

    def test_entity_encoded_markup_is_stripped(self):
        """The tags go; their inner text stays, which is what a summary is."""
        got = _entry_summary({"summary": "&lt;script&gt;alert(1)&lt;/script&gt; Real text."})
        assert "<" not in got and ">" not in got
        assert "Real text." in got

    def test_double_encoded_markup_cannot_reappear(self):
        """Decoding after the strip would hand back markup the regex already
        walked past."""
        got = _entry_summary({"summary": "&amp;lt;img src=x onerror=alert(1)&amp;gt; Text."})
        assert "<" not in got and ">" not in got

    def test_plain_tags_are_stripped(self):
        assert _entry_summary({"summary": "<p>Hello <b>world</b>.</p>"}).startswith("Hello world")

    def test_only_two_sentences_are_kept(self):
        got = _entry_summary({"summary": "One. Two. Three. Four."})
        assert "Three" not in got


class TestLoadSources:
    def test_disabled_sources_are_skipped(self, tmp_path):
        path = tmp_path / "s.yml"
        path.write_text(
            "sources:\n"
            "  - name: Live\n    url: https://a/feed\n"
            "  - name: Dead\n    url: https://b/feed\n    enabled: false\n",
            encoding="utf-8",
        )
        names = [s.name for s in load_sources(path)]
        assert names == ["Live"]


class TestCleanText:
    def test_double_encoded_apostrophe_in_a_title_is_decoded(self):
        """The Verge ships these. Liquid escapes on output, so an undecoded
        entity reaches the reader as the literal characters "&#8217;"."""
        from newsbot.sources import clean_text

        got = clean_text("Nvidia&#8217;s Jensen Huang thinks AI fears are overblown")
        assert "&#8217;" not in got
        assert got.startswith("Nvidia’s Jensen Huang")

    def test_markup_in_a_title_is_removed(self):
        from newsbot.sources import clean_text

        assert clean_text("<em>Exclusive</em>: the deal") == "Exclusive : the deal"

    def test_whitespace_is_collapsed(self):
        from newsbot.sources import clean_text

        assert clean_text("  too   many\n\nspaces ") == "too many spaces"
