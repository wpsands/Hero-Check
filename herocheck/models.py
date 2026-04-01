"""Pydantic models for HeroCheck scoring output."""

from pydantic import BaseModel


class CategoryScore(BaseModel):
    category: str
    score: int  # 1-5
    evidence: str  # what was observed
    recommendation: str  # how to improve


class ICPProfile(BaseModel):
    name: str
    title: str
    industry: str
    company_size: str = ""
    priorities: list[str]
    pain_points: list[str]
    trust_signals: list[str]
    description: str = ""


class PositioningCheck(BaseModel):
    alignment_score: int  # 1-5
    hero_message: str  # what the hero communicates
    positioning_message: str  # what the doc says
    drift_details: str  # where they diverge
    recommendation: str


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
    persona_name: str | None = None
    positioning_check: PositioningCheck | None = None
    layout_source: str = "markdown"  # "markdown" or "screenshot"


class CategoryConsensus(BaseModel):
    category: str
    scores: dict[str, int]  # persona_name -> score
    spread: int  # max - min score
    signal: str  # "consensus", "tension", or "split"
    insight: str  # what the agreement/disagreement means


class CommitteeSynthesis(BaseModel):
    url: str
    personas: list[str]
    consensus: list[CategoryConsensus]  # categories where personas agree
    tensions: list[CategoryConsensus]  # categories where personas disagree
    priority_actions: list[str]  # what to fix first, ordered by committee impact
    who_this_hero_is_for: str  # which persona it resonates with most
    who_it_loses: str  # which persona it repels
    executive_summary: str  # 2-3 paragraph synthesis


class CompetitorRanking(BaseModel):
    url: str
    name: str
    overall_score: float
    strongest_category: str
    weakest_category: str
    verdict: str  # one-line persona reaction


class CompetitiveReport(BaseModel):
    persona_name: str
    rankings: list[CompetitorRanking]
    executive_summary: str
    recommendations: list[str]  # actionable for primary URL
