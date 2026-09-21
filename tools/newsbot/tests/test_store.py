import json
from datetime import datetime, timezone

import pytest

from newsbot.models import Item
from newsbot.store import Store, repo_root


@pytest.fixture
def store(tmp_path):
    (tmp_path / "_config.yml").write_text("title: test\n")
    return Store(tmp_path)


class TestRepoRoot:
    def test_finds_the_directory_holding_config(self, tmp_path):
        (tmp_path / "_config.yml").write_text("title: test\n")
        deep = tmp_path / "tools" / "newsbot" / "newsbot"
        deep.mkdir(parents=True)
        assert repo_root(deep / "store.py") == tmp_path.resolve()

    def test_raises_outside_the_site(self, tmp_path):
        with pytest.raises(RuntimeError, match="_config.yml"):
            repo_root(tmp_path / "nowhere" / "file.py")


class TestSaveHome:
    def test_writes_only_the_fields_the_template_uses(self, store):
        store.save_home([
            Item("A headline", "https://a.com/1", "WIRED",
                 datetime(2026, 9, 20, tzinfo=timezone.utc), summary="ignored")
        ])
        payload = json.loads(store.news_json.read_text())
        assert set(payload["items"][0]) == {
            "title", "url", "source", "date", "corroboration"
        }
        assert "summary" not in payload["items"][0]

    def test_respects_the_limit(self, store):
        items = [
            Item(f"Story {n}", f"https://a.com/{n}", "X",
                 datetime(2026, 9, 20, tzinfo=timezone.utc))
            for n in range(40)
        ]
        store.save_home(items, limit=15)
        assert len(json.loads(store.news_json.read_text())["items"]) == 15

    def test_output_is_valid_json_jekyll_can_read(self, store):
        store.save_home([
            Item("Curly ’quotes’ and émojis 🤖", "https://a.com/1", "X",
                 datetime(2026, 9, 20, tzinfo=timezone.utc))
        ])
        payload = json.loads(store.news_json.read_text())
        assert payload["items"][0]["title"].endswith("🤖")

    def test_leaves_no_temporary_file_behind(self, store):
        store.save_home([
            Item("A", "https://a.com/1", "X",
                 datetime(2026, 9, 20, tzinfo=timezone.utc))
        ])
        assert list(store.data.glob("*.tmp")) == []


class TestState:
    def test_missing_state_reads_as_empty(self, store):
        assert store.load_state() == {"covered": [], "last_article": None}

    def test_covered_topics_round_trip(self, store):
        store.save_state({
            "covered": [{"slug": "gemini-breach", "date": "2026-09-20"}],
            "last_article": "2026-09-20",
        })
        state = store.load_state()
        assert state["covered"][0]["slug"] == "gemini-breach"
        assert state["last_article"] == "2026-09-20"


class TestRecordCovered:
    def test_the_url_also_urls_slug_and_date_are_all_written(self, store):
        day = datetime(2026, 9, 21, tzinfo=timezone.utc)
        store.record_covered(
            Item("Gemini went rogue at three companies",
                 "https://www.wired.com/gemini?utm_source=rss", "WIRED", day,
                 also=["Ars"], also_urls=["https://arstechnica.com/gemini/"]),
            "when-the-model-stopped", day)
        entry = store.load_state()["covered"][0]
        assert entry["url"] == "https://wired.com/gemini"
        assert entry["also_urls"] == ["https://arstechnica.com/gemini"]
        assert entry["title"] == "Gemini went rogue at three companies"
        assert entry["slug"] == "when-the-model-stopped"
        assert entry["date"] == "2026-09-21"
        assert store.load_state()["last_article"] == "2026-09-21"

    def test_a_second_article_is_appended_not_replaced(self, store):
        day = datetime(2026, 9, 21, tzinfo=timezone.utc)
        store.record_covered(Item("A", "https://a.com/1", "X", day), "a", day)
        store.record_covered(Item("B", "https://b.com/1", "X", day), "b", day)
        assert [c["slug"] for c in store.load_state()["covered"]] == ["a", "b"]

    def test_rerunning_the_same_slug_does_not_duplicate_it(self, store):
        """--candidate reruns of the same subject are a normal Sunday."""
        day = datetime(2026, 9, 21, tzinfo=timezone.utc)
        store.record_covered(Item("A", "https://a.com/1", "X", day), "a", day)
        store.record_covered(Item("A", "https://a.com/1", "X", day), "a", day)
        assert len(store.load_state()["covered"]) == 1


class TestArchive:
    def test_archive_is_written_outside_data(self, store):
        day = datetime(2026, 9, 20, tzinfo=timezone.utc)
        path = store.save_archive(day, [
            Item("A", "https://a.com/1", "X", day, summary="kept here")
        ], failures={"Dead Feed": "HTTPError: 500"})
        assert path.name == "2026-09-20.json"
        assert ".newsbot" in str(path)
        assert "_data" not in str(path)
        payload = json.loads(path.read_text())
        assert payload["failures"] == {"Dead Feed": "HTTPError: 500"}
        assert payload["items"][0]["summary"] == "kept here"


class TestRegressions:
    def test_repo_root_is_found_from_the_working_directory(self, tmp_path, monkeypatch):
        """The workflow installs the package non-editably, so __file__ lives in
        site-packages and walking up from it never reaches the site."""
        site = tmp_path / "site"
        (site / "deep" / "nested").mkdir(parents=True)
        (site / "_config.yml").write_text("title: t\n")
        monkeypatch.chdir(site / "deep" / "nested")
        assert repo_root() == site.resolve()

    def test_newsbot_root_env_var_overrides(self, tmp_path, monkeypatch):
        site = tmp_path / "site"
        site.mkdir()
        (site / "_config.yml").write_text("title: t\n")
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        monkeypatch.setenv("NEWSBOT_ROOT", str(site))
        assert repo_root() == site.resolve()

    def test_error_names_the_directory_it_searched(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("NEWSBOT_ROOT", raising=False)
        with pytest.raises(RuntimeError, match="NEWSBOT_ROOT"):
            repo_root()

    def test_no_temp_file_left_when_the_write_fails(self, store, monkeypatch):
        import pathlib

        def boom(self, target):
            raise OSError("disk full")

        monkeypatch.setattr(pathlib.Path, "replace", boom)
        with pytest.raises(OSError):
            store.save_home([
                Item("A", "https://a.com/1", "X",
                     datetime(2026, 9, 20, tzinfo=timezone.utc))
            ])
        assert list(store.data.glob("*.tmp")) == []
