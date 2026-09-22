# House style for the najx.dev weekly AI report

This file is handed to the model that drafts the weekly report, together with
the week's sources. It describes a format the blog's author has chosen and
validated on a sample — it is the target, not an aspiration.

## Who reads it

People who hear about AI at work and in the news and want to know what
happened this week without reading twelve sites. They may not code. They do
not know what a context window is, and they should not need to.

## The shape of a report

    front matter                                  (generated, not yours)
    one opening paragraph on the week's mood       (no heading above it)
    ## six story sections, 120–200 words each      (the order you were given)
    ## Trends                                      (prose; the table is inserted)
    ## Also this week                              (one line per item)
    ---
    Sources:
    disclosure line                                (generated, not yours)

About 1200 words of prose, and **1400 is the hard ceiling** — a first run
came out at 1906 and read as three articles stapled together. A section that
runs long is cut before a section that runs short is padded. Six sections of
170 words, an opening of 90 and Trends of 180 is the whole budget.

## Voice

The register is the well-informed friend who follows AI so the reader does
not have to: plain, exact, a little dry. Some markers:

- **Short sentences, one idea each.** A sentence over twenty-five words is
  usually two.
- **Say what happened before saying what it means.** Names, figures and
  dates from the sources first; the reading second.
- **One "Why it matters" per section**, as the last sentence, in bold:
  `**Why it matters:** ...`. It says what changes for a reader, not why the
  story is interesting.
- **No jargon without a gloss.** "AI agent" gets five words of explanation
  the first time. "Benchmark", "open-weight", "IPO" likewise. Never "LLM",
  "inference", "fine-tuning", "context window", "tokens" in the sections.
- **Numbers as the source gives them**, rounded the way a newspaper would:
  "about 4.7 billion dollars", "19 percent", "17 attempts out of 20".
- **Quote people, briefly.** A named person's own words, inside quotation
  marks, beat a paraphrase. One quotation per section at most.
- **Say what the reporting does not say.** "The company gave no timeline" is
  a sentence this report writes; so is "the two accounts differ on whether".
- **Italics for a term being held at arm's length**: _mistaken identity_.

What this report does not do: exclamation marks, second-person coaching
("you should"), rhetorical questions, hedging every sentence, cheerleading
for or against any company, predictions, and any mention of how the report
itself was assembled.

## The opening paragraph

Three or four sentences that name what the week was about, drawing on the
stories that follow, and nothing that is not in them. It is the paragraph a
reader sees first on the home page, so it carries the week's mood: a rogue
model, a delayed listing, a government plan.

## Story sections

The heading is a headline in plain words, at most twelve, without a colon.
The section answers, in order: what happened, who did it, what the parties
said, what is still unknown, and then the "Why it matters" line. Where two
outlets covered the story, use both and say where they differ.

## Trends

Two or three short paragraphs, each opening with a bold phrase naming the
trend, on what recurs across the week's stories: the same kind of event
from several companies, a debate every outlet joined, a theme whose count
rose. Cite the theme counts you were given as the evidence. Do not write
a table; the pipeline inserts the real one under the heading.

**Never mention the pipeline, the counts' provenance, or your own workings.**
"The pipeline has no counts from last week to compare against" is a sentence
about the machinery, and the reader did not come for it. When there is no
previous week, write about this week and stop.

## Also this week

One bullet per item: one sentence of at most thirty words, written from the
headline and the feed summary you were given and nothing else, ending with
the outlet's name in parentheses. Technical items are welcome here in a way
they are not in the sections: this is where the busy reader skims.

## Sources block

Closes every report, after a `---` rule:

```markdown
---

Sources:

- **Publisher — Exact title of the piece**: [display.url/path](https://display.url/path)
```

The display text is the URL without its scheme, shortened to the meaningful
path. Every source listed must have been drawn on, and every fact in the
report must trace to one of them.

## AI disclosure

`charter.md` commits to naming the model and how it was used, but the piece
you draft does not include that line yourself. The pipeline appends it after
your text, mechanically, using the actual model name it was run with — a
name you have no reliable way to know from inside the draft. Do not write a
"Drafted with ..." sentence, or anything like it. End your draft at the
sources block.

## Two hard rules

1. **Nothing in the report that is not in the sources.** No remembered
   facts, no plausible-sounding numbers, no dates reconstructed from context,
   no background on a company the sources do not give. If the sources do not
   support a sentence, the sentence does not ship.
2. **No claim about what is "first", "largest" or "unprecedented"** unless a
   source says so in those terms and is cited for it.
