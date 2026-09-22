# newsbot

Collects AI headlines every morning, judges them, and once a week turns the
week into a report for people who do not build AI systems: **AI Weekly**,
published under `/ai-news/`. Lives in [`tools/newsbot`](../tools/newsbot);
driven by two workflows under `.github/workflows/`.

## What runs, and when

| when | what | writes |
|---|---|---|
| daily, 05:17 UTC | fetch every feed, window, deduplicate, cluster, judge with Jev | `.newsbot/archive/<date>.json` |
| Sunday, 06:17 UTC | merge the week, rank, pick six stories, fetch their articles, draft with Claude, check with Jev then Claude Haiku, open a draft PR | `_ai_news/<week>.md`, `.newsbot/state.json`, on a branch — never `main` |
| by hand | judge the calibration set with Jev, print the agreement question by question | a `judge-calibration` artifact |

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
newsbot -v eval                    # judge the labelled set, print the agreement
```

`collect --window` changes how far back to look (48 hours by default).
`weekly --days` is the width of the week (7), `--stories` the number of
sections (6), `--no-verify` skips the citation check, `--no-recheck` skips
the Claude Haiku second reading of what Jev flagged, and `--checks-out`
writes the check as JSON for the workflow's checklist. Every run ends with
one line per model naming the requests, the tokens and the list price. `--out` writes the
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
| `story_type` | Choice | incident, news report, engineering report, research, release, feature, essay, policy, digest, notice |
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

Every judgement carries `rubric: "weekly-2"`, the name of this question set.
The weekly run only ranks judgements under the current rubric; whatever the
archives hold under an older one, or unjudged because the key was missing
that day, is scored on the spot before selection. A change of questions
therefore costs one run's worth of Jev calls, not a week of silence.
`weekly-2` added `news_report` to `story_type`: a plain report of a
company's move — a loan, a settlement, a delayed listing, one company
blocking another — had no label under `weekly-1` and landed in `notice` or
`policy_report` at random. The week SoftBank borrowed $11 billion for its
OpenAI stake, the story was weighted as a personnel note.

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
3. **Select** — the stories published inside the days the title names, never
   the last seven days counted from the run: a Sunday run admitted the Sunday
   before as well, and a manual run mid-week put stories from after the
   labelled week into it. Then six sections, at most two per theme, each
   clearing: judged under the current rubric, not gated, score ≥ 0.30,
   informative state, no injection suspicion, accessibility ≥ 1.5 of 3, and
   nothing the blog has already covered (below). What misses a section may
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
6. **Check and render** (`verify.py`, `recheck.py`, `render.py`) — Jev reads
   every sentence back against the texts the writer was given, in two
   passes: checkable claims first, then support. Each story section is read
   against the sources *that* story was written from, the also-list against
   its items' headline and summary, and the overview against everything
   plus the theme counts. Every source is cut into passages of about two
   thousand characters and the claim is put to each one; the best passage
   wins. Whatever Jev cannot place is re-read by Claude Haiku, which sees the
   whole of the section's sources and must quote, word for word, the passage
   it found; the quote is looked up in the source text before the verdict
   counts. The report is rendered with the collection's front matter —
   `week`, `period`, the `stories` list of anchors the home page links to —
   the theme table inserted under *Trends* from the pipeline's own counts,
   and the disclosure line naming the models that actually answered, the
   second reader included.

### The report's shape

One opening paragraph on the week. Six sections, each ending on a bold *Why
it matters*. *Trends*: the theme table, then two or three paragraphs. *Also
this week*: one line per item. Sources. Disclosure. **No word count and no
ceiling** — each story gets the length its sources warrant, and the shape is
what keeps the report readable. The full house style is
[`tools/newsbot/style.md`](../tools/newsbot/style.md).

### Not covering the same thing twice

Three checks, in increasing order of effort.

**The last three weeks of reports.** `.newsbot/state.json` remembers which
stories had a section: the canonical URL, the `also_urls` of the other
write-ups, the source title, the report's week and the date. `select` refuses
a candidate whose URL — or any of its own `also_urls` — appears in an entry
less than 21 days old. The file is committed on the report's branch, so the
cooldown only starts once the report is merged. An entry whose date will not
parse is treated as recent.

**Everything the blog has ever published.** `published_coverage` reads every
article under `_posts/` and every earlier report under `_ai_news/`, and
collects two things: every link they cite, and their titles — including the
outlet headlines in their Sources blocks, which is what a feed hands us and a
far better handle on a subject than the title Claude rewrote. A candidate
whose link the blog has already cited gets nothing, with no time limit: a
source this blog has written from is not news to report again. A candidate
whose headline overlaps a published title by 0.40 or more is refused too.
The week being written is skipped, so a second run for the same week does not
find all of its own stories already covered.

**The same event under another outlet's headline.** The hard case, and the
one that prompted all this: the blog's article on the Gemini break-in is
titled *When the Model Stopped*, which shares no word with the feed headline,
and Marktechpost's write-up of the same incident sits at a different link
again. Its headline scores 0.21 against the one the article cites — below the
overlap threshold, above noise. That is exactly the band `judge.same_story`
exists for, so those pairs are put to Jev, and the ones it calls the same
event join the excluded links. Without a key the lexical checks still run;
only this last one is skipped.

### What the checklist means

The pull request opens as a draft with one checkbox per claim neither reader
could find in the sources, each followed by Claude Haiku's one-line note:
what the sources say instead, or what they do not say. Read the list as
*look at these*, not as *these are wrong*; when a claim is genuinely
invented the separation is stark — measured against a real source, true
claims scored 0.94 and 0.75 and planted ones 0.07 and below.

Under its own heading come the sentences Jev flagged that Claude Haiku
found, with the passage it quoted and the source it is in. Those are
bullets, not checkboxes: the quote is there to be compared with the
sentence, and the quote has already been verified to exist in the source.
The first live run under the old checker flagged the headline of the week —
Trump's "AI Force" — at 0.12 because the claim was put against an entire
article at once; passages and the second reader exist so that kind of line
never reaches the checklist again.

**The opening paragraph and Trends are listed separately.** Both draw on the
whole week at once: on several stories, and on counts this pipeline computed
rather than on any article. The checker compares one claim to one source at a
time, so a sentence spanning four stories is borne out by none of them. On
the first live run, eight of eleven findings were of that kind, which buried
the three that mattered. They are still read back — against the same sources
plus the theme counts, so a misread number is still caught — and printed
under their own heading, to be read rather than treated as findings.

### Cost

Every run prints one line per model: requests, tokens, and the cost at list
price ($0.042 per million input tokens for Jev, output free; $5 in and $25
out for Claude Opus 5; $1 in and $5 out for Claude Haiku 4.5). Measured on a
dry run of the week of 14–20 September 2026, on 22 September:

| step | requests | tokens | cost |
|---|---|---|---|
| draft, Claude Opus 5 | 1 | 15,310 in, 10,045 out | $0.328 |
| judge and check, Jev | 572 | 494,919 in | $0.021 |
| second reading, Claude Haiku 4.5 | 11 | 26,954 in, 2,454 out | $0.039 |
| daily collection, Jev (79 stories) | 81 | 287,016 in | $0.012 |

About $0.40 a report and $0.36 a month of collection: **under $2 a month**.
The checker's 451 claim-passage pairs cost less than the old article-at-once
check would have, because each section is now read against its own sources
rather than all of them.

## Measuring the judge

The ranking weights in `judge.py` are editorial judgement, and until this
existed the rubrics had never been scored against an answer key: the only way
to know whether a change helped was to read the next report.
[`tools/newsbot/eval/headlines.jsonl`](../tools/newsbot/eval/headlines.jsonl)
holds real headlines from the archives — sixty-odd, one write-up per outlet
per event — each with the answer the author expects from the seven
questions, plus four made-up lines that carry an instruction to whatever
reads the feed. Those four are the only test the injection gate has ever had
against a positive; on the live feeds it has never fired.

```bash
newsbot -v eval                       # needs TYPESAFE_API_KEY; well under a cent
newsbot eval --min-agreement 0.8      # exit 1 if any question is under 80%
```

The *AI news — judge calibration* workflow runs the same thing from GitHub,
by hand, and uploads the tally. Run it before merging any change to a
criterion in `judge.py`: a rubric change is what the set exists to measure.
The tally reports exact agreement for the gate, the theme, the genre and the
significance level, and agreement within one level for significance and
accessibility, because neighbouring levels of the rubric are close calls by
design. A disagreement is a question, not a verdict — read the item and fix
whichever of the label or the criterion is wrong. How to label, and why the
labels follow the three fields Jev sees rather than what the article is
really about, is in [`tools/newsbot/eval/README.md`](../tools/newsbot/eval/README.md).

## Required secrets

| secret | why |
|---|---|
| `NEWSBOT_TOKEN` | fine-grained PAT, Contents: read and write. Commits the daily archive and opens the weekly pull request. |
| `TYPESAFE_API_KEY` | the judging and the citation check. Optional for the daily run — an unscored day is scored on Sunday — required for the weekly report. |
| `ANTHROPIC_API_KEY` | the weekly draft, and the second reading of the claims Jev flags. |

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
