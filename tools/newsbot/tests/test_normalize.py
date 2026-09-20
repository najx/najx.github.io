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

    def test_identical_headline_different_url_kept_once(self, make_item):
        items = [
            make_item("Same headline", "https://a.com/1"),
            make_item("Same headline", "https://b.com/2", minutes_ago=5),
        ]
        assert len(dedupe(items)) == 1

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

    def test_returns_newest_first(self, make_item):
        stories = cluster([
            make_item("Older unrelated story", minutes_ago=600),
            make_item("Newer different story", minutes_ago=5),
        ])
        assert stories[0].title == "Newer different story"

    def test_band_sits_below_the_certain_threshold(self):
        assert CLUSTER_BAND_LOW < CLUSTER_CERTAIN
