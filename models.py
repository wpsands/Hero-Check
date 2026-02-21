"""Pydantic models for HeroCheck scoring output."""

from pydantic import BaseModel


class CategoryScore(BaseModel):
    category: str
    score: int  # 1-5
    evidence: str  # what was observed
    recommendation: str  # how to improve


class HeroAnalysis(BaseModel):
    url: str
    headline: str  # the actual headline text found
    subheadline: str  # subheadline if present
    cta_text: str  # CTA button text found
    value_prop_score: CategoryScore
    headline_score: CategoryScore
    layout_score: CategoryScore
    cta_score: CategoryScore
    social_proof_score: CategoryScore
    overall_score: float  # average 1.0-5.0
    strengths: list[str]  # top 3 things done well
    improvements: list[str]  # top 3 things to fix
    summary: str  # brief narrative
