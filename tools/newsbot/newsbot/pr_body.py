"""Build a reviewable weekly PR body within GitHub's 65,536-character limit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


MAX_BODY_BYTES = 60_000  # Leave room for GitHub's 65,536-character limit.
MAX_LOG_BYTES = 16_000


def _clip(value: object, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text.encode("utf-8")) <= limit:
        return text
    clipped = text.encode("utf-8")[: limit - 3].decode("utf-8", "ignore")
    return clipped + "..."


def _findings(rows: list[dict], budget: int, format_row) -> str:
    output = ""
    shown = 0
    for row in rows:
        entry = format_row(row)
        if len((output + entry).encode("utf-8")) > budget - 120:
            break
        output += entry
        shown += 1
    if shown < len(rows):
        output += f"- [ ] {len(rows) - shown} autre(s) entrée(s) omise(s) ici : relire le rapport en entier.\n"
    return output


def _log_excerpt(log: str) -> str:
    # Keep the start (selection) and end (verification) when the log is long.
    safe = log.replace("`", "").replace("~~~~", "~ ~ ~ ~")
    if len(safe.encode("utf-8")) <= MAX_LOG_BYTES:
        return safe
    encoded = safe.encode("utf-8")
    head = encoded[: MAX_LOG_BYTES // 2].decode("utf-8", "ignore")
    tail = encoded[-MAX_LOG_BYTES // 2 :].decode("utf-8", "ignore")
    return head + "\n\n[Milieu du journal omis ; version complète dans les logs de l'exécution.]\n\n" + tail


def render_body(week: str, checks: dict | None, log: str, run_url: str) -> str:
    parts = [
        f"Rapport hebdomadaire {week}. **Rien n'est publié tant que cette PR n'est pas mergée et sortie de l'état brouillon.**\n\n",
        "## À cocher avant de passer la PR en \"Ready for review\"\n\n",
    ]
    if checks is None:
        parts.append("- [ ] Vérification des citations indisponible : relire le rapport en entier avant de sortir du brouillon.\n")
    else:
        unsupported = checks.get("unsupported", [])
        if not unsupported:
            parts.append(f"- [ ] Aucune affirmation non étayée sur {checks.get('checked', 0)} vérifiées par Jev — à confirmer en relisant le rapport.\n")
        else:
            parts.append(_findings(
                unsupported, 18_000,
                lambda f: f"- [ ] [{f['support']:.2f}] {_clip(f['sentence'], 450)}\n"
                + (f"  - Claude Haiku : {_clip(f['note'], 450)}\n" if f.get("note") else ""),
            ))

        reconsidered = checks.get("reconsidered", [])
        if reconsidered:
            parts.append("\n### Signalées par Jev, retrouvées par Claude Haiku (extrait vérifié)\n\n")
            parts.append(_findings(
                reconsidered, 10_000,
                lambda f: f"- [{f['support']:.2f}] {_clip(f['sentence'], 450)}\n"
                f"  - « {_clip(f.get('excerpt'), 450)} » — {_clip(f.get('source') or '?', 200)}\n",
            ))

        synthesis = checks.get("synthesis", [])
        if synthesis:
            parts.append("\n### Ouverture et Trends, à relire\n\n")
            parts.append(_findings(
                synthesis, 7_000,
                lambda f: f"- [ ] [{f['support']:.2f}] {_clip(f['sentence'], 450)}\n",
            ))

    parts.extend([
        "\n### Le reste\n\n",
        "- [ ] Le tableau des thèmes sous « Trends » correspond au journal joint à l'exécution.\n",
        "- [ ] Le bloc de divulgation en fin de rapport, que la charte impose.\n",
        "- [ ] Les six titres de section lisibles sans bagage technique.\n\n",
        f"[Journal complet de l'exécution]({run_url}).\n\n",
        "## Extrait du journal de la sélection et de la vérification\n\n~~~~\n",
        _log_excerpt(log),
        "\n~~~~\n",
    ])
    body = "".join(parts)
    if len(body.encode("utf-8")) > MAX_BODY_BYTES:
        raise ValueError("PR body exceeds its 60,000-byte safety limit")
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--checks", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    checks = json.loads(args.checks.read_text(encoding="utf-8")) if args.checks.exists() else None
    body = render_body(args.week, checks, args.log.read_text(encoding="utf-8"), args.run_url)
    args.out.write_text(body, encoding="utf-8")


if __name__ == "__main__":
    main()
