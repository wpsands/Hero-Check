"""HeroCheck CLI — simulate your buying committee against any hero section.

Usage:
    python -m herocheck <url> --icp icps/
    herocheck <url> --icp icps/
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import yaml
from dotenv import load_dotenv

from herocheck.analyzer import (
    analyze_hero,
    compare_heroes,
    run_parallel,
    synthesize_committee,
)
from herocheck.display import print_single_analysis, print_synthesis
from herocheck.models import HeroAnalysis, ICPProfile
from herocheck.report import (
    generate_comparison_markdown,
    generate_markdown_report,
    generate_synthesis_markdown,
    save_report,
)
from herocheck.scraper import scrape_pages


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HeroCheck \u2014 Simulate your buying committee against any hero section",
    )
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument(
        "--model",
        default="sonnet",
        choices=["haiku", "sonnet", "opus"],
        help="Claude model (default: sonnet)",
    )
    parser.add_argument("--headline", default=None, help="Override hero headline")
    parser.add_argument(
        "--icp", default=None, help="Persona YAML file or directory",
    )
    parser.add_argument(
        "--positioning", default=None, help="Positioning doc (markdown) for drift detection",
    )
    parser.add_argument(
        "--vs", nargs="+", default=None, help="Competitor URLs for comparison",
    )
    parser.add_argument(
        "--no-screenshot", action="store_true", help="Skip screenshot capture",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _check_env() -> None:
    missing = [k for k in ("FIRECRAWL_API_KEY", "ANTHROPIC_API_KEY") if not os.environ.get(k)]
    if missing:
        print(f"Fatal: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


def _validate_url(raw: str) -> str:
    url = raw.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    if not parsed.netloc or not re.match(
        r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", parsed.netloc,
    ):
        print(f"Fatal: Invalid URL: {raw}", file=sys.stderr)
        sys.exit(1)
    return url


def _domain_short(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "").split(".")[0]


def _persona_slug(name: str) -> str:
    return "_" + name.lower().replace(" ", "_")


def _load_icps(path: str) -> list[ICPProfile]:
    p = Path(path)
    if p.is_dir():
        files = sorted(p.glob("*.yaml")) + sorted(p.glob("*.yml"))
        if not files:
            print(f"Fatal: No YAML files in {path}", file=sys.stderr)
            sys.exit(1)
        return [_parse_icp(f) for f in files]
    return [_parse_icp(p)]


def _parse_icp(filepath: Path) -> ICPProfile:
    with open(filepath, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ICPProfile(**data)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    load_dotenv(override=True)
    args = _parse_args()
    _check_env()

    url = _validate_url(args.url)
    icps = _load_icps(args.icp) if args.icp else []
    positioning = (
        Path(args.positioning).read_text(encoding="utf-8") if args.positioning else None
    )

    if icps:
        print(
            f"[Committee] {', '.join(f'{p.name} ({p.title})' for p in icps)}"
        )

    # Collect all URLs
    all_urls = [url]
    competitor_slugs: list[str] = []
    if args.vs:
        for u in args.vs:
            v = _validate_url(u)
            all_urls.append(v)
            competitor_slugs.append(_domain_short(v))

    total_steps = 4 if len(icps) >= 2 else 3

    # -----------------------------------------------------------------------
    # Step 1: Scrape all pages in parallel
    # -----------------------------------------------------------------------
    print(f"\n[1/{total_steps}] Scraping {len(all_urls)} page(s)...")
    scrapes = scrape_pages(all_urls, screenshot=not args.no_screenshot)
    valid = {}
    for sr in scrapes:
        if sr.markdown:
            valid[sr.url] = sr
            extra = " + screenshot" if sr.screenshot_b64 else ""
            print(f"  [OK] {sr.url} \u2014 {len(sr.markdown):,} chars{extra}")
        else:
            print(f"  [FAIL] {sr.url}", file=sys.stderr)

    if url not in valid:
        print("Fatal: Could not scrape primary URL.", file=sys.stderr)
        sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 2: Analyze all persona × URL combinations in parallel
    # -----------------------------------------------------------------------
    icps_to_run: list[ICPProfile | None] = icps if icps else [None]

    tasks: list[dict] = []
    task_meta: list[tuple[ICPProfile | None, str]] = []
    for icp in icps_to_run:
        for scrape_url, sr in valid.items():
            tasks.append(dict(
                url=scrape_url,
                page_content=sr.markdown,
                model=args.model,
                headline=args.headline if scrape_url == url else None,
                icp=icp,
                positioning_content=positioning if scrape_url == url else None,
                screenshot_b64=sr.screenshot_b64,
            ))
            task_meta.append((icp, scrape_url))

    n = len(tasks)
    print(f"\n[2/{total_steps}] Scoring {n} analysis{'es' if n != 1 else ''} in parallel...")

    analyses = run_parallel(analyze_hero, tasks, max_workers=min(n, 6))

    for i, analysis in enumerate(analyses):
        icp_item, scrape_url = task_meta[i]
        persona = icp_item.name if icp_item else "Generic"
        domain = urlparse(scrape_url).netloc
        if analysis:
            print(f"  [{i + 1}/{n}] {domain} as {persona} \u2014 {analysis.overall_score:.1f}/5")
        else:
            print(f"  [{i + 1}/{n}] {domain} as {persona} \u2014 FAIL", file=sys.stderr)

    # Group results by persona
    by_persona: dict[str, list[HeroAnalysis]] = defaultdict(list)
    persona_icps: dict[str, ICPProfile | None] = {}
    for i, analysis in enumerate(analyses):
        if analysis:
            icp_item, _ = task_meta[i]
            key = icp_item.name if icp_item else "Generic"
            by_persona[key].append(analysis)
            persona_icps[key] = icp_item

    # -----------------------------------------------------------------------
    # Step 3: Generate per-persona reports
    # -----------------------------------------------------------------------
    vs_slug = "_vs_" + "_".join(competitor_slugs) if competitor_slugs else ""
    print(f"\n[3/{total_steps}] Saving reports...")

    for persona_name, persona_analyses in by_persona.items():
        suffix = _persona_slug(persona_name) if persona_name != "Generic" else ""

        if args.vs and len(persona_analyses) > 1:
            icp_item = persona_icps[persona_name]
            comparison = compare_heroes(
                persona_analyses, url, model=args.model, icp=icp_item,
            )
            if comparison:
                content = generate_comparison_markdown(comparison, persona_analyses)
                fp = save_report(content, url, suffix=f"{vs_slug}{suffix}")
                print(f"  {fp.name}")
        else:
            content = generate_markdown_report(persona_analyses[0])
            fp = save_report(content, url, suffix=suffix)
            print(f"  {fp.name}")

    # -----------------------------------------------------------------------
    # Step 4: Committee synthesis (2+ personas)
    # -----------------------------------------------------------------------
    if len(icps) >= 2:
        primary = [a for a in analyses if a and a.url == url]
        if len(primary) >= 2:
            print(f"\n[4/{total_steps}] Synthesizing committee view...")
            synthesis = synthesize_committee(primary, url, model=args.model)
            if synthesis:
                content = generate_synthesis_markdown(synthesis, primary)
                fp = save_report(content, url, suffix="_committee_synthesis")
                print(f"  {fp.name}")
                print_synthesis(synthesis, primary, icps)
    else:
        # Single persona or generic — show terminal scorecard
        primary = [a for a in analyses if a and a.url == url]
        if primary:
            print_single_analysis(primary[0])
