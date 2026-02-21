"""HeroCheck — B2B SaaS hero section analyzer.

Usage: python herocheck/agent.py <url>

Scrapes a webpage, analyzes the hero section across 5 categories,
and generates a scored markdown report.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Patch SDK to skip unknown message types (e.g. rate_limit_event)
# ---------------------------------------------------------------------------
import claude_agent_sdk._internal.client as _client
import claude_agent_sdk._internal.message_parser as _mp

_original_parse = _client.parse_message


def _patched_parse(data):
    try:
        return _original_parse(data)
    except _mp.MessageParseError:
        return None


_client.parse_message = _patched_parse

# ---------------------------------------------------------------------------
# Imports after patch
# ---------------------------------------------------------------------------
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query  # noqa: E402
from firecrawl import FirecrawlApp  # noqa: E402

from models import HeroAnalysis  # noqa: E402

# ---------------------------------------------------------------------------
# Firecrawl singleton
# ---------------------------------------------------------------------------
_firecrawl: FirecrawlApp | None = None


def get_firecrawl() -> FirecrawlApp:
    global _firecrawl
    if _firecrawl is None:
        api_key = os.environ.get("FIRECRAWL_API_KEY")
        if not api_key:
            print(
                "Fatal: FIRECRAWL_API_KEY environment variable is not set.",
                file=sys.stderr,
            )
            sys.exit(1)
        _firecrawl = FirecrawlApp(api_key=api_key)
    return _firecrawl


# ---------------------------------------------------------------------------
# Step 1 — Scrape
# ---------------------------------------------------------------------------
def scrape_page(url: str) -> str | None:
    """Scrape a URL via Firecrawl and return markdown content."""
    try:
        result = get_firecrawl().scrape(url, formats=["markdown"])
        if result and result.markdown:
            return result.markdown
        print(
            f"  [WARN] Firecrawl returned no markdown for {url}", file=sys.stderr
        )
        return None
    except Exception as e:
        print(f"  [WARN] Firecrawl error for {url}: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Step 2 — Analyze
# ---------------------------------------------------------------------------
ANALYSIS_PROMPT = """\
You are a B2B SaaS hero section analyst. Analyze the hero section of the webpage below and score it across 5 categories on a 1–5 scale.

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

## Instructions

- Focus ONLY on the hero section (the first visible viewport content above the fold)
- Extract the actual headline, subheadline, and CTA button text verbatim
- For each category, provide specific evidence from the page and a concrete recommendation
- List exactly 3 strengths and 3 improvements
- Calculate overall_score as the average of all 5 category scores (1 decimal place)
- Write a brief 2-3 sentence summary of the hero section's effectiveness

## Page Content

{page_content}

Return your analysis as structured JSON matching the requested schema.
"""


async def analyze_hero(url: str, page_content: str) -> HeroAnalysis | None:
    """Run the hero section analysis agent."""
    prompt = ANALYSIS_PROMPT.format(page_content=page_content)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        model="haiku",
        output_format={
            "type": "json_schema",
            "schema": HeroAnalysis.model_json_schema(),
        },
    )

    result_data = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage) and message.structured_output:
            result_data = message.structured_output

    if result_data:
        analysis = HeroAnalysis(**result_data)
        print(f"  [OK] Analysis complete — overall score: {analysis.overall_score}/5.0")
        return analysis

    print("  [FAIL] No structured output returned from agent", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Step 3 — Report
# ---------------------------------------------------------------------------
def star_bar(score: float, max_score: int = 5) -> str:
    """Render a score as filled/empty stars."""
    filled = round(score)
    return "\u2605" * filled + "\u2606" * (max_score - filled)


def generate_report(analysis: HeroAnalysis) -> str:
    """Generate a markdown report from the analysis."""
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


def save_report(report: str, url: str) -> Path:
    """Save the report to herocheck/reports/{domain}_{timestamp}.md."""
    domain = urlparse(url).netloc.replace("www.", "").replace(".", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    filepath = reports_dir / f"{domain}_{timestamp}.md"
    filepath.write_text(report, encoding="utf-8")
    return filepath


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    parser = argparse.ArgumentParser(
        description="HeroCheck — Analyze B2B SaaS hero sections"
    )
    parser.add_argument("url", help="URL of the page to analyze")
    args = parser.parse_args()

    url = args.url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Step 1 — Scrape
    print("[Step 1] Scraping page...")
    content = scrape_page(url)
    if not content:
        print("Fatal: Could not scrape page content.", file=sys.stderr)
        sys.exit(1)
    print(f"  [OK] Scraped {len(content)} characters")

    # Step 2 — Analyze
    print("[Step 2] Analyzing hero section...")
    analysis = await analyze_hero(url, content)
    if not analysis:
        print("Fatal: Analysis failed.", file=sys.stderr)
        sys.exit(1)

    # Step 3 — Report
    print("[Step 3] Generating report...")
    report = generate_report(analysis)
    filepath = save_report(report, url)
    print(f"  [OK] Report saved to {filepath}")


if __name__ == "__main__":
    asyncio.run(main())
