"""newsbot — command line entry point.

    newsbot probe              check every feed answers, print a table
    newsbot collect            fetch, dedupe, cluster, score, archive the day
    newsbot collect --dry-run  same, but print instead of writing
    newsbot weekly             plan, draft, check and write the week's report
    newsbot weekly --dry-run   print the plan and stop before drafting
    newsbot eval               judge the labelled set and print the agreement
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import sources as src
from .models import Item
from .normalize import CLUSTER_BAND_LOW, CLUSTER_CERTAIN, cluster, dedupe
from .store import Store, count_by_source, repo_root

WINDOW_HOURS = 48
log = logging.getLogger(__name__)


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(message)s",
        stream=sys.stderr,
    )


def _say(msg: str) -> None:
    print(msg, file=sys.stderr)


def _have_jev() -> bool:
    return bool(os.environ.get("TYPESAFE_API_KEY"))


def _have_claude() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _say_usage() -> None:
    """One line per model that was asked anything this run."""
    from .judge import JEV
    if JEV.requests:
        _say(JEV.summary())
    try:
        from .recheck import HAIKU
    except ImportError:  # anthropic not installed: nothing was asked of it
        return
    if HAIKU.requests:
        _say(HAIKU.summary())


# --- probe ------------------------------------------------------------------

def cmd_probe(args: argparse.Namespace) -> int:
    store = Store(repo_root())
    feeds = src.load_sources(store.sources_yml)
    items, failures = src.collect(feeds)

    by_source: dict[str, int] = {}
    for item in items:
        by_source[item.source] = by_source.get(item.source, 0) + 1

    for feed in feeds:
        count = by_source.get(feed.name, 0)
        if feed.name in failures:
            print(f"DEAD  {feed.name:20s} {failures[feed.name]}")
        else:
            print(f"ok    {feed.name:20s} {count:4d} items")
    print(f"\n{len(feeds) - len(failures)}/{len(feeds)} feeds answered, "
          f"{len(items)} items total")
    return 1 if failures else 0


# --- collect ----------------------------------------------------------------

def _score(stories, args) -> tuple[list, dict]:
    """Judge the day's stories with Jev when a key is configured.

    Without TYPESAFE_API_KEY the day is still archived, unscored, and says so
    loudly: the weekly run will score whatever it finds unscored, so a missing
    key costs one run's worth of calls later rather than a week of silence.
    """
    if args.no_score or not _have_jev():
        if not args.no_score:
            _say("TYPESAFE_API_KEY not set: archiving the day unscored.")
        return stories, {}

    from .judge import as_record, resolve_band, score_all

    stories = resolve_band(stories, CLUSTER_BAND_LOW, CLUSTER_CERTAIN)
    assessed = score_all(stories)
    scores = {a.item.url: as_record(a) for a in assessed}

    gated = [a for a in assessed if a.gate]
    if gated:
        _say("  gated: " + ", ".join(sorted({a.gate for a in gated})) +
             f" ({len(gated)} stories)")
    errors = [a for a in assessed if a.error]
    if errors:
        _say(f"  {len(errors)} stories could not be scored")
    return stories, scores


def cmd_collect(args: argparse.Namespace) -> int:
    store = Store(repo_root())
    now = datetime.now(timezone.utc)

    feeds = src.load_sources(store.sources_yml)
    items, failures = src.collect(feeds)
    if not items:
        _say("no items collected from any feed; leaving the archive alone")
        return 1

    fresh = [i for i in items if i.published >= now - timedelta(hours=args.window)]
    distinct = dedupe(fresh)
    stories = cluster(distinct)

    # Per feed, how many of its entries actually fell inside the window —
    # not the raw fetch total `collect()` already logs per source. Also
    # written into the day's archive as `per_source`, so it survives the run.
    for name, count in sorted(count_by_source(distinct).items()):
        log.info("  %s: %d in window", name, count)

    stories, scores = _score(stories, args)

    _say(f"{len(items)} entries -> {len(fresh)} within {args.window}h "
         f"-> {len(distinct)} distinct -> {len(stories)} stories "
         f"({len(failures)} feeds failed)")

    _say_usage()

    if args.dry_run:
        ranked = sorted(stories, key=lambda i: -(scores.get(i.url, {}).get("score") or 0.0))
        for item in ranked:
            rec = scores.get(item.url, {})
            mark = f" x{item.corroboration}" if item.corroboration > 1 else ""
            score = rec.get("score")
            shown = f"{score:.3f}" if score is not None else "  -  "
            gate = f" [{rec['gate']}]" if rec.get("gate") else ""
            theme = f" {rec['theme']}" if rec.get("theme") else ""
            print(f"  {shown}  {item.published:%b %d}  {item.title[:60]:62s} "
                  f"[{item.source}{mark}]{theme}{gate}")
        return 0

    # Archive the windowed, deduplicated set rather than every entry the
    # feeds returned: the full haul is ~2500 entries a day, mostly years-old
    # back catalogue from the lab blogs, and committing that daily would add
    # hundreds of megabytes a year to the repository for no benefit.
    store.save_archive(now, distinct, failures, scores)
    _say(f"wrote {store.archive_for(now).relative_to(store.root)}")
    return 0


# --- weekly -----------------------------------------------------------------

def _backfill(stories):
    """Score, now, whatever the daily runs left unscored under this rubric."""
    from . import weekly

    todo = weekly.unscored(stories)
    if not todo:
        return 0
    if not _have_jev():
        _say(f"{len(todo)} stories carry no judgement under the current rubric "
             f"and TYPESAFE_API_KEY is not set; they cannot be selected.")
        return 0

    from .judge import as_record, score_all

    assessed = score_all([s.item for s in todo])
    by_url = {a.item.url: as_record(a) for a in assessed if not a.error}
    for s in todo:
        if s.item.url in by_url:
            s.judgement = by_url[s.item.url]
    failed = len(assessed) - len(by_url)
    _say(f"scored {len(by_url)} stories the archives had not judged under the "
         f"current rubric" + (f"; {failed} could not be scored" if failed else ""))
    return len(by_url)


def _print_plan(selection, now) -> None:
    from . import weekly

    _say("\ntheme count (this week / last week):")
    for _, display, now_c, then_c in selection.table:
        last = str(then_c) if then_c is not None else "-"
        _say(f"  {display:26s} {now_c:2d} / {last}")

    _say("\nsections:")
    for s in selection.sections:
        _say(f"  {weekly.trend(s, now):.3f}  {s.item.title[:60]:62s} "
             f"[{s.item.source} x{s.outlets}] {s.theme} "
             f"days={len(s.days_seen)} acc={float(s.judgement.get('accessibility', 0)):.1f}")
    _say("\nalso this week:")
    for s in selection.also:
        _say(f"  {weekly.trend(s, now):.3f}  {s.item.title[:60]:62s} "
             f"[{s.item.source}] {s.theme}")
    if selection.rejected:
        _say("\nrejected:")
        for s, why in selection.rejected[:15]:
            _say(f"  {s.score:.3f}  {s.item.title[:56]:58s} {'; '.join(why)}")


def cmd_weekly(args: argparse.Namespace) -> int:
    """The week's report: merge, rank, select, fetch, draft, check, render."""
    from . import fetch, render, verify, weekly, write

    store = Store(repo_root())
    now = datetime.now(timezone.utc)
    week_id, period, start, end = weekly.week_of(now, args.days)
    _say(f"report {week_id}: {period}")

    entries = list(weekly.load_archives(store.archive, now, days=args.days))
    if not entries:
        _say(f"no archives covering {period} — run collect first")
        return 1

    resolve = None
    if _have_jev():
        from .judge import resolve_band
        resolve = lambda items: resolve_band(items, CLUSTER_BAND_LOW, CLUSTER_CERTAIN)
    stories = weekly.merge(entries, resolve=resolve)
    # Windowed on the days the title names, not on the last seven days from
    # now: the two differ on every weekday, and a manual mid-week run put
    # stories from after the labelled week into it.
    current = weekly.in_week(stories, start, end)
    previous = weekly.week_before(stories, start, days=args.days)
    _say(f"{len(entries)} archive entries -> {len(stories)} stories, "
         f"{len(current)} this week, {len(previous)} last week")

    _backfill(current)

    covered = store.load_state().get("covered", [])
    # What the blog has already put out — articles and earlier reports. The
    # week's own file is skipped, so a second run for the same week does not
    # read what the first one wrote and find all its stories already covered.
    published = weekly.published_coverage(store.root, skip=week_id)
    _say(f"already published: {len(published[0])} cited links, "
         f"{len(published[1])} titles")
    if _have_jev():
        # A rewritten headline scores below the overlap threshold even when
        # it reports the same event, so the band is put to Jev, exactly as
        # the daily clustering does. The URLs it returns join the cited ones.
        from .judge import same_story
        matched = weekly.already_published(current, published[1], same_story)
        if matched:
            _say(f"{len(matched)} stories Jev says the blog already reported")
            published = (published[0] | matched, published[1])
    exclude: set[str] = set()
    texts: dict[str, dict[str, str]] = {}
    selection = None
    for _ in range(4):
        selection = weekly.select(current, now, covered=covered, previous=previous,
                                  sections=args.stories, exclude=frozenset(exclude),
                                  published=published)
        if args.dry_run:
            break
        missing = []
        for s in selection.sections:
            if s.item.url in texts:
                continue
            # The representative plus the other write-ups of the SAME story,
            # by URL — never by outlet name, which would pull in everything
            # that outlet published this week.
            wanted = [Item(title=s.item.title, url=u, source=s.item.source,
                           published=s.item.published) for u in s.source_urls]
            got = fetch.fetch_sources(wanted)
            if got:
                texts[s.item.url] = got
            else:
                missing.append(s)
        if not missing:
            break
        for s in missing:
            _say(f"no source could be fetched for: {s.item.title[:70]}")
            exclude.add(s.item.url)

    if not args.dry_run:
        # Four rounds is plenty; whatever still has no text is dropped rather
        # than written from its headline.
        selection.sections = [s for s in selection.sections if s.item.url in texts]

    _print_plan(selection, now)
    if selection.quiet:
        _say(f"\nonly {len(selection.sections)} stories cleared the bar "
             f"(fewer than {weekly.MIN_SECTIONS}); publishing nothing this week.")
        return 2
    if args.dry_run:
        return 0

    brief = write.Brief(
        week_id=week_id, period=period,
        sections=[(s, texts[s.item.url]) for s in selection.sections],
        also=selection.also, table=selection.table,
    )
    guide = (store.root / "tools" / "newsbot" / "style.md").read_text(encoding="utf-8")
    previous_report = store.latest_report()
    voice = previous_report.read_text(encoding="utf-8")[:9000] if previous_report else None

    draft = write.draft(brief, guide, previous=voice)
    if draft.refused:
        _say(f"the model declined this week ({draft.refusal_reason}); nothing written.")
        return 4
    _say(f"drafted {len(draft.markdown.split())} words, "
         f"{draft.input_tokens} in / {draft.output_tokens} out, ${draft.cost_usd:.3f}")

    report = render.parse_draft(draft.markdown)

    # The checker reads exactly what the writer read: the fetched articles
    # for the sections, the headline plus feed summary for the also-list, and
    # the theme counts, which are the Trends section's only source of fact
    # and come from this pipeline rather than from any article.
    checkable = {url: text for texts_ in texts.values() for url, text in texts_.items()}
    for s in selection.also:
        checkable[s.item.url] = f"{s.item.title}\n\n{s.item.summary}"
    checkable[THEME_COUNTS] = _theme_counts_text(selection.table)
    # Each story section is read against the sources it was written from,
    # in the order the writer was given them; the also-list against its
    # items' headline and summary; the overview against everything.
    section_urls = [list(texts[s.item.url]) for s in selection.sections]
    also_urls = [s.item.url for s in selection.also]
    # What Jev cannot place is re-read by Claude Haiku, which has to quote
    # the passage it found. Without a key the Jev pass stands alone.
    recheck_hook = None
    if not args.no_recheck and _have_claude():
        from .recheck import second_opinions
        recheck_hook = second_opinions
    # The parsed body, not the raw draft: the TITLE and DESCRIPTION lines are
    # instructions to this pipeline, and checking them against a news article
    # reported the description itself as an unsupported claim.
    checks = (verify.Report() if args.no_verify
              else verify.verify(report.body, checkable, sections=section_urls,
                                 also=also_urls, recheck=recheck_hook))
    if checks.error:
        _say(f"citation check unavailable: {checks.error}")
    else:
        _say(f"checked {checks.checked} claims, {len(checks.unsupported)} unsupported"
             + (f" ({len(checks.reconsidered)} more flagged by Jev were found by the "
                f"second reader)" if checks.reconsidered else "")
             + f", {len(checks.synthesis)} of the overview unmatched")
    _say_usage()

    out_root = Path(args.out) if args.out else store.root
    judge_models = {s.judgement.get("model") for s in selection.sections}
    path = render.write_report(
        out_root, report, now, week_id, period, _model_name(draft.model),
        checks.checked, len(checks.unsupported), rows=selection.table,
        judge_model=judge_models.pop() if len(judge_models) == 1 else None,
        verify_model=checks.model,
        recheck_model=_model_name(checks.recheck_model) if checks.recheck_model else None,
        reconsidered=len(checks.reconsidered))
    _say(f"wrote {path}")

    # Only when the report lands in the site itself. `--out` is a preview,
    # and marking stories as covered on a preview would silently cost the
    # following week its sections on them.
    if out_root == store.root:
        for s in selection.sections:
            store.record_covered(s.item, week_id, now)
        _say(f"recorded {len(selection.sections)} stories in "
             f"{store.state_json.relative_to(store.root)}")
    else:
        _say("--out: preview only, nothing was marked as covered")

    if checks.unsupported:
        _say("\nclaims the sources do not bear out:")
        for f in checks.unsupported[:12]:
            _say(f"  [{f.best_support:.2f}] {f.sentence[:100]}")
            if f.second is not None and (f.second.note or f.second.error):
                _say(f"         second reader: {f.second.error or f.second.note}")

    if checks.reconsidered:
        _say("\nflagged by Jev, found in the sources by the second reader:")
        for f in checks.reconsidered[:12]:
            _say(f"  [{f.best_support:.2f}] {f.sentence[:100]}")
            _say(f"         “{f.second.excerpt[:100]}” — {f.second.source}")

    if checks.synthesis:
        _say("\nopening and Trends, drawing on the week rather than on one "
             "source — read, do not treat as findings:")
        for f in checks.synthesis[:8]:
            _say(f"  [{f.best_support:.2f}] {f.sentence[:100]}")

    if args.checks_out:
        # A machine-readable sibling of the log above, so the workflow can
        # build the PR's review checklist without scraping stderr.
        payload = {
            "week": week_id,
            "checked": checks.checked,
            "unsupported": [
                {"sentence": f.sentence, "support": round(f.best_support, 3),
                 "source": f.best_source,
                 "note": (f.second.error or f.second.note) if f.second else None}
                for f in checks.unsupported
            ],
            "reconsidered": [
                {"sentence": f.sentence, "support": round(f.best_support, 3),
                 "source": f.second.source, "excerpt": f.second.excerpt,
                 "note": f.second.note}
                for f in checks.reconsidered
            ],
            "synthesis": [
                {"sentence": f.sentence, "support": round(f.best_support, 3),
                 "source": f.best_source}
                for f in checks.synthesis
            ],
            "sections": [s.item.title for s in selection.sections],
            "post": str(path),
        }
        Path(args.checks_out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _say(f"wrote {args.checks_out}")
    return 0


# The key the theme counts are filed under in the checker's sources. Not a
# URL: it is this pipeline's own arithmetic, and it is shown as its own line
# in the report rather than linked.
THEME_COUNTS = "the week's theme counts, computed by the pipeline"


def _theme_counts_text(rows) -> str:
    lines = ["The number of stories collected this week under each theme, "
             "and under the same theme the week before."]
    for _, display, now_c, then_c in rows:
        last = f"{then_c} last week" if then_c is not None else "no count for last week"
        lines.append(f"{display}: {now_c} stories this week, {last}.")
    return "\n".join(lines)


def _model_name(model_id: str) -> str:
    """The name the disclosure prints for a Claude model id the API returned."""
    for prefix, name in (("claude-opus-5", "Claude Opus 5"),
                         ("claude-haiku-4-5", "Claude Haiku 4.5")):
        if model_id.startswith(prefix):
            return name
    return model_id


# --- eval -------------------------------------------------------------------

def cmd_eval(args: argparse.Namespace) -> int:
    from . import evaluate

    if not _have_jev():
        _say("TYPESAFE_API_KEY is not set; nothing can be judged.")
        return 1
    path = Path(args.set) if args.set else (
        repo_root() / "tools" / "newsbot" / "eval" / "headlines.jsonl")
    labelled = evaluate.load_set(path)
    _say(f"{len(labelled)} labelled items from {path}")

    from .judge import RUBRIC, score_all

    summary = evaluate.run(labelled, score_all)
    print(f"rubric {RUBRIC}\n" + evaluate.report(summary))
    _say_usage()
    if args.json:
        Path(args.json).write_text(
            json.dumps({"rubric": RUBRIC, **summary.as_dict()}, indent=2,
                       ensure_ascii=False) + "\n", encoding="utf-8")
        _say(f"wrote {args.json}")
    if args.min_agreement is not None:
        low = summary.below(args.min_agreement)
        if low:
            _say(f"under {args.min_agreement:.0%}: {', '.join(low)}")
            return 1
    return 0


# --- entry point ------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="newsbot", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("probe", help="check every feed answers").set_defaults(
        func=cmd_probe
    )

    collect = sub.add_parser("collect", help="fetch, score and archive the day")
    collect.add_argument("--window", type=int, default=WINDOW_HOURS,
                         help="how many hours back to keep (default: 48)")
    collect.add_argument("--dry-run", action="store_true",
                         help="print the result instead of writing it")
    collect.add_argument("--no-score", action="store_true",
                         help="skip Jev and archive the day unscored")
    collect.set_defaults(func=cmd_collect)

    weekly = sub.add_parser("weekly", help="write the week's report")
    weekly.add_argument("--days", type=int, default=7,
                        help="how far back the week reaches (default: 7)")
    weekly.add_argument("--stories", type=int, default=6,
                        help="how many stories get a section (default: 6)")
    weekly.add_argument("--dry-run", action="store_true",
                        help="print the plan and stop before drafting")
    weekly.add_argument("--out", help="write the report under this root instead")
    weekly.add_argument("--no-verify", action="store_true",
                        help="skip the Jev citation check")
    weekly.add_argument("--checks-out",
                        help="also write the citation check as JSON to this path")
    weekly.add_argument("--no-recheck", action="store_true",
                        help="skip the Claude Haiku second reading of what Jev flagged")
    weekly.set_defaults(func=cmd_weekly)

    ev = sub.add_parser("eval", help="judge the labelled set and print the agreement")
    ev.add_argument("--set", help="JSONL file (default: tools/newsbot/eval/headlines.jsonl)")
    ev.add_argument("--json", help="also write the tally as JSON to this path")
    ev.add_argument("--min-agreement", type=float,
                    help="exit 1 if any question's agreement is under this rate")
    ev.set_defaults(func=cmd_eval)

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
