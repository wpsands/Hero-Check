# HeroCheck

Your hero section is a Rorschach test. Your CTO sees missing uptime SLAs. Your VP Marketing sees generic messaging with no proof points. Your senior engineer sees a beautiful page with no link to the docs. They're all looking at the same page — and they're all right.

HeroCheck simulates your buying committee. Define your buyer personas, point it at your hero section, and see exactly where each stakeholder would lean in or bounce. The output isn't a score — it's a committee briefing that shows you who your hero is built for and what you're giving up.

## Why This Exists

No hero speaks to every audience. A hero optimized for engineers will bore your VP Marketing. A hero optimized for marketers will make your engineer bounce. Most teams make this tradeoff accidentally. HeroCheck makes it intentional.

## How It Works

1. **Define your buying committee** — Write YAML personas for each stakeholder who has a say in the deal
2. **Point it at your hero** — Your URL, plus optionally a positioning doc for drift detection
3. **Each persona scores independently** — Claude role-plays as each buyer, scoring from their perspective with specific evidence
4. **The committee synthesizes** — All persona scores are analyzed together to surface:
   - **Consensus** — Where all personas agree (high-confidence strengths or gaps)
   - **Tensions** — Where they disagree (reveals who you're optimizing for)
   - **Who it's built for** — Which persona resonates most
   - **Who it loses** — Which persona would bounce
   - **Priority actions** — What to fix first, ranked by committee-wide impact

The synthesis is the product. Everything else is scaffolding to get there.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Set API keys
export FIRECRAWL_API_KEY=your-key-here
export ANTHROPIC_API_KEY=your-key-here

# Simulate your buying committee
herocheck yoursite.com --icp icps/

# Or run as a module
python -m herocheck yoursite.com --icp icps/

# Single persona
herocheck yoursite.com --icp icps/sample_cto.yaml

# With positioning drift detection
herocheck yoursite.com --icp icps/ --positioning sample_positioning.md
```

## Sample Personas

Three members of a buying committee at a 200-500 person Series B dev tools company:

| Persona | Role | Attack Angle |
|---------|------|-------------|
| Alex Chen | CTO | Build vs. buy. Skeptical by default. Looking for reasons to say no. |
| Marcus Rivera | Senior Engineer | Developer experience. The silent killer of every deal. Wants docs and code, not marketing. |
| Sarah Martinez | VP Marketing | Story and proof. If you can't sell yourself, how will she sell the integration? |

## Sample Output

```
================================================================
  HEROCHECK: twilio.com
  Alex Chen (CTO) + Marcus Rivera (Senior Engineer) + Sarah
  Martinez (VP Marketing)
================================================================

  VERDICT: Built for Sarah Martinez. Loses Alex Chen.

  CATEGORY              Alex  Marcus   Sarah  SIGNAL
  ------------------------------------------------------------
  X Value Prop             3       3       3  consensus
  X Headline               2       2       2  consensus
  + Layout                 4       4       4  consensus
  + CTA                    4       4       4  consensus
  ! Social Proof           1       3       3  tension
  ------------------------------------------------------------
  OVERALL                2.8     3.2     3.2

  FIX FIRST (by committee impact)
    1. Replace the generic headline with a specific, quantified statement.
    2. Move social proof and trust signals above the fold.
    3. Clarify the value prop with concrete, developer-friendly capabilities.
```

## CLI Flags

```
herocheck <url> [options]

--icp PATH             Persona file (YAML) or directory for committee simulation
--positioning PATH     Positioning doc (markdown) for drift detection
--no-screenshot        Skip screenshot capture (text-only analysis)
--headline TEXT         Override hero headline (DOM order fix)
--model haiku|sonnet|opus  Model selection (default: sonnet)
--vs URL [URL ...]     Competitor URLs for comparison
```

## Writing Your Own Personas

Create a YAML file per committee member:

```yaml
name: Alex Chen
title: CTO
industry: B2B SaaS
company_size: 200-500 employees
description: Technical decision-maker. Skeptical by default.
priorities:
  - Reducing time engineers spend on infrastructure
  - System reliability and uptime guarantees
  - Minimizing vendor lock-in
pain_points:
  - Burned by a vendor last year
  - Every new vendor adds cognitive load
  - Hard to justify spend without clear productivity gains
trust_signals:
  - Public status page with real incident history
  - Open-source SDKs on GitHub
  - Named engineering teams at similar-scale companies
```

The persona's priorities, pain points, and trust signals are injected directly into the scoring prompt. Different personas = different scores = the tension that makes this useful.

## Architecture

```
herocheck/
├── __init__.py        # Package version
├── __main__.py        # python -m herocheck
├── cli.py             # CLI entry point + orchestration
├── models.py          # Pydantic models
├── scraper.py         # Firecrawl scraping + screenshots
├── analyzer.py        # Anthropic API (tool_use structured output + retries)
├── prompt.py          # Composable prompt builder
├── report.py          # Markdown report generation
├── display.py         # Terminal display
icps/                  # Sample buyer personas
sample_positioning.md  # Example positioning document
tests/                 # Test suite
reports/               # Generated reports (gitignored)
```

Key design decisions:
- **Tool-use structured output** — Forces Claude to return data via a tool call matching the Pydantic schema, eliminating JSON parsing failures
- **Parallel execution** — All persona × URL analyses run concurrently via ThreadPoolExecutor
- **Retry with backoff** — Transient API errors (rate limits, 500s) retry automatically
- **Composable prompts** — Persona, positioning, and rubric segments combine cleanly

## Requirements

- Python 3.10+
- [Firecrawl API key](https://firecrawl.dev) for web scraping + screenshots
- [Anthropic API key](https://console.anthropic.com) for Claude analysis

## Running Tests

```bash
pip install -e ".[dev]"
pytest -v
```

## License

MIT
