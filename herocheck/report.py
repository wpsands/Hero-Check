"""Report generation — markdown output."""

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from herocheck.models import CommitteeSynthesis, CompetitiveReport, HeroAnalysis


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def star_bar(score: float, max_score: int = 5) -> str:
    """Render a score as filled/empty stars."""
    filled = round(score)
    return "\u2605" * filled + "\u2606" * (max_score - filled)


def _domain_slug(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "").replace(".", "_")


# ---------------------------------------------------------------------------
# Markdown report — single analysis
# ---------------------------------------------------------------------------
def generate_markdown_report(analysis: HeroAnalysis) -> str:
    """Generate a markdown report from a single analysis."""
    categories = [
        analysis.value_prop_score,
        analysis.headline_score,
        analysis.layout_score,
        analysis.cta_score,
        analysis.social_proof_score,
    ]

    lines: list[str] = []
    lines.append(f"# HeroCheck Report: {analysis.url}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if analysis.persona_name:
        lines.append(f"**Persona:** {analysis.persona_name}")
    lines.append("")

    # Overall score
    lines.append("## Overall Score")
    lines.append("")
    lines.append(
        f"**{analysis.overall_score:.1f} / 5.0** {star_bar(analysis.overall_score)}"
    )
    lines.append("")

    # Extracted elements
    lines.append("## Extracted Elements")
    lines.append("")
    lines.append(f"- **Headline:** {analysis.headline}")
    lines.append(f"- **Subheadline:** {analysis.subheadline}")
    lines.append(f"- **CTA:** {analysis.cta_text}")
    lines.append(f"- **Layout Source:** {analysis.layout_source}")
    lines.append("")

    # Scorecard table
    lines.append("## Scorecard")
    lines.append("")
    lines.append("| Category | Score | Evidence |")
    lines.append("|----------|-------|----------|")
    for cat in categories:
        lines.append(
            f"| {cat.category} | {star_bar(cat.score)} ({cat.score}/5) | {cat.evidence} |"
        )
    lines.append("")

    # Strengths
    lines.append("## Strengths")
    lines.append("")
    for s in analysis.strengths:
        lines.append(f"- {s}")
    lines.append("")

    # Improvements
    lines.append("## Areas for Improvement")
    lines.append("")
    for imp in analysis.improvements:
        lines.append(f"- {imp}")
    lines.append("")

    # Positioning drift
    if analysis.positioning_check:
        pc = analysis.positioning_check
        lines.append("## Positioning Drift Check")
        lines.append("")
        lines.append(
            f"**Alignment Score:** {pc.alignment_score}/5 {star_bar(pc.alignment_score)}"
        )
        lines.append(f"- **Hero says:** {pc.hero_message}")
        lines.append(f"- **Positioning says:** {pc.positioning_message}")
        lines.append(f"- **Drift:** {pc.drift_details}")
        lines.append(f"- **Recommendation:** {pc.recommendation}")
        lines.append("")

    # Detailed recommendations
    lines.append("## Detailed Recommendations")
    lines.append("")
    for cat in categories:
        lines.append(f"### {cat.category}")
        lines.append("")
        lines.append(f"{cat.recommendation}")
        lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(analysis.summary)
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown report — competitive comparison
# ---------------------------------------------------------------------------
def generate_comparison_markdown(
    report: CompetitiveReport,
    analyses: list[HeroAnalysis],
) -> str:
    """Generate a markdown competitive comparison report."""
    lines: list[str] = []
    lines.append("# HeroCheck Competitive Comparison")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Persona:** {report.persona_name}")
    lines.append("")

    # Rankings table
    lines.append("## Rankings")
    lines.append("")
    lines.append("| Rank | Company | Score | Strongest | Weakest | Verdict |")
    lines.append("|------|---------|-------|-----------|---------|---------|")
    for i, r in enumerate(report.rankings, 1):
        lines.append(
            f"| {i} | [{r.name}]({r.url}) | {r.overall_score:.1f}/5.0 "
            f"| {r.strongest_category} | {r.weakest_category} | {r.verdict} |"
        )
    lines.append("")

    # Executive summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(report.executive_summary)
    lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    for rec in report.recommendations:
        lines.append(f"- {rec}")
    lines.append("")

    # Individual analyses
    lines.append("---")
    lines.append("")
    for analysis in analyses:
        lines.append(generate_markdown_report(analysis))
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown report — committee synthesis
# ---------------------------------------------------------------------------
def generate_synthesis_markdown(
    synthesis: CommitteeSynthesis,
    analyses: list[HeroAnalysis],
) -> str:
    """Generate a markdown committee synthesis report."""
    lines: list[str] = []
    lines.append(f"# HeroCheck Committee Synthesis: {synthesis.url}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Personas:** {', '.join(synthesis.personas)}")
    lines.append("")

    # Score grid
    lines.append("## Score Grid")
    lines.append("")
    cat_labels = ["Value Prop", "Headline", "Layout", "CTA", "Social Proof"]
    header = "| Category | " + " | ".join(synthesis.personas) + " | Signal |"
    sep = "|----------|" + "|".join(["-------"] * len(synthesis.personas)) + "|--------|"
    lines.append(header)
    lines.append(sep)

    all_items = synthesis.consensus + synthesis.tensions
    for label in cat_labels:
        item = next((c for c in all_items if label.lower() in c.category.lower()), None)
        if item:
            scores = " | ".join(
                f"{'**' if item.signal == 'tension' else ''}"
                f"{item.scores.get(p, '?')}"
                f"{'**' if item.signal == 'tension' else ''}"
                for p in synthesis.personas
            )
            signal_emoji = {"consensus": "=", "tension": "!!", "split": "~"}.get(
                item.signal, "?"
            )
            lines.append(f"| {label} | {scores} | {signal_emoji} {item.signal} |")
        else:
            scores = " | ".join("?" for _ in synthesis.personas)
            lines.append(f"| {label} | {scores} | |")

    # Overall scores
    overall_scores = " | ".join(f"{a.overall_score:.1f}" for a in analyses)
    lines.append(f"| **Overall** | {overall_scores} | |")
    lines.append("")

    # Consensus
    if synthesis.consensus:
        lines.append("## Consensus (All Personas Agree)")
        lines.append("")
        for c in synthesis.consensus:
            scores_str = ", ".join(f"{p}: {s}" for p, s in c.scores.items())
            lines.append(f"### {c.category} ({scores_str})")
            lines.append("")
            lines.append(f"{c.insight}")
            lines.append("")

    # Tensions
    if synthesis.tensions:
        lines.append("## Tensions (Personas Disagree)")
        lines.append("")
        for t in synthesis.tensions:
            scores_str = ", ".join(f"{p}: {s}" for p, s in t.scores.items())
            lines.append(f"### {t.category} ({scores_str}) \u2014 spread: {t.spread}")
            lines.append("")
            lines.append(f"{t.insight}")
            lines.append("")

    # Who it's for / who it loses
    lines.append("## Persona Fit")
    lines.append("")
    lines.append(f"**Built for:** {synthesis.who_this_hero_is_for}")
    lines.append("")
    lines.append(f"**Loses:** {synthesis.who_it_loses}")
    lines.append("")

    # Priority actions
    lines.append("## Priority Actions (by committee impact)")
    lines.append("")
    for i, action in enumerate(synthesis.priority_actions, 1):
        lines.append(f"{i}. {action}")
    lines.append("")

    # Executive summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(synthesis.executive_summary)
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
def save_report(
    content: str, url: str, *, suffix: str = "", output_dir: Path | None = None,
) -> Path:
    """Save report to {output_dir}/{domain}{suffix}.md."""
    domain = _domain_slug(url)
    slug = suffix.lower().replace(" ", "_") if suffix else ""
    reports_dir = output_dir or Path.cwd() / "reports"
    reports_dir.mkdir(exist_ok=True)
    filepath = reports_dir / f"{domain}{slug}.md"
    filepath.write_text(content, encoding="utf-8")
    return filepath
