# newsbot

Collects AI headlines every morning and publishes a short list to the home
page. Lives in [`tools/newsbot`](../tools/newsbot); driven by
[`.github/workflows/ai-news-collect.yml`](../.github/workflows/ai-news-collect.yml).

## What runs, and when

| when | what | writes |
|---|---|---|
| daily, 05:17 UTC | fetch every feed, window, deduplicate, cluster, rank with Jev | `_data/news.json`, `.newsbot/archive/<date>.json` |

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
job log instead of quietly shrinking the list. The same applies to a single
malformed link: `canonical_url` hands back anything `urlsplit` rejects rather
than raising.

**Deduplication keys on the canonical URL alone, never the title.** Two
outlets running the same wire headline are two documents, and collapsing them
here would destroy the corroboration that `cluster()` exists to count —
precisely when corroboration is strongest. It would also have collapsed every
non-Latin headline onto one key, since they normalise to the empty string.

**Nothing published is trusted.** Titles and links come off the open web. The
home template escapes every interpolation and renders a link only for
`http://` and `https://` URLs; feed text is decoded to a fixed point and then
stripped of markup, in that order, so doubly-encoded input cannot reappear as
tags after the strip.

**`newsbot` finds the site from the working directory**, not from where its
code lives, because the workflow installs the package non-editably. Set
`NEWSBOT_ROOT` to run it from elsewhere.

**`_data/news.json` is written through a temporary file** and parsed before
being moved into place. A malformed file there would fail the Jekyll build
and take the site down — too steep a price for a feed hiccup.

## Ranking with Jev

Seven questions about one story, batched into a single request. The rubrics
are long on purpose: *Literal Reading* is the first failure mode TypeSafe
documents — Jev answers the question you wrote, not the one you meant — so
each level spells out its boundary cases rather than trusting a short phrase.

| question | type | what it decides |
|---|---|---|
| `domain_fit` | Score 0-4 | how close the subject is to the blog's five beats |
| `story_type` | Choice | incident, engineering report, research, release, feature, essay, policy, digest, notice |
| `mechanism_depth` | Score 0-4 | how much machinery the text actually hands an author |
| `practitioner_stakes` | Score 0-3 | whether a reader would go and check their own systems |
| `is_promo_or_admin` | Noul | event, hire, call for papers, housekeeping |
| `state_is_informative` | Noul | do the fields say enough to know what this is about |
| `injection_present` | Noul | is the text addressing whatever reads it |

Three hard gates, each reading its own question against its own threshold —
the *Structural Invariants* warning says a Noul probability and a Score
position are not comparable, so they never meet in one inequality. Then a
weighted merit, a soft confidence gate, and a ceiling from
`state_is_informative`. Every weight lives in `judge.py`, not in a rubric:
changing a weight changes what we do with an answer, changing a criterion
changes what Jev is asked.

`domain_fit` is read as an expectation over its **probability distribution**,
not from `.score`. The Score guide says neighbouring levels are not assumed
adjacent, so a weighted position is meaningless when the mass splits between
level 0 and level 4 — which is exactly what an ambiguous headline produces.

A `same_story` Noul settles the clustering band: pairs from different outlets
whose headlines overlap between 0.20 and 0.60. Two such pairs came up in a
real day, one of which was the same Gemini break-in written up twice, taking
two of the top three slots.

**Measured on the day's real corpus**: all eight noise items the unranked list
was publishing are gated; the Gemini break-in and the nuclear-hallucination
story land first and fifth. Without `TYPESAFE_API_KEY` the collection still
publishes, newest first, and says so in the log.

### Tuning

`PUBLISH_FLOOR` (0.12) decides how thin a thin day is allowed to be — on the
corpus above it let 7 of 28 stories through. `MAX_PER_SOURCE` (2) stops one
outlet taking the page. Slots are never back-filled with gated stories.

## The weekly article

| when | what | writes |
|---|---|---|
| Sunday, 06:17 UTC | pick a subject, fetch its sources, draft, check, open a PR | a branch and a pull request — never `main` |

Five steps, and the bar at each one is deliberately higher than the home
page's: a mis-ordered row on the front page is replaced tomorrow, a badly
chosen subject wastes the week.

1. **Pick** (`pick.py`) — the best-scoring story of the last seven days that
   clears every clause: score, informative state, no injection suspicion, a
   subject squarely on topic with confidence behind it, a genre that reports
   a development rather than discussing one, and no overlap with a title
   already published. If nothing clears it, a relaxed bar runs; if nothing
   clears that either, the week publishes nothing and the job says so. That
   is a normal quiet week, not a failure.
2. **Fetch** (`fetch.py`) — the source articles, extracted with trafilatura.
   Nothing fetched is ever committed; storing other outlets' prose in a public
   repository is not ours to do. If no source loads, the run stops rather than
   writing from a headline.
3. **Draft** (`write.py`) — Claude Opus 5, streamed, effort high. Each source
   arrives wrapped in a `<source>` element tagged with a per-run nonce, and
   the system prompt says only an element carrying that nonce is part of the
   instructions — so a page that opens its own `<source>` or addresses the
   model is reported on, not obeyed. `fallbacks` is on: a policy decline would
   otherwise leave the week empty, and security incidents are this blog's
   staple.
4. **Check** (`verify.py`) — Jev reads every sentence back against the sources,
   in two passes. The first separates checkable claims from the author's own
   reasoning, because asking "is this supported" of an argument produces a
   confident no and a report full of noise. The second asks, for each claim
   and each source, whether the source bears it out.
5. **Render and open a PR** (`render.py`) — the house front matter with
   `ai_assisted: true`, which the theme turns into its banner, plus the
   disclosure line naming both models, which `charter.md` promises.

### What the report means

On a real run: 80 sentences, 27 checkable claims, 6 flagged. The six were the
author's own framing rather than fabrications — read the list as *look at
these*, not as *these are wrong*. When a claim is genuinely invented the
separation is stark: measured against a real source, two true claims scored
0.94 and 0.75 and four planted ones 0.07 and below, including a plausible
"the first known case of…" that the source never claims.

Cost of one article, measured: **$0.16** — about 9,400 tokens in and 4,700 out
on Claude Opus 5, plus a few cents of Jev. Roughly $0.70 a month.

### Running it by hand

```bash
newsbot article --out /tmp/preview      # write the post somewhere else
newsbot article --candidate 1           # take the runner-up subject
newsbot article --days 14 --no-verify   # wider window, skip the check
```

## Required secrets

| secret | why |
|---|---|
| `NEWSBOT_TOKEN` | fine-grained PAT, Contents: read and write. A commit pushed with the default `GITHUB_TOKEN` does **not** trigger other workflows, so `jekyll.yml` would never rebuild and the home page would keep showing yesterday's headlines. |
| `TYPESAFE_API_KEY` | the ranking and the citation check. Optional for the daily list — without it the collection publishes chronologically — required for the weekly article. Measured: **$0.0000190 per story**, about $0.025/month. |
| `ANTHROPIC_API_KEY` | the weekly draft. Claude Opus 5, measured at **$0.16 per article**. |

The workflow checks for `NEWSBOT_TOKEN` first and fails with that explanation
rather than running and silently publishing nothing.
