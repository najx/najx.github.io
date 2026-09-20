"""Turning a pile of feed entries into distinct stories.

Three jobs, in order: make URLs comparable, drop exact repeats, then group
what is left into clusters so the same event carried by five outlets counts
once — and counts as corroborated.

None of this asks a model anything. Jev is explicitly weak at counting and at
comparing dates, so both stay here in code where they are exact.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Item

# Query parameters that identify the referrer rather than the document.
TRACKING_PREFIXES = ("utm_", "at_", "mc_", "pk_", "ref_")
# Only keys that are unambiguously about the referrer. "s", "sh", "source" and
# "ref" were here too and had to go: they carry content on real sites (?s= is
# a search query on WordPress), so stripping them merged genuinely different
# URLs into one. Failing to merge a duplicate is cosmetic; dropping a distinct
# story is data loss.
TRACKING_EXACT = {
    "fbclid", "gclid", "igshid", "mkt_tok", "referrer",
    "cmpid", "ncid", "_hsenc", "_hsmi", "guccounter",
}

# Words carrying no topical signal, dropped before comparing two headlines.
STOPWORDS = frozenset("""
a an and are as at be been but by for from has have how in into is it its
more new now of on or our out over than that the their then there these they
this to up was were what when where which who why will with you your
says said report reports new latest just now first
""".split())

_WORD_RE = re.compile(r"[a-z0-9]+")

# Clustering thresholds, measured against a real 48h window of the configured
# feeds: of 903 headline pairs, exactly two scored above 0.20 — 0.50 for two
# write-ups of the same Gemini break-in, 0.20 for two takes on Meta Muse.
# Outlets rewrite headlines enough that lexical overlap alone under-clusters,
# so only the top is safe to merge blind; everything in the band is a question
# for Jev (judge.same_story), and below it we accept the misses.
CLUSTER_CERTAIN = 0.60
CLUSTER_BAND_LOW = 0.20


def canonical_url(url: str) -> str:
    """Strip a URL down to what actually identifies the document.

    Tracking parameters, fragments, `www.` and a trailing slash all vary
    between feeds carrying the same link, so none of them survive.
    """
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        # "Invalid IPv6 URL" and friends. One malformed link in one feed must
        # not abort the day's collection.
        return url.strip()
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if not parts.scheme or not host:
        # Relative or malformed: hand it back rather than mangle it.
        return url.strip()

    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in TRACKING_EXACT
        and not k.lower().startswith(TRACKING_PREFIXES)
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(query), ""))


def normalize_title(title: str) -> str:
    """Fold a headline to its comparable form: no accents, no punctuation."""
    folded = unicodedata.normalize("NFKD", title)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    # Curly quotes and dashes differ between feeds carrying the same headline.
    folded = folded.replace("’", "'").replace("‘", "'")
    return " ".join(_WORD_RE.findall(folded.lower()))


def title_tokens(title: str) -> frozenset[str]:
    """Significant words of a headline, for comparing two of them."""
    return frozenset(
        w for w in normalize_title(title).split()
        if len(w) > 2 and w not in STOPWORDS
    )


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedupe(items: list[Item]) -> list[Item]:
    """Drop entries pointing at the same document. The earliest one wins.

    Deliberately keyed on the canonical URL alone. An earlier version also
    keyed on the normalised title, which broke two ways: outlets running the
    same wire headline were discarded before cluster() could count them, so
    the strongest corroboration signal in the whole pipeline was destroyed
    exactly when it was strongest; and any headline with no ASCII word
    characters normalises to "", so every non-Latin headline collapsed onto a
    single key and all but the first vanished. Identical titles are now merged
    by cluster(), which scores them at Jaccard 1.0 and keeps their sources.
    """
    seen: set[str] = set()
    kept: list[Item] = []
    for item in sorted(items, key=lambda i: i.published):
        url_key = canonical_url(item.url)
        if url_key in seen:
            continue
        seen.add(url_key)
        kept.append(item)
    return kept


def cluster(items: list[Item], threshold: float = CLUSTER_CERTAIN) -> list[Item]:
    """Group headlines reporting the same event.

    Returns one representative per cluster — the earliest publication — with
    `also` listing the other outlets that carried it. Comparison is a plain
    token-set Jaccard on the significant words; it is blunt, but it is
    deterministic and free, and the borderline band is where a Noul question
    earns its keep (see CLUSTER_BAND_LOW).
    """
    ordered = sorted(items, key=lambda i: i.published)
    tokens = [title_tokens(i.title) for i in ordered]
    parent = list(range(len(ordered)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            if jaccard(tokens[i], tokens[j]) >= threshold:
                parent[find(j)] = find(i)

    groups: dict[int, list[Item]] = {}
    for idx, item in enumerate(ordered):
        groups.setdefault(find(idx), []).append(item)

    out = []
    for members in groups.values():
        head, rest = members[0], members[1:]
        head.also = sorted({m.source for m in rest} - {head.source})
        out.append(head)
    return sorted(out, key=lambda i: i.published, reverse=True)
