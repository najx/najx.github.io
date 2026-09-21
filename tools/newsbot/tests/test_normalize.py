from newsbot.normalize import (
    CLUSTER_BAND_LOW,
    CLUSTER_CERTAIN,
    canonical_url,
    cluster,
    dedupe,
    jaccard,
    normalize_title,
    title_tokens,
)


class TestCanonicalUrl:
    def test_strips_tracking_and_fragment(self):
        assert canonical_url(
            "https://www.Example.com/a/b/?utm_source=rss&id=7&fbclid=z#top"
        ) == "https://example.com/a/b?id=7"

    def test_keeps_meaningful_query(self):
        assert canonical_url("https://x.com/p?page=2") == "https://x.com/p?page=2"

    def test_bare_host_keeps_root_slash(self):
        assert canonical_url("https://example.com") == "https://example.com/"

    def test_relative_url_passes_through_untouched(self):
        assert canonical_url("/relative/path") == "/relative/path"

    def test_same_story_two_feeds_one_url(self):
        a = canonical_url("https://site.com/story?utm_campaign=feed")
        b = canonical_url("https://www.site.com/story/#comments")
        assert a == b


class TestNormalizeTitle:
    def test_folds_accents_and_punctuation(self):
        assert normalize_title("Déjà vu: AI's “big” week!") == "deja vu ai s big week"

    def test_curly_and_straight_apostrophes_match(self):
        assert normalize_title("Meta’s Muse") == normalize_title("Meta's Muse")

    def test_tokens_drop_stopwords_and_short_words(self):
        assert title_tokens("The AI of the New Era") == {"era"}


class TestJaccard:
    def test_empty_is_zero(self):
        assert jaccard(frozenset(), frozenset({"a"})) == 0.0

    def test_identical_is_one(self):
        assert jaccard(frozenset({"a", "b"}), frozenset({"a", "b"})) == 1.0


class TestDedupe:
    def test_same_url_modulo_tracking_kept_once(self, make_item):
        items = [
            make_item("First wording", "https://site.com/x?utm_source=a", minutes_ago=0),
            make_item("Other wording", "https://www.site.com/x/", minutes_ago=30),
        ]
        assert len(dedupe(items)) == 1

    def test_earliest_publication_wins(self, make_item):
        items = [
            make_item("Late", "https://site.com/x", minutes_ago=0),
            make_item("Early", "https://site.com/x", minutes_ago=60),
        ]
        assert dedupe(items)[0].title == "Early"

    def test_identical_headline_at_different_urls_both_survive(self, make_item):
        """dedupe keys on the URL alone. Two outlets running the same wire
        headline are two documents; collapsing them here would hide the
        corroboration that cluster() exists to count."""
        items = [
            make_item("Same headline", "https://a.com/1", source="Reuters"),
            make_item("Same headline", "https://b.com/2", source="AP", minutes_ago=5),
        ]
        assert len(dedupe(items)) == 2

    def test_distinct_stories_survive(self, make_item):
        items = [make_item("Alpha ships"), make_item("Beta ships")]
        assert len(dedupe(items)) == 2


class TestCluster:
    def test_near_identical_headlines_merge_and_record_sources(self, make_item):
        items = [
            make_item(
                "OpenAI releases GPT-6 model weights",
                "https://a.com/1", source="WIRED", minutes_ago=60,
            ),
            make_item(
                "OpenAI releases the GPT-6 model weights today",
                "https://b.com/2", source="The Verge", minutes_ago=10,
            ),
        ]
        stories = cluster(items)
        assert len(stories) == 1
        assert stories[0].source == "WIRED"          # earliest wins
        assert stories[0].also == ["The Verge"]
        assert stories[0].corroboration == 2

    def test_unrelated_headlines_stay_apart(self, make_item):
        stories = cluster([
            make_item("Anthropic publishes interpretability research"),
            make_item("Kubernetes 1.40 reaches general availability"),
        ])
        assert len(stories) == 2
        assert all(s.corroboration == 1 for s in stories)

    def test_same_outlet_twice_is_not_corroboration(self, make_item):
        stories = cluster([
            make_item("Gemini breach hits three companies",
                      "https://a.com/1", source="WIRED", minutes_ago=60),
            make_item("Gemini breach hits three companies again",
                      "https://a.com/2", source="WIRED", minutes_ago=10),
        ])
        assert len(stories) == 1
        assert stories[0].also == []
        assert stories[0].corroboration == 1

    def test_what_the_head_already_carried_is_kept(self, make_item):
        """cluster() is run twice on the same data — once a day, once a week —
        so the second pass must add to `also`, never replace it."""
        head = make_item("Gemini breach hits three companies", "https://a.com/1",
                         source="WIRED", minutes_ago=60)
        head.also, head.also_urls = ["Ars Technica"], ["https://ars.com/1"]
        other = make_item("Gemini breach hits three companies today",
                          "https://b.com/2", source="The Verge", minutes_ago=10)
        stories = cluster([head, other])
        assert len(stories) == 1
        assert stories[0].also == ["Ars Technica", "The Verge"]
        assert stories[0].also_urls == ["https://ars.com/1", "https://b.com/2"]

    def test_a_singleton_keeps_its_corroboration_too(self, make_item):
        head = make_item("Alone", "https://a.com/1", source="WIRED")
        head.also, head.also_urls = ["Ars Technica"], ["https://ars.com/1"]
        assert cluster([head])[0].corroboration == 2

    def test_returns_newest_first(self, make_item):
        stories = cluster([
            make_item("Older unrelated story", minutes_ago=600),
            make_item("Newer different story", minutes_ago=5),
        ])
        assert stories[0].title == "Newer different story"

    def test_band_sits_below_the_certain_threshold(self):
        assert CLUSTER_BAND_LOW < CLUSTER_CERTAIN


class TestRegressions:
    """One test per defect the adversarial review demonstrated."""

    def test_wire_headline_from_several_outlets_counts_as_corroboration(self, make_item):
        """dedupe used to key on the title too, which discarded the other
        outlets before cluster() could count them — killing the corroboration
        signal exactly when it was strongest."""
        headline = "OpenAI signs chip supply deal with Broadcom"
        stories = cluster(dedupe([
            make_item(headline, "https://reuters.com/a", source="Reuters", minutes_ago=90),
            make_item(headline, "https://theverge.com/b", source="The Verge", minutes_ago=60),
            make_item(headline, "https://arstechnica.com/c", source="Ars Technica", minutes_ago=30),
        ]))
        assert len(stories) == 1
        assert stories[0].corroboration == 3
        assert stories[0].source == "Reuters"

    def test_non_latin_headlines_are_not_collapsed(self, make_item):
        """Every title with no ASCII word characters normalised to "", so they
        all shared one dedupe key and all but the first disappeared."""
        items = [
            make_item("Искусственный интеллект в России", "https://ria.ru/1"),
            make_item("人工知能の最新動向", "https://nikkei.com/2", minutes_ago=10),
            make_item("인공지능 반도체", "https://chosun.com/3", minutes_ago=20),
        ]
        assert len(dedupe(items)) == 3

    def test_malformed_url_does_not_abort_the_run(self, make_item):
        """urlsplit raises ValueError on an unbalanced bracket in the host."""
        assert canonical_url("https://foo]bar/a") == "https://foo]bar/a"
        assert canonical_url("https://[::1/a") == "https://[::1/a"
        kept = dedupe([
            make_item("Good story", "https://ok.com/1"),
            make_item("Bad link", "https://[::1/a", minutes_ago=5),
        ])
        assert len(kept) == 2

    def test_content_bearing_query_keys_survive(self):
        """?s= is a search term on WordPress, not a tracker; stripping it
        merged genuinely different pages."""
        a = canonical_url("https://blog.example/?s=kubernetes")
        b = canonical_url("https://blog.example/?s=terraform")
        assert a != b
        assert canonical_url("https://x.com/p?utm_source=rss&fbclid=z") == "https://x.com/p"
