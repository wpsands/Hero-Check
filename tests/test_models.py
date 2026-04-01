"""Tests for HeroCheck data models."""

import pytest

from herocheck.models import (
    CategoryScore,
    CompetitiveReport,
    CompetitorRanking,
    HeroAnalysis,
    ICPProfile,
    PositioningCheck,
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


class TestICPProfile:
    def test_minimal(self):
        icp = ICPProfile(
            name="Test",
            title="CTO",
            industry="Tech",
            priorities=["Speed"],
            pain_points=["Cost"],
            trust_signals=["Logos"],
        )
        assert icp.name == "Test"
        assert icp.company_size == ""
        assert icp.description == ""

    def test_full(self):
        icp = ICPProfile(
            name="Alex",
            title="CISO",
            industry="Finance",
            company_size="1000+",
            priorities=["Security", "Compliance"],
            pain_points=["Tool sprawl"],
            trust_signals=["SOC 2"],
            description="Enterprise CISO",
        )
        assert icp.company_size == "1000+"


class TestPositioningCheck:
    def test_creates(self):
        pc = PositioningCheck(
            alignment_score=4,
            hero_message="We secure identities",
            positioning_message="Autonomous identity governance",
            drift_details="Hero is more generic",
            recommendation="Be more specific about autonomous capabilities",
        )
        assert pc.alignment_score == 4


class TestHeroAnalysisV2:
    def test_backwards_compatible(self):
        a = _make_analysis()
        assert a.persona_name is None
        assert a.positioning_check is None
        assert a.layout_source == "markdown"

    def test_with_persona(self):
        a = _make_analysis(persona_name="Alex Chen")
        assert a.persona_name == "Alex Chen"

    def test_with_positioning(self):
        pc = PositioningCheck(
            alignment_score=3,
            hero_message="msg",
            positioning_message="pos",
            drift_details="drift",
            recommendation="rec",
        )
        a = _make_analysis(positioning_check=pc)
        assert a.positioning_check.alignment_score == 3

    def test_with_screenshot_source(self):
        a = _make_analysis(layout_source="screenshot")
        assert a.layout_source == "screenshot"


class TestCompetitiveReport:
    def test_creates(self):
        r = CompetitiveReport(
            persona_name="Alex",
            rankings=[
                CompetitorRanking(
                    url="https://a.com",
                    name="A Corp",
                    overall_score=4.2,
                    strongest_category="CTA",
                    weakest_category="Social Proof",
                    verdict="Strong contender",
                )
            ],
            executive_summary="A wins.",
            recommendations=["Improve social proof"],
        )
        assert len(r.rankings) == 1
        assert r.rankings[0].overall_score == 4.2
