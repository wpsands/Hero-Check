# Hero-Check

Analyze any B2B SaaS hero section in 30 seconds. Get a scored report with specific strengths, weaknesses, and fixes.

## The Problem

Your hero section is the first thing prospects see. If the headline is vague, the CTA is weak, or the value prop is buried, visitors bounce before they scroll. Most teams guess whether their hero is working. This tool measures it.

## What It Does

1. **Scrapes** the target URL using Firecrawl
2. **Analyzes** the hero section across 5 scoring categories using Claude
3. **Generates** a scored markdown report with evidence for every rating

## Scoring Categories

Each category is scored 1-5 with specific evidence from the page:

| Category | What It Measures |
|----------|-----------------|
| Value Prop Clarity | Can a visitor understand what you do in 5 seconds? |
| Headline | Is it specific, benefit-driven, and differentiated? |
| Layout | Is the visual hierarchy guiding attention to the right elements? |
| CTA | Is the call to action clear, compelling, and low-friction? |
| Social Proof | Are trust signals present and credible? |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set your Firecrawl API key
export FIRECRAWL_API_KEY=your-key-here

# Analyze a site
python herocheck/agent.py 6sense.com
```

Reports are saved to `reports/{domain}_{timestamp}.md`.

## Example Output

```
Overall Score: 3.8/5.0  ★★★★☆

Extracted Hero Elements:
  Headline:    "Revenue AI for the enterprise"
  Subheadline: "Identify accounts, engage buyers, close deals"
  CTA:         "Get a demo"

Scorecard:
  Value Prop Clarity    4/5  Clear enterprise focus, specific to revenue teams
  Headline              3/5  Benefit implied but not quantified
  Layout                4/5  Clean hierarchy, CTA above fold
  CTA                   4/5  Direct, low friction, single action
  Social Proof          4/5  Logo bar with recognizable brands
```

## Requirements

- Python 3.10+
- [Firecrawl API key](https://firecrawl.dev) for web scraping
- Anthropic API key (used via Claude Agent SDK)

## Dependencies

```
claude-agent-sdk
firecrawl-py
pydantic
```

## License

MIT
