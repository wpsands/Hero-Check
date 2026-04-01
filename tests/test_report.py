"""Tests for report generation (markdown)."""

import pytest

from herocheck.models import (
    CategoryScore,
    CompetitiveReport,
    CompetitorRanking,
    HeroAnalysis,
    PositioningCheck,
)
from herocheck.report import (
    generate_comparison_markdown,
    generate_markdown_report,
    star_bar,
)


def _make_category(category: str, score: int) -> CategoryScore:
    return CategoryScore(
        category=category,
        score=score,
        evidence=f"Evidence for {category}",
        recommendation=f"Recommendation for {category}",
    )


def _make_analysis(**overrides) -> HeroAnalysis:
    defaults = dict(
        url="https://example.com",
        headline="Test Headline",
        subheadline="Test Sub",
        cta_text="Get Started",
        value_prop_score=_make_category("Value Prop", 4),
        headline_score=_make_category("Headline", 3),
        layout_score=_make_category("Layout", 4),
        cta_score=_make_category("CTA", 5),
        social_proof_score=_make_category("Social Proof", 2),
        overall_score=3.6,
        strengths=["A", "B", "C"],
        improvements=["X", "Y", "Z"],
        summary="Test summary.",
    )
    defaults.update(overrides)
    return HeroAnalysis(**defaults)


class TestMarkdownReport:
    def test_basic_sections(self):
        report = generate_markdown_report(_make_analysis())
        assert "## Overall Score" in report
        assert "## Scorecard" in report
        assert "## Summary" in report

    def test_persona_shown(self):
        report = generate_markdown_report(_make_analysis(persona_name="Alex"))
        assert "**Persona:** Alex" in report

    def test_no_persona_no_line(self):
        report = generate_markdown_report(_make_analysis())
        assert "**Persona:**" not in report

    def test_positioning_drift(self):
        pc = PositioningCheck(
            alignment_score=3,
            hero_message="hero",
            positioning_message="pos",
            drift_details="drift info",
            recommendation="fix it",
        )
        report = generate_markdown_report(_make_analysis(positioning_check=pc))
        assert "Positioning Drift Check" in report
        assert "drift info" in report

    def test_layout_source_shown(self):
        report = generate_markdown_report(_make_analysis(layout_source="screenshot"))
        assert "screenshot" in report


class TestComparisonMarkdown:
    def test_rankings_table(self):
        comp = CompetitiveReport(
            persona_name="Alex",
            rankings=[
                CompetitorRanking(
                    url="https://a.com", name="A", overall_score=4.0,
                    strongest_category="CTA", weakest_category="Social",
                    verdict="Good",
                ),
            ],
            executive_summary="A is best.",
            recommendations=["Do X"],
        )
        report = generate_comparison_markdown(comp, [_make_analysis()])
        assert "Rankings" in report
        assert "A" in report
        assert "Executive Summary" in report
