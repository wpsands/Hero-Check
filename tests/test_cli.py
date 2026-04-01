"""Tests for HeroCheck CLI utilities."""

import pytest

from herocheck.cli import _validate_url
from herocheck.models import HeroAnalysis, CategoryScore
from herocheck.report import star_bar, generate_markdown_report, save_report


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _make_category(category: str, score: int) -> CategoryScore:
    return CategoryScore(
        category=category,
        score=score,
        evidence=f"Evidence for {category}",
        recommendation=f"Recommendation for {category}",
    )


@pytest.fixture
def sample_analysis() -> HeroAnalysis:
    return HeroAnalysis(
        url="https://example.com",
        headline="Ship faster with AI",
        subheadline="The platform for modern teams",
        cta_text="Get Started Free",
        value_prop_score=_make_category("Clarity of Value Prop", 4),
        headline_score=_make_category("Headline Copy", 3),
        layout_score=_make_category("Visual Hierarchy", 4),
        cta_score=_make_category("CTA Effectiveness", 5),
        social_proof_score=_make_category("Social Proof", 2),
        overall_score=3.6,
        strengths=["Strong CTA", "Clear value prop", "Clean layout"],
        improvements=["Add social proof", "Sharpen headline", "Add urgency"],
        summary="A solid hero section with room for improvement in social proof.",
    )


# ---------------------------------------------------------------------------
# star_bar
# ---------------------------------------------------------------------------
class TestStarBar:
    def test_full_score(self):
        assert star_bar(5) == "\u2605\u2605\u2605\u2605\u2605"

    def test_zero_score(self):
        assert star_bar(0) == "\u2606\u2606\u2606\u2606\u2606"

    def test_partial_score(self):
        result = star_bar(3)
        assert result == "\u2605\u2605\u2605\u2606\u2606"

    def test_rounds_half_up(self):
        result = star_bar(3.5)
        assert result.count("\u2605") == 4

    def test_custom_max(self):
        result = star_bar(2, max_score=3)
        assert result == "\u2605\u2605\u2606"


# ---------------------------------------------------------------------------
# validate_url
# ---------------------------------------------------------------------------
class TestValidateUrl:
    def test_adds_https(self):
        assert _validate_url("example.com") == "https://example.com"

    def test_preserves_existing_scheme(self):
        assert _validate_url("https://example.com") == "https://example.com"

    def test_preserves_http(self):
        assert _validate_url("http://example.com") == "http://example.com"

    def test_strips_whitespace(self):
        assert _validate_url("  example.com  ") == "https://example.com"

    def test_rejects_invalid_url(self):
        with pytest.raises(SystemExit):
            _validate_url("not a url !!!")


# ---------------------------------------------------------------------------
# generate_markdown_report
# ---------------------------------------------------------------------------
class TestGenerateReport:
    def test_contains_url(self, sample_analysis):
        report = generate_markdown_report(sample_analysis)
        assert "https://example.com" in report

    def test_contains_headline(self, sample_analysis):
        report = generate_markdown_report(sample_analysis)
        assert "Ship faster with AI" in report

    def test_contains_overall_score(self, sample_analysis):
        report = generate_markdown_report(sample_analysis)
        assert "3.6 / 5.0" in report

    def test_contains_all_sections(self, sample_analysis):
        report = generate_markdown_report(sample_analysis)
        for section in [
            "## Overall Score",
            "## Extracted Elements",
            "## Scorecard",
            "## Strengths",
            "## Areas for Improvement",
            "## Detailed Recommendations",
            "## Summary",
        ]:
            assert section in report

    def test_contains_strengths(self, sample_analysis):
        report = generate_markdown_report(sample_analysis)
        assert "- Strong CTA" in report

    def test_scorecard_table(self, sample_analysis):
        report = generate_markdown_report(sample_analysis)
        assert "| Category | Score | Evidence |" in report
        assert "Clarity of Value Prop" in report


# ---------------------------------------------------------------------------
# save_report
# ---------------------------------------------------------------------------
class TestSaveReport:
    def test_saves_to_disk(self, sample_analysis, tmp_path):
        filepath = save_report(
            "# Test Report", "https://example.com", output_dir=tmp_path,
        )
        assert filepath.exists()
        assert filepath.read_text() == "# Test Report"
        assert "example_com" in filepath.name

    def test_with_suffix(self, tmp_path):
        filepath = save_report(
            "content", "https://example.com", suffix="_alex_chen", output_dir=tmp_path,
        )
        assert "_alex_chen" in filepath.name


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------
class TestHeroAnalysis:
    def test_rejects_missing_fields(self):
        with pytest.raises(Exception):
            HeroAnalysis(url="https://example.com")

    def test_accepts_valid_data(self, sample_analysis):
        assert sample_analysis.url == "https://example.com"
        assert sample_analysis.overall_score == 3.6
        assert len(sample_analysis.strengths) == 3
        assert len(sample_analysis.improvements) == 3
