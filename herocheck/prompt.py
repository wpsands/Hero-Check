"""Composable prompt builder for HeroCheck analysis."""

from herocheck.models import ICPProfile


# ---------------------------------------------------------------------------
# Segment A — Persona
# ---------------------------------------------------------------------------
def build_persona_segment(icp: ICPProfile) -> str:
    priorities = "\n".join(f"- {p}" for p in icp.priorities)
    pain_points = "\n".join(f"- {p}" for p in icp.pain_points)
    trust_signals = "\n".join(f"- {t}" for t in icp.trust_signals)

    return f"""\
## Your Persona

You are **{icp.name}**, a **{icp.title}** in **{icp.industry}**{f' ({icp.company_size})' if icp.company_size else ''}.
You are evaluating this landing page as a potential buyer.

**Your priorities:**
{priorities}

**Your pain points:**
{pain_points}

**Trust signals you look for:**
{trust_signals}

Score every category through YOUR eyes as this buyer. A "5" means
this hero would immediately resonate with you. A "1" means you'd bounce.
Explain your scores from this persona's perspective — e.g., "As a CISO, I need to see..."
"""


# ---------------------------------------------------------------------------
# Segment B — Positioning
# ---------------------------------------------------------------------------
def build_positioning_segment(positioning_content: str) -> str:
    return f"""\
## Positioning Document

Compare the hero section against this positioning document.
Identify any drift between what the hero communicates and what the positioning says.
Fill in the positioning_check field in your output.

{positioning_content}
"""


# ---------------------------------------------------------------------------
# Segment C — Rubric (always present)
# ---------------------------------------------------------------------------
RUBRIC = """\
## Scoring Rubric

### 1. Clarity of Value Prop (value_prop_score)
- **5**: Immediately obvious what the product does and who it's for; benefit is front-and-center
- **4**: Clear value prop with minor ambiguity
- **3**: Value prop present but requires effort to parse
- **2**: Vague or jargon-heavy; unclear benefit
- **1**: No discernible value proposition

### 2. Headline Copy (headline_score)
- **5**: Compelling, specific, differentiated; creates urgency or curiosity
- **4**: Strong headline with minor room for improvement
- **3**: Generic but functional ("The platform for X")
- **2**: Bland, forgettable, or confusing
- **1**: Missing or completely unclear

### 3. Visual Hierarchy / Layout Description (layout_score)
- **5**: Clear information flow; eye naturally guided from headline → subhead → CTA
- **4**: Good structure with minor issues
- **3**: Acceptable but some elements compete for attention
- **2**: Cluttered or confusing layout
- **1**: No clear visual hierarchy

### 4. CTA Effectiveness (cta_score)
- **5**: Clear, action-oriented, compelling CTA; well-placed and visually prominent
- **4**: Good CTA with minor improvements possible
- **3**: Generic CTA ("Learn More", "Get Started") with okay placement
- **2**: Weak, hidden, or confusing CTA
- **1**: No CTA present or completely ineffective

### 5. Social Proof / Trust Signals (social_proof_score)
- **5**: Strong proof — customer logos, specific stats, named testimonials visible in hero
- **4**: Good proof present (logos or a quote)
- **3**: Minimal proof (e.g., "Trusted by 1000+ companies" with no specifics)
- **2**: Very weak or generic claims
- **1**: No social proof or trust signals in the hero area
"""

DOM_ORDER_WARNING = """\
## Important: DOM Order vs. Visual Layout

The page content below is in DOM source order, which may NOT match the visual layout.
Modern websites use CSS positioning, JavaScript rendering, and dynamic content to display
elements in a different order than they appear in the HTML source. The true hero headline
may appear further down in the source but be visually positioned at the top of the page.
Do NOT assume the first heading in the source is the hero headline. Look for contextual
clues (e.g., CTA buttons nearby, subheadlines, background image references) to identify
the actual above-the-fold hero section.
"""


def build_analysis_prompt(
    url: str,
    page_content: str,
    *,
    icp: ICPProfile | None = None,
    positioning_content: str | None = None,
    headline: str | None = None,
    has_screenshot: bool = False,
) -> str:
    """Build the full analysis prompt from composable segments."""
    parts: list[str] = []

    parts.append(
        "You are a B2B SaaS hero section analyst. Analyze the hero section of the "
        "webpage below and score it across 5 categories on a 1\u20135 scale."
    )
    parts.append("")

    # Segment A — Persona
    if icp:
        parts.append(build_persona_segment(icp))

    # Segment C — Rubric (always)
    parts.append(RUBRIC)
    parts.append(DOM_ORDER_WARNING)

    # Headline override
    if headline:
        parts.append(
            f'**User-confirmed headline:** The actual hero headline is: '
            f'"{headline}". Use this as the definitive headline for your analysis.\n'
        )

    # Screenshot instruction
    if has_screenshot:
        parts.append(
            "## Screenshot\n\n"
            "A screenshot of the page is provided. Score layout based on what you "
            "SEE \u2014 visual hierarchy, whitespace, CTA prominence, contrast. This is "
            "more reliable than inferring layout from markdown.\n"
        )

    # Segment B — Positioning
    if positioning_content:
        parts.append(build_positioning_segment(positioning_content))

    # Instructions
    positioning_instruction = ""
    if positioning_content:
        positioning_instruction = (
            "- Fill in the positioning_check field comparing hero vs. positioning document\n"
        )
    persona_instruction = ""
    if icp:
        persona_instruction = f'- Set persona_name to "{icp.name}"\n'

    parts.append(f"""\
## Instructions

- Focus ONLY on the hero section (the first visible viewport content above the fold)
- Extract the actual headline, subheadline, and CTA button text verbatim
- For each category, provide specific evidence from the page and a concrete recommendation
- List exactly 3 strengths and 3 improvements
- Calculate overall_score as the average of all 5 category scores (1 decimal place)
- Write a brief 2-3 sentence summary of the hero section's effectiveness
- Set the "url" field to exactly: {url}
{persona_instruction}{positioning_instruction}{'- Set layout_source to "screenshot"' if has_screenshot else '- Set layout_source to "markdown"'}

## Page Content

{page_content}

Record your analysis using the provided tool.""")

    return "\n".join(parts)


SYNTHESIS_PROMPT = """\
You are a B2B SaaS buying committee analyst. You have been given hero section analyses \
of the same webpage scored by multiple buyer personas \u2014 members of the same buying committee \
at the same company.

## Persona Analyses

{analyses_json}

## Instructions

Synthesize these perspectives into a single committee-level assessment for {url}.

1. **Consensus**: Identify categories where all personas score within 1 point of each other. \
These are high-confidence signals \u2014 the hero is genuinely strong or weak here regardless of \
who's looking. For each, explain WHY they agree.

2. **Tensions**: Identify categories where scores differ by 2+ points. These reveal who the \
hero is optimized for and who it alienates. For each, explain the disagreement from both sides.

3. **For each category** (value_prop, headline, layout, cta, social_proof): create a \
CategoryConsensus entry with:
   - scores: mapping of persona name to their score
   - spread: difference between highest and lowest score
   - signal: "consensus" if spread <= 1, "tension" if spread >= 2, "split" if in between
   - insight: one sentence explaining what the agreement or disagreement reveals

4. **Priority Actions**: 3-5 actions ordered by committee-wide impact. Actions that fix a \
consensus weakness (everyone agrees it's bad) rank higher than actions that resolve a tension \
(some think it's fine). Frame each action in terms of committee dynamics: "This fix satisfies \
both your CTO and your engineer" or "This trades headline appeal for your VP Marketing \
against technical credibility for your CTO."

5. **Who this hero is for**: Which persona does it resonate with most, and why?

6. **Who it loses**: Which persona would bounce, and why?

7. **Executive Summary**: 2-3 paragraphs synthesizing the committee's view. Lead with \
consensus, then tensions, then the key insight about who the hero is built for.

Place consensus items (spread <= 1) in the "consensus" list and tension items (spread >= 2) \
in the "tensions" list. Items with spread of exactly 1 go in consensus.

Record your synthesis using the provided tool.
"""


def build_synthesis_prompt(
    analyses_json: str,
    url: str,
) -> str:
    """Build the committee synthesis prompt."""
    return SYNTHESIS_PROMPT.format(
        analyses_json=analyses_json,
        url=url,
    )


COMPARISON_PROMPT = """\
You are a B2B SaaS competitive analyst. You have been given individual hero section \
analyses for multiple websites, all scored through the same buyer persona's eyes.

{persona_context}

## Individual Analyses

{analyses_json}

## Instructions

Produce a competitive comparison report:

1. **Rankings**: Rank all URLs from best to worst overall_score. For each, identify:
   - The company name (extract from URL or analysis)
   - Their strongest and weakest scoring category
   - A one-line verdict as this persona would say it (e.g., "This speaks my language \u2014 I'd click through")

2. **Executive Summary**: 2-3 paragraphs comparing how these hero sections stack up through this persona's eyes. What patterns do you see? Who wins and why?

3. **Recommendations**: 3-5 specific, actionable recommendations for the PRIMARY URL ({primary_url}) to outperform competitors.

Set persona_name to "{persona_name}".

Record your comparison using the provided tool.
"""


def build_comparison_prompt(
    analyses_json: str,
    primary_url: str,
    persona_name: str,
    icp: ICPProfile | None = None,
) -> str:
    """Build the competitive comparison prompt."""
    persona_context = ""
    if icp:
        persona_context = build_persona_segment(icp)

    return COMPARISON_PROMPT.format(
        persona_context=persona_context,
        analyses_json=analyses_json,
        primary_url=primary_url,
        persona_name=persona_name,
    )
