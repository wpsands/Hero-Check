"""Tests for prompt builder."""

import pytest

from herocheck.models import ICPProfile
from herocheck.prompt import build_analysis_prompt, build_comparison_prompt


@pytest.fixture
def sample_icp() -> ICPProfile:
    return ICPProfile(
        name="Alex Chen",
        title="CISO",
        industry="Financial Services",
        company_size="2,000-10,000",
        priorities=["Zero trust", "Compliance"],
        pain_points=["Tool sprawl", "Alert fatigue"],
        trust_signals=["SOC 2", "Gartner recognition"],
    )


class TestBuildAnalysisPrompt:
    def test_basic_prompt(self):
        prompt = build_analysis_prompt("https://example.com", "# Hello World")
        assert "https://example.com" in prompt
        assert "# Hello World" in prompt
        assert "Scoring Rubric" in prompt
        assert "DOM Order" in prompt

    def test_with_persona(self, sample_icp):
        prompt = build_analysis_prompt(
            "https://example.com", "content", icp=sample_icp
        )
        assert "Alex Chen" in prompt
        assert "CISO" in prompt
        assert "Zero trust" in prompt
        assert "persona_name" in prompt

    def test_with_positioning(self):
        prompt = build_analysis_prompt(
            "https://example.com",
            "content",
            positioning_content="We are the best at X",
        )
        assert "Positioning Document" in prompt
        assert "We are the best at X" in prompt
        assert "positioning_check" in prompt

    def test_with_headline_override(self):
        prompt = build_analysis_prompt(
            "https://example.com", "content", headline="My Override"
        )
        assert "My Override" in prompt
        assert "User-confirmed headline" in prompt

    def test_with_screenshot(self):
        prompt = build_analysis_prompt(
            "https://example.com", "content", has_screenshot=True
        )
        assert "Screenshot" in prompt
        assert "screenshot" in prompt.lower()
        assert "layout_source" in prompt

    def test_no_persona_no_persona_instruction(self):
        prompt = build_analysis_prompt("https://example.com", "content")
        assert "persona_name" not in prompt

    def test_no_positioning_no_positioning_instruction(self):
        prompt = build_analysis_prompt("https://example.com", "content")
        assert "positioning_check" not in prompt


class TestBuildComparisonPrompt:
    def test_basic(self, sample_icp):
        prompt = build_comparison_prompt(
            analyses_json='[{"url": "https://a.com"}]',
            primary_url="https://a.com",
            persona_name="Alex Chen",
            icp=sample_icp,
        )
        assert "Alex Chen" in prompt
        assert "https://a.com" in prompt
        assert "competitive" in prompt.lower() or "Rankings" in prompt or "rankings" in prompt

    def test_without_icp(self):
        prompt = build_comparison_prompt(
            analyses_json="[]",
            primary_url="https://a.com",
            persona_name="Generic Buyer",
        )
        assert "Generic Buyer" in prompt
