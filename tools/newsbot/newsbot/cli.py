"""newsbot — command line entry point.

    newsbot probe              check every feed answers, print a table
    newsbot collect            fetch, dedupe, cluster, write _data/news.json
    newsbot collect --dry-run  same, but print instead of writing
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import sources as src
from .normalize import cluster, dedupe
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

    print(
        f"{len(items)} entries -> {len(fresh)} within {args.window}h "
        f"-> {len(distinct)} distinct -> {len(stories)} stories "
        f"({len(failures)} feeds failed)",
        file=sys.stderr,
    )

    if args.dry_run:
        for item in stories[: args.limit]:
            mark = f" +{len(item.also)}" if item.also else ""
            print(f"  {item.published:%b %d}  {item.title[:72]:72s} "
                  f"[{item.source}{mark}]")
        return 0

    # Archive the windowed, deduplicated set rather than every entry the
    # feeds returned: the full haul is ~2500 entries a day, mostly years-old
    # back catalogue from the lab blogs, and committing that daily would add
    # hundreds of megabytes a year to the repository for no benefit.
    store.save_archive(now, distinct, failures)
    store.save_home(stories, limit=args.limit)

    print(f"wrote {store.news_json.relative_to(store.root)} "
          f"and {store.archive_for(now).relative_to(store.root)}", file=sys.stderr)
    return 0


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
    collect.set_defaults(func=cmd_collect)

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
