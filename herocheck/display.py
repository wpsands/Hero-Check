"""Terminal display for HeroCheck results."""

import textwrap
from urllib.parse import urlparse

from herocheck.models import CommitteeSynthesis, HeroAnalysis, ICPProfile

W = 64


def print_synthesis(
    synthesis: CommitteeSynthesis,
    analyses: list[HeroAnalysis],
    icps: list[ICPProfile],
) -> None:
    """Print the one-screen committee briefing to terminal."""
    bar = "=" * W

    # Header
    domain = urlparse(synthesis.url).netloc
    print(f"\n{bar}")
    print(f"  HEROCHECK: {domain}")
    committee_line = " + ".join(f"{p.name} ({p.title})" for p in icps)
    for line in textwrap.wrap(committee_line, width=W - 4):
        print(f"  {line}")
    print(bar)

    # Verdict — best and worst persona
    scored = sorted(
        [(a.persona_name or "Generic", a.overall_score) for a in analyses],
        key=lambda x: x[1],
        reverse=True,
    )
    best_name, _ = scored[0]
    worst_name, _ = scored[-1]

    print()
    print(f"  VERDICT: Built for {best_name}. Loses {worst_name}.")
    print()

    # Score grid
    names = synthesis.personas
    short_names = [n.split()[0] for n in names]
    print(f"  {'CATEGORY':<20}", end="")
    for sn in short_names:
        print(f" {sn:>7}", end="")
    print("  SIGNAL")
    print(f"  {'-' * (W - 4)}")

    cat_labels = ["Value Prop", "Headline", "Layout", "CTA", "Social Proof"]
    all_items = synthesis.consensus + synthesis.tensions
    for label in cat_labels:
        item = next((c for c in all_items if label.lower() in c.category.lower()), None)
        if item:
            if item.signal == "consensus":
                avg = sum(item.scores.values()) / len(item.scores)
                icon = "+" if avg >= 3.5 else "X"
            else:
                icon = {"tension": "!", "split": "~"}.get(item.signal, " ")

            print(f"  {icon} {label:<18}", end="")
            for persona in names:
                s = item.scores.get(persona, 0)
                print(f" {s:>7}", end="")
            print(f"  {item.signal}")
        else:
            print(f"    {label:<18}", end="")
            for _ in names:
                print(f"     {'?':>3}", end="")
            print()

    # Overall
    print(f"  {'-' * (W - 4)}")
    print(f"  {'OVERALL':<20}", end="")
    for persona in names:
        for a in analyses:
            if a.persona_name == persona:
                print(f" {a.overall_score:>7.1f}", end="")
                break
    print()
    print()

    # Consensus
    if synthesis.consensus:
        print("  CONSENSUS (all agree)")
        for c in synthesis.consensus:
            avg = sum(c.scores.values()) / len(c.scores)
            icon = "+" if avg >= 3.5 else "X"
            short_insight = _truncate(c.insight, W - 6)
            print(f"    {icon} {c.category}")
            print(f"      {short_insight}")
        print()

    # Tensions
    if synthesis.tensions:
        print("  TENSIONS (they disagree)")
        for t in synthesis.tensions:
            print(f"    ! {t.category} (spread: {t.spread})")
            for line in textwrap.wrap(t.insight, width=W - 8):
                print(f"      {line}")
        print()

    # Persona fit
    print("  BUILT FOR")
    for line in textwrap.wrap(synthesis.who_this_hero_is_for, width=W - 6):
        print(f"    {line}")
    print()
    print("  LOSES")
    for line in textwrap.wrap(synthesis.who_it_loses, width=W - 6):
        print(f"    {line}")
    print()

    # Fix first
    print("  FIX FIRST (by committee impact)")
    for i, action in enumerate(synthesis.priority_actions[:5], 1):
        short = _first_sentence(action)
        short = _truncate(short, W - 8)
        print(f"    {i}. {short}")

    print(f"\n{bar}")


def print_single_analysis(analysis: HeroAnalysis) -> None:
    """Print a concise single-persona result to terminal."""
    bar = "=" * W
    domain = urlparse(analysis.url).netloc

    print(f"\n{bar}")
    print(f"  HEROCHECK: {domain}")
    if analysis.persona_name:
        print(f"  Persona: {analysis.persona_name}")
    print(bar)
    print()
    print(f"  OVERALL: {analysis.overall_score:.1f} / 5.0")
    print()

    cats = [
        ("Value Prop", analysis.value_prop_score),
        ("Headline", analysis.headline_score),
        ("Layout", analysis.layout_score),
        ("CTA", analysis.cta_score),
        ("Social Proof", analysis.social_proof_score),
    ]
    for label, cat in cats:
        icon = "+" if cat.score >= 4 else ("X" if cat.score <= 2 else "-")
        print(f"  {icon} {label:<20} {cat.score}/5")
    print()

    print("  STRENGTHS")
    for s in analysis.strengths[:3]:
        print(f"    + {_truncate(_first_sentence(s), W - 8)}")
    print()

    print("  FIX")
    for imp in analysis.improvements[:3]:
        print(f"    X {_truncate(_first_sentence(imp), W - 8)}")

    print(f"\n{bar}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _first_sentence(text: str) -> str:
    return text.split(".")[0] + "." if "." in text else text


def _truncate(text: str, max_len: int) -> str:
    return text[:max_len - 3] + "..." if len(text) > max_len else text
