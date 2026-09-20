"""newsbot — command line entry point.

    newsbot probe              check every feed answers, print a table
    newsbot collect            fetch, dedupe, cluster, write _data/news.json
    newsbot collect --dry-run  same, but print instead of writing
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import sources as src
from .normalize import CLUSTER_BAND_LOW, CLUSTER_CERTAIN, cluster, dedupe
from .store import Store, repo_root

WINDOW_HOURS = 48


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(message)s",
        stream=sys.stderr,
    )


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


def _rank(stories, now, args):
    """Order the day's stories, with Jev when a key is configured.

    Without TYPESAFE_API_KEY the collection still publishes, newest first —
    a home page of unranked headlines beats no home page — but it says so
    loudly, because that is the state the whole pipeline exists to improve on.
    """
    if args.no_rank or not os.environ.get("TYPESAFE_API_KEY"):
        if not args.no_rank:
            print("TYPESAFE_API_KEY not set: publishing unranked, newest first.",
                  file=sys.stderr)
        return stories, {}

    from .judge import rank, resolve_band, score_all

    stories = resolve_band(stories, CLUSTER_BAND_LOW, CLUSTER_CERTAIN)
    assessed = score_all(stories)

    scores = {
        a.item.url: {
            "score": round(a.score, 4),
            "gate": a.gate,
            "flags": a.flags,
            **a.detail,
            **({"error": a.error} if a.error else {}),
        }
        for a in assessed
    }
    gated = [a for a in assessed if a.gate]
    if gated:
        print(f"  gated: " + ", ".join(sorted({a.gate for a in gated})) +
              f" ({len(gated)} stories)", file=sys.stderr)
    errors = [a for a in assessed if a.error]
    if errors:
        print(f"  {len(errors)} stories could not be scored", file=sys.stderr)

    return [a.item for a in rank(assessed, now, limit=args.limit)], scores


def cmd_collect(args: argparse.Namespace) -> int:
    store = Store(repo_root())
    now = datetime.now(timezone.utc)

    feeds = src.load_sources(store.sources_yml)
    items, failures = src.collect(feeds)
    if not items:
        print("no items collected from any feed; leaving news.json alone",
              file=sys.stderr)
        return 1

    fresh = [i for i in items if i.published >= now - timedelta(hours=args.window)]
    distinct = dedupe(fresh)
    stories = cluster(distinct)

    ranked, scores = _rank(stories, now, args)

    print(
        f"{len(items)} entries -> {len(fresh)} within {args.window}h "
        f"-> {len(distinct)} distinct -> {len(stories)} stories "
        f"-> {len(ranked)} published ({len(failures)} feeds failed)",
        file=sys.stderr,
    )

    if args.dry_run:
        for item in ranked[: args.limit]:
            mark = f" x{item.corroboration}" if item.corroboration > 1 else ""
            score = scores.get(item.url, {}).get("score")
            shown = f"{score:.3f}" if score is not None else "  -  "
            print(f"  {shown}  {item.published:%b %d}  {item.title[:64]:66s} "
                  f"[{item.source}{mark}]")
        return 0

    # Archive the windowed, deduplicated set rather than every entry the
    # feeds returned: the full haul is ~2500 entries a day, mostly years-old
    # back catalogue from the lab blogs, and committing that daily would add
    # hundreds of megabytes a year to the repository for no benefit.
    store.save_archive(now, distinct, failures, scores)
    store.save_home(ranked, limit=args.limit)

    print(f"wrote {store.news_json.relative_to(store.root)} "
          f"and {store.archive_for(now).relative_to(store.root)}", file=sys.stderr)
    return 0


def cmd_article(args: argparse.Namespace) -> int:
    """Draft the week's article: pick, fetch, write, check, render."""
    from . import fetch, pick, render, verify, write

    store = Store(repo_root())
    now = datetime.now(timezone.utc)

    candidates = pick.load_week(store.archive, now, days=args.days)
    if not candidates:
        print(f"no scored stories in the last {args.days} days — run collect first",
              file=sys.stderr)
        return 1

    winner, report, strict = pick.choose(candidates, store.root / "_posts",
                                         index=args.candidate)
    if winner is None:
        print("nothing cleared the bar, even relaxed; publishing nothing this week.",
              file=sys.stderr)
        _print_report(report)
        return 2

    bar = "the weekly bar" if strict else "the relaxed fallback bar"
    print(f"subject ({bar}): {winner.item.title}  [{winner.item.source}] "
          f"score {winner.score:.3f} x{winner.item.corroboration}", file=sys.stderr)

    # The winner plus the other write-ups of the SAME story. Matching on the
    # outlet name instead would pull in every article that outlet published
    # this week — six unrelated pieces, in the case this was caught on — and
    # hand them to the model as material on the subject.
    wanted = set(winner.item.also_urls)
    cluster = [winner.item] + [c.item for c in candidates
                               if c.item.url in wanted]
    sources = fetch.fetch_sources(cluster)
    print(f"fetched {len(sources)}/{len(cluster)} source articles", file=sys.stderr)
    if not sources:
        print("no source article could be fetched; refusing to write from the "
              "headline alone.", file=sys.stderr)
        return 3

    guide, examples = write.load_style(store.root)
    draft = write.draft(winner.item, sources, cluster[1:], guide, examples)
    if draft.refused:
        print(f"the model declined this subject ({draft.refusal_reason}); "
              f"nothing written.", file=sys.stderr)
        return 4
    print(f"drafted {len(draft.markdown.split())} words, "
          f"{draft.input_tokens} in / {draft.output_tokens} out, "
          f"${draft.cost_usd:.3f}", file=sys.stderr)

    checks = verify.Report() if args.no_verify else verify.verify(draft.markdown, sources)
    if checks.error:
        print(f"citation check unavailable: {checks.error}", file=sys.stderr)
    else:
        print(f"checked {checks.checked} claims, "
              f"{len(checks.unsupported)} unsupported", file=sys.stderr)

    post = render.parse_draft(draft.markdown)
    out_root = Path(args.out) if args.out else store.root
    path = render.write_post(out_root, post, datetime.now(timezone.utc),
                             _model_name(draft.model), checks.checked,
                             len(checks.unsupported))
    print(f"wrote {path}", file=sys.stderr)

    if checks.unsupported:
        print("\nclaims the sources do not bear out:", file=sys.stderr)
        for f in checks.unsupported[:12]:
            print(f"  [{f.best_support:.2f}] {f.sentence[:100]}", file=sys.stderr)
    return 0


def _model_name(model_id: str) -> str:
    return {"claude-opus-5": "Claude Opus 5"}.get(model_id, model_id)


def _print_report(report: list[dict]) -> None:
    for row in report[:12]:
        print(f"  {row['score']:.3f}  {row['title'][:56]:58s} "
              f"{'; '.join(row['rejected_for'])}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="newsbot", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("probe", help="check every feed answers").set_defaults(
        func=cmd_probe
    )

    collect = sub.add_parser("collect", help="fetch and write the home list")
    collect.add_argument("--window", type=int, default=WINDOW_HOURS,
                         help="how many hours back to keep (default: 48)")
    collect.add_argument("--limit", type=int, default=15,
                         help="how many stories to publish (default: 15)")
    collect.add_argument("--dry-run", action="store_true",
                         help="print the result instead of writing it")
    collect.add_argument("--no-rank", action="store_true",
                         help="skip Jev and publish newest first")
    collect.set_defaults(func=cmd_collect)

    article = sub.add_parser("article", help="draft the week's article")
    article.add_argument("--days", type=int, default=7,
                         help="how far back to look for a subject (default: 7)")
    article.add_argument("--candidate", type=int, default=0,
                         help="take the Nth eligible subject instead of the first")
    article.add_argument("--out", help="write the post under this root instead")
    article.add_argument("--no-verify", action="store_true",
                         help="skip the Jev citation check")
    article.set_defaults(func=cmd_article)

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
