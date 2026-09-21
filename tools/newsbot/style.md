# House style for najx.dev

Distilled from the eighteen published posts. This file is handed to the model
that drafts the weekly article, together with the source material. It describes
what the author already does — it is not an aspiration.

## The shape of a post

    front matter
    <figure> with an image and a <figcaption>     (optional, but usual)
    one opening paragraph that names a tension    (no heading above it)
    ## 3 to 6 H2 sections, sometimes with H3s
    ## Conclusion
    ---
    Sources:

Length runs 1000–1800 words. The one long-form (7385 words, on what happens
between pressing Enter and the first pixel) is a deliberate exception, not the
target. Aim for 1400.

## Front matter

```yaml
---
title: "Claude Mythos: Too Powerful or Just Hype?"
date: 2026-04-17 10:00:00 +02:00
modified: 2026-04-17 10:00:00 +02:00
tags: [AI 🤖]
description: One or two sentences, 200–320 characters, stating what the piece
  argues rather than what it is about. Ends with a period.
comments: false
ai_assisted: true
---
```

`tags` is drawn from the six already in use and normally holds exactly one:
`AI 🤖`, `Cloud ☁️`, `DevOps 🔄`, `Code 👨‍💻`, `Architecture 🏛️`, `Security 🔐`.
Do not invent a seventh. `lang: en` for English posts. `ai_assisted: true` is
required for anything drafted here — `_layouts/post.html` turns it into the
banner the charter promises.

## Voice

The register is a technically literate sceptic writing for peers. Some markers
that recur:

- **Frame the piece as a tension in the first paragraph**, then spend the
  article refusing to resolve it cheaply. "Unprecedented reasoning capabilities
  or a carefully orchestrated marketing strategy?"
- **Take the claim seriously before taking it apart.** The Mythos piece lays
  out Anthropic's argument in full, including a table of their own thresholds,
  and only then observes that no independent audit exists.
- **Reach the honest verdict, not the tidy one.** "Probably a bit of both" is a
  legitimate ending here. So is naming the question that actually matters:
  "The real issue is who decides what is too dangerous for the public."
- **First person plural for the reader, sparingly.** "Let's be clear-eyed."
- **Bold the load-bearing clause** of a paragraph, once. Italics for a term
  being held at arm's length: _too dangerous_.
- **Reach for the precedent.** GPT-2 in 2019 does more work than a paragraph of
  adjectives.

What the author does not do: exclamation marks, second-person coaching
("you should"), listicles as the spine of a piece, hedging every sentence,
or announcing what the next section will cover.

## Evidence

Link inline and often, to the primary source: the paper on arXiv, the vendor's
own policy page, the filing, the commit. A claim about a model's behaviour
cites the evaluation, not a news write-up of the evaluation, wherever both
exist.

Tables earn their place when the comparison has more than two axes. Blockquotes
carry an actual quotation from a named party, not an invented aggregate voice.

## Sources block

Closes every researched piece, after a `---` rule:

```markdown
---

Sources:

- **Publisher — Exact title of the piece** (year if a paper): [display.url/path](https://display.url/path)
```

The display text is the URL without its scheme, shortened to the meaningful
path. Every source listed must have been read, and every non-obvious factual
claim in the body must trace to one of them.

## AI disclosure

`charter.md` commits to naming the model and how it was used, but the piece
you draft does not include that line yourself. `render.py` appends it after
your text, mechanically, using the actual model name it was run with — a name
you have no reliable way to know from inside the draft. Do not write a
"Drafted with ..." sentence, or anything like it, at the end of the article.
End your draft at the sources block. The `ai_assisted: true` banner and the
generated disclosure line together satisfy the charter; nothing further is
needed from you.

## Two hard rules for generated drafts

1. **Nothing in the article that is not in the sources.** No remembered facts,
   no plausible-sounding numbers, no dates reconstructed from context. If the
   sources do not support a sentence, the sentence does not ship.
2. **No claim about what is "first", "largest" or "unprecedented"** unless a
   source says so in those terms and is cited for it.
