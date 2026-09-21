import json
from datetime import datetime, timezone

import pytest

from newsbot.models import Item
from newsbot.store import Store, count_by_source, repo_root


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


class TestState:
    def test_missing_state_reads_as_empty(self, store):
        assert store.load_state() == {"covered": [], "last_report": None}

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
        day = datetime(2026, 9, 20, tzinfo=timezone.utc)
        store.record_covered(
            Item("Gemini went rogue at three companies",
                 "https://www.wired.com/gemini?utm_source=rss", "WIRED", day,
                 also=["Ars"], also_urls=["https://arstechnica.com/gemini/"]),
            "2026-w38", day)
        entry = store.load_state()["covered"][0]
        assert entry["url"] == "https://wired.com/gemini"
        assert entry["also_urls"] == ["https://arstechnica.com/gemini"]
        assert entry["title"] == "Gemini went rogue at three companies"
        assert entry["slug"] == "2026-w38"
        assert entry["date"] == "2026-09-20"
        assert store.load_state()["last_report"] == "2026-09-20"

    def test_several_stories_of_one_report_share_the_slug(self, store):
        """A report has six sections; keying on the slug would keep one."""
        day = datetime(2026, 9, 20, tzinfo=timezone.utc)
        store.record_covered(Item("A", "https://a.com/1", "X", day), "2026-w38", day)
        store.record_covered(Item("B", "https://b.com/1", "X", day), "2026-w38", day)
        assert [c["url"] for c in store.load_state()["covered"]] == \
            ["https://a.com/1", "https://b.com/1"]

    def test_rerunning_the_same_story_does_not_duplicate_it(self, store):
        day = datetime(2026, 9, 20, tzinfo=timezone.utc)
        store.record_covered(Item("A", "https://a.com/1", "X", day), "2026-w38", day)
        store.record_covered(Item("A", "https://a.com/1?utm_source=x", "X", day), "2026-w38", day)
        assert len(store.load_state()["covered"]) == 1

    def test_the_old_last_article_key_is_retired(self, store):
        store.save_state({"covered": [], "last_article": "2026-09-21"})
        day = datetime(2026, 9, 27, tzinfo=timezone.utc)
        store.record_covered(Item("A", "https://a.com/1", "X", day), "2026-w39", day)
        state = store.load_state()
        assert "last_article" not in state and state["last_report"] == "2026-09-27"


class TestLatestReport:
    def test_none_without_a_reports_directory(self, store):
        assert store.latest_report() is None

    def test_the_newest_week_wins_by_name(self, store):
        store.reports.mkdir()
        for name in ("2026-w40.md", "2026-w38.md", "2026-w39.md"):
            (store.reports / name).write_text("x", encoding="utf-8")
        assert store.latest_report().name == "2026-w40.md"


class TestCountBySource:
    def test_counts_items_per_source(self):
        day = datetime(2026, 9, 20, tzinfo=timezone.utc)
        items = [
            Item("A", "https://a.com/1", "WIRED", day),
            Item("B", "https://a.com/2", "WIRED", day),
            Item("C", "https://a.com/3", "The Verge", day),
        ]
        assert count_by_source(items) == {"WIRED": 2, "The Verge": 1}

    def test_empty_list_counts_nothing(self):
        assert count_by_source([]) == {}


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

    def test_archive_records_a_per_source_count_for_tracking_over_time(self, store):
        """Issue #15: measuring which feeds actually publish inside the
        window needs a per-feed count that persists past one run's log."""
        day = datetime(2026, 9, 20, tzinfo=timezone.utc)
        path = store.save_archive(day, [
            Item("A", "https://a.com/1", "WIRED", day),
            Item("B", "https://a.com/2", "WIRED", day),
            Item("C", "https://a.com/3", "The Verge", day),
        ], failures={})
        payload = json.loads(path.read_text())
        assert payload["per_source"] == {"WIRED": 2, "The Verge": 1}


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
            store.save_state({"covered": [], "last_report": None})
        assert list(store.work.glob("*.tmp")) == []
