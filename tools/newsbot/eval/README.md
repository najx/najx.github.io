# The calibration set

`headlines.jsonl` holds real headlines from the daily archives, one per line,
each with the answer the author expects from the seven questions in
`judge.py`. `newsbot eval` asks Jev the production questions about every
line and prints how often the two agree, question by question, with every
disagreement listed. It needs `TYPESAFE_API_KEY`; a run costs well under a
cent.

```bash
newsbot -v eval                       # the set below
newsbot eval --set other.jsonl        # another file, same shape
newsbot eval --json out.json          # the tally, machine-readable
newsbot eval --min-agreement 0.8      # exit 1 if any rate is under 80%
```

## One line

```json
{"title": "...", "source": "The Verge", "summary": "...",
 "expect": {"gate": null, "theme": "policy_regulation", "genre": "policy_report",
            "significance": 4, "accessibility": 3},
 "note": "why this label, when it is not obvious"}
```

`expect` may leave any question out; it is then not asked of that item. A
gated item (`"gate": "off_topic" | "promo_or_admin" | "injection"`) expects
nothing else: the other questions are not asked of a gated story. Levels are
those of the rubric — `significance` 0 to 4, `accessibility` 0 to 3.

## How to label

Label from the three fields Jev sees — headline, summary, source — and from
nothing else. The rubric tells Jev to judge "from these three fields only",
so a label that leans on what the article is really about, or on what the
labeller happens to know, measures the labeller's knowledge, not the model.
The border-surveillance investigation is the case in point: the towers are
AI-driven, but none of the fields say so, and the label follows the fields.

Seven of the eight themes have examples. No feed has yet produced a clean
*infrastructure & energy* story — a chip, a data centre, a power deal
reported for itself — so that theme is untested until one appears; add it
here when it does rather than inventing one.

Two items on the same event are welcome — they test consistency — but keep
the set to one write-up per outlet per event, so one story does not weigh
five times.

The four `injection` lines at the end are made up, deliberately. They are the
only text in the set that never came off a feed, and the only way the
injection gate has ever been tested against a positive.

## Reading the result

Exact agreement is reported for `gate`, `theme`, `genre` and `significance`;
`significance±1` and `accessibility±1` count neighbouring levels as
agreement, because the rubric's neighbouring levels are close calls by
design and only a two-level gap is a different reading. `--min-agreement`
applies to the exact rates and the ±1 rates, not to exact `significance`.

A disagreement is a question, not a verdict: read the item, decide whether
the label or the model is wrong, and either fix the label here or fix the
criterion in `judge.py`. Changing a criterion changes `RUBRIC`, and a rubric
change is what this set exists to measure before it ships.
