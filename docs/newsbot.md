# newsbot

Collects AI headlines every morning, judges them, and once a week turns the
week into a report for people who do not build AI systems: **AI Weekly**,
published under `/ai-news/`. Lives in [`tools/newsbot`](../tools/newsbot);
driven by two workflows under `.github/workflows/`.

## What runs, and when

| when | what | writes |
|---|---|---|
| daily, 05:17 UTC | fetch every feed, window, deduplicate, cluster, judge with Jev | `.newsbot/archive/<date>.json` |
| Sunday, 06:17 UTC | merge the week, rank, pick six stories, fetch their articles, draft with Claude, check with Jev, open a draft PR | `_ai_news/<week>.md`, `.newsbot/state.json`, on a branch — never `main` |

The home page renders the latest report at build time from the `_ai_news`
collection: its title, its period, and its six section headings as anchors
into the report. No client-side fetch, no outbound links on the home page —
the outlets get their links in the report's Sources block. If the collection
is empty the section simply does not render. `/ai-news/` lists every report;
`/feed/ai_news.xml` is its own feed.

## Where things live

```
_data/news-sources.yml       the feed list — the one file you edit by hand
.newsbot/archive/<date>.json the day's distinct stories, summaries and judgements
.newsbot/state.json          which stories already had a section, and when
_ai_news/<year>-w<week>.md   the reports, one per ISO week
tools/newsbot/style.md       the house style handed to the writer
```

`.newsbot/` starts with a dot, so Jekyll ignores it. That matters: Jekyll
reads *every* file under `_data/` on *every* build, so a year of daily
archives there would be paid for on each rebuild. Nothing the daily run
writes is read by Jekyll any more, and `jekyll.yml` skips the rebuild when a
push only touches `.newsbot/`.

## Adding a source

Append to `_data/news-sources.yml`:

```yaml
  - name: Example Lab
    url: https://example.com/blog/rss.xml
```

`name` is what the report's Sources block will show, so keep it short. Then
check it actually answers:

```bash
newsbot probe
```

A source with no feed goes in with `enabled: false` and a `note` saying why,
so the gap stays visible rather than being silently dropped. Anthropic and
Mistral are both in that state today — neither publishes RSS.

## Running it by hand

```bash
pip install -e './tools/newsbot[dev]'
newsbot probe                      # does every feed still answer?
newsbot -v collect --dry-run       # judge the day and print it, write nothing
newsbot -v collect                 # write today's archive
newsbot -v weekly --dry-run        # print the week's plan, draft nothing
newsbot -v weekly --out /tmp/prev  # draft, check, write the report elsewhere
```

`collect --window` changes how far back to look (48 hours by default).
`weekly --days` is the width of the week (7), `--stories` the number of
sections (6), `--no-verify` skips the citation check, and `--checks-out`
writes the check as JSON for the workflow's checklist. `--out` writes the
report under another root and marks nothing as covered. Both workflows take
their inputs as `workflow_dispatch` fields, and the weekly one has a
`dry_run` checkbox that uploads the report as an artifact instead of opening
a pull request.

## Design notes

**Feeds, not scraping.** Every enabled source publishes RSS or Atom. Nothing
to keep working when a site reskins, no anti-bot to get around, no question
about terms of use, and no cost.

**Dates and counting stay in code.** Jev is documented as unreliable at
comparing dates and at counting, so the freshness window, the corroboration
count, the days a story kept appearing, and the theme table are all computed
here, exactly, and never asked of a model.

**Clustering is deliberately blunt.** Two headlines merge when their
significant words overlap by 60% or more. Measured against a real 48-hour
window, only two of 903 headline pairs scored above 0.20 — outlets rewrite
headlines enough that lexical overlap alone under-clusters. Pairs in the
0.20–0.60 band are put to Jev's `same_story` question; below it, misses are
accepted. The thresholds are `CLUSTER_BAND_LOW` and `CLUSTER_CERTAIN` in
`normalize.py`. The weekly run clusters again across the seven archives, so
a story two outlets ran on different days still counts as one story with two
outlets.

**Only the representative is fetched, plus its own write-ups.** When several
outlets carry the same story, the earliest publication is the representative
and the others are recorded in `also_urls`. The writer is given up to three
of those texts per story — matched by URL, never by outlet name, which would
pull in everything that outlet published that week.

**A feed that fails does not fail the run.** Failures are collected, logged,
and written into the day's archive, so a source going dark shows up in the
job log instead of quietly shrinking the list. The same applies to a single
malformed link: `canonical_url` hands back anything `urlsplit` rejects rather
than raising.

**Deduplication keys on the canonical URL alone, never the title.** Two
outlets running the same wire headline are two documents, and collapsing them
here would destroy the corroboration that `cluster()` exists to count.

**Nothing published is trusted.** Titles come off the open web. The home
template escapes every interpolation; feed text is decoded to a fixed point
and then stripped of markup, in that order, so doubly-encoded input cannot
reappear as tags after the strip. The report's own links are the ones Claude
writes into the Sources block from the URLs it was given.

**`newsbot` finds the site from the working directory**, not from where its
code lives, because the workflow installs the package non-editably. Set
`NEWSBOT_ROOT` to run it from elsewhere.

**Every JSON file is written through a temporary file** and parsed before
being moved into place, so a crash never leaves a half-written archive for
Sunday's run to choke on.

## Judging with Jev

Seven questions about one story, batched into a single request. The rubrics
are long on purpose: *Literal Reading* is the first failure mode TypeSafe
documents — Jev answers the question you wrote, not the one you meant — so
each level spells out its boundary cases rather than trusting a short phrase.

| question | type | what it decides |
|---|---|---|
| `public_significance` | Score 0-4 | how far beyond the AI industry the story reaches: from "not about AI" to "in the general news" |
| `accessibility` | Score 0-3 | how much technical background a reader needs to follow it |
| `theme` | Choice | one of the eight themes of the report (below) |
| `story_type` | Choice | incident, engineering report, research, release, feature, essay, policy, digest, notice |
| `is_promo_or_admin` | Noul | event, hire, call for papers, housekeeping |
| `state_is_informative` | Noul | do the fields say enough to know what this is about |
| `injection_present` | Noul | is the text addressing whatever reads it |

Three hard gates — injection, promotion, and "not about AI" — each reading
its own question against its own threshold. Then a merit of significance,
accessibility and genre, significance again multiplicatively so that an easy
story nobody would hear of cannot be rescued, a soft confidence gate, and a
ceiling from `state_is_informative`. Every weight lives in `judge.py`, not in
a rubric: changing a weight changes what we do with an answer, changing a
criterion changes what Jev is asked.

`public_significance` is read as an expectation over its **probability
distribution**, not from `.score`: the Score guide says neighbouring levels
are not assumed adjacent, so a weighted position is meaningless when the mass
splits between level 0 and level 4.

Every judgement carries `rubric: "weekly-1"`, the name of this question set.
The weekly run only ranks judgements under the current rubric; whatever the
archives hold under an older one, or unjudged because the key was missing
that day, is scored on the spot before selection. A change of questions
therefore costs one run's worth of Jev calls, not a week of silence.

The eight themes: models & products, agents & assistants, safety &
incidents, policy & regulation, business & money, research & science,
society & work, infrastructure & energy.

## The weekly report

Six steps.

1. **Merge** (`weekly.py`) — the seven archives folded into distinct stories:
   same document across days counted once, same event across outlets
   clustered, the best judgement kept, the days seen and the outlets counted.
   The previous seven days are loaded too, for the theme table.
2. **Rank** — `trend = score × (0.55 + 0.25·corroboration + 0.10·recurrence
   + 0.10·freshness)`. Corroboration is outlets out of four, recurrence days
   seen out of three, freshness a four-day half-life. A story one outlet ran
   once still ranks; the multiplier bottoms out at 0.55.
3. **Select** — six sections, at most two per theme, each clearing: judged
   under the current rubric, not gated, score ≥ 0.30, informative state, no
   injection suspicion, accessibility ≥ 1.5 of 3, and not covered by a
   section in the last 21 days (`state.json`). What misses a section may
   still get a line under *Also this week*: same clauses, a lower floor,
   and no accessibility clause, so the technical items land there. Fewer
   than three sections is a quiet week: the run stops and says so.
4. **Fetch** (`fetch.py`) — the article behind each section, extracted with
   trafilatura, up to three write-ups per story. Nothing fetched is ever
   committed. A story none of whose write-ups load drops out and the next
   moves up; a section is never written from a headline.
5. **Draft** (`write.py`) — Claude Opus 5, streamed, effort high, given
   `style.md`, the previous report for voice, the sections' texts, the
   also-list's headlines and feed summaries, and the theme counts. Each
   source arrives in a `<source>` element tagged with a per-run nonce, and
   only an element carrying that nonce is part of the instructions.
6. **Check and render** (`verify.py`, `render.py`) — Jev reads every sentence
   back against the texts the writer was given (for the also-list, the
   headline and summary), in two passes: checkable claims first, then
   support. The report is rendered with the collection's front matter —
   `week`, `period`, the `stories` list of anchors the home page links to —
   the theme table inserted under *Trends* from the pipeline's own counts,
   and the disclosure line naming the models that actually answered.

### The report's shape

One opening paragraph on the week. Six sections of 120–200 words, each
ending on a bold *Why it matters*. *Trends*: the theme table, then two or
three paragraphs. *Also this week*: one line per item. Sources. Disclosure.
About 1200 words of prose. The full house style is
[`tools/newsbot/style.md`](../tools/newsbot/style.md).

### The cooldown

`.newsbot/state.json` remembers which stories had a section: the canonical
URL, the `also_urls` of the other write-ups, the source title, the report's
week and the date. `select` refuses a candidate whose URL — or any of its own
`also_urls` — appears in an entry less than 21 days old. The seven-day window
keeps most repeats out on its own; this catches the story that straddles two
Sundays and the follow-up published under a new link. The file is committed
on the report's branch, so the cooldown only starts once the report is
merged. An entry whose date will not parse is treated as recent.

### What the checklist means

The pull request opens as a draft with one checkbox per claim Jev could not
find in the sources. Most flagged sentences are the writer's own framing
rather than fabrications — read the list as *look at these*, not as *these
are wrong*. When a claim is genuinely invented the separation is stark:
measured against a real source, true claims scored 0.94 and 0.75 and planted
ones 0.07 and below.

### Cost

To be measured on the first live run. Estimated from the single-story
article it replaces ($0.16 for 9,400 tokens in): six stories with up to
three write-ups each puts roughly 40,000 tokens in front of Claude Opus 5,
so $0.30–0.40 per report, plus a few cents of Jev for the selection and
several hundred claim checks.

## Required secrets

| secret | why |
|---|---|
| `NEWSBOT_TOKEN` | fine-grained PAT, Contents: read and write. Commits the daily archive and opens the weekly pull request. |
| `TYPESAFE_API_KEY` | the judging and the citation check. Optional for the daily run — an unscored day is scored on Sunday — required for the weekly report. |
| `ANTHROPIC_API_KEY` | the weekly draft. |

Both workflows check for their secrets first and fail with an explanation
rather than running and silently publishing nothing.

## Lot 5 — Apify adapter for Anthropic and Mistral (design, not built)

Issue #15 asks for this. It is written down here rather than shipped because
there is no Apify token available to develop or test it against — an adapter
built without ever calling the real API would be speculation wearing code,
and a feed that silently returns nothing is worse than one that stays
`enabled: false` with a note.

**Integration points, in the code as it stands:** `Source` (`sources.py`)
would grow a `kind` field read by `load_sources()`; `collect()` would
dispatch on it to a second fetcher with the same contract — takes a
`Source`, returns `list[Item]`, raises on failure — so the failure isolation
and `probe`'s table keep working unchanged. The adapter's job is to produce
`Item`s; clustering, judging and the weekly run do not care where one came
from. `fetch()`'s per-entry rules (no title, no link, no parseable date:
skip; `clean_text()` on everything) apply just as much to scraped entries.

**What it would run:** a generic content-crawler actor pointed at the two
news pages, once per collection, filtered to that day, with a mapping step
from the actor's output to `Item`'s five fields. **New secret:** `APIFY_TOKEN`.
**Before it ships:** a token, a choice of actor, a measured per-run cost, and
the same live check `newsbot probe` gives every feed.
