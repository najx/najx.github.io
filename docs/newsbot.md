# newsbot

Collects AI headlines every morning and publishes a short list to the home
page. Lives in [`tools/newsbot`](../tools/newsbot); driven by
[`.github/workflows/ai-news-collect.yml`](../.github/workflows/ai-news-collect.yml).

## What runs, and when

| when | what | writes |
|---|---|---|
| daily, 05:17 UTC | fetch every feed, window, deduplicate, cluster | `_data/news.json`, `.newsbot/archive/<date>.json` |

The home page renders `_data/news.json` at build time. There is no
client-side fetch: no CORS to satisfy, no empty section when a feed is down,
and nothing to load before the page paints. If the file is missing the
`/ai-news` section simply does not render.

## Where things live

```
_data/news-sources.yml       the feed list — the one file you edit by hand
_data/news.json              the ~15 stories the home page shows
.newsbot/archive/<date>.json the day's distinct stories, summaries included
.newsbot/state.json          which stories already became an article
```

`.newsbot/` starts with a dot, so Jekyll ignores it. That matters: Jekyll
reads *every* file under `_data/` on *every* build, so a year of daily
archives there would be paid for on each rebuild.

## Adding a source

Append to `_data/news-sources.yml`:

```yaml
  - name: Example Lab
    url: https://example.com/blog/rss.xml
```

`name` is what shows in the tag on the right of each headline, so keep it
short. Then check it actually answers:

```bash
newsbot probe
```

A source with no feed goes in with `enabled: false` and a `note` saying why,
so the gap stays visible rather than being silently dropped. Anthropic and
Mistral are both in that state today — neither publishes RSS, and they are
the reason the Apify adapter exists.

## Running it by hand

```bash
pip install ./tools/newsbot
newsbot probe                      # does every feed still answer?
newsbot -v collect --dry-run       # print what would be published
newsbot -v collect                 # write _data/news.json
```

`--window` changes how far back to look (48 hours by default) and `--limit`
how many stories reach the home page (15).

The workflow also takes both as `workflow_dispatch` inputs, plus a `dry_run`
checkbox that prints the result without committing.

## Design notes

**Feeds, not scraping.** Every enabled source publishes RSS or Atom. Nothing
to keep working when a site reskins, no anti-bot to get around, no question
about terms of use, and no cost.

**Dates and counting stay in code.** Jev is documented as unreliable at
comparing dates and at counting, so the freshness window and the
corroboration count are computed here, exactly, and never asked of a model.

**Clustering is deliberately blunt.** Two headlines merge when their
significant words overlap by 60% or more. Measured against a real 48-hour
window, only two of 903 headline pairs scored above 0.20 — outlets rewrite
headlines enough that lexical overlap alone under-clusters. Pairs in the
0.20–0.60 band are the ones worth a Jev question; below it, misses are
accepted. The thresholds are `CLUSTER_BAND_LOW` and `CLUSTER_CERTAIN` in
`normalize.py`.

**Only the representative is published.** When several outlets carry the
same story, the earliest publication is the one linked, and the others are
recorded in `also` — that count is the corroboration signal the weekly
article ranks on.

**A feed that fails does not fail the run.** Failures are collected, logged,
and written into the day's archive, so a source going dark shows up in the
job log instead of quietly shrinking the list.

**`_data/news.json` is written through a temporary file** and parsed before
being moved into place. A malformed file there would fail the Jekyll build
and take the site down — too steep a price for a feed hiccup.

## Required secrets

| secret | why |
|---|---|
| `NEWSBOT_TOKEN` | fine-grained PAT, Contents: read and write. A commit pushed with the default `GITHUB_TOKEN` does **not** trigger other workflows, so `jekyll.yml` would never rebuild and the home page would keep showing yesterday's headlines. |

The workflow checks for it first and fails with that explanation rather than
running and silently publishing nothing.
