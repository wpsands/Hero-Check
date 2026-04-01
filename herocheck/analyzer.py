"""Anthropic API calls with tool_use structured output and retry logic."""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
from pydantic import BaseModel, ValidationError

from herocheck.models import (
    CommitteeSynthesis,
    CompetitiveReport,
    HeroAnalysis,
    ICPProfile,
)
from herocheck.prompt import (
    build_analysis_prompt,
    build_comparison_prompt,
    build_synthesis_prompt,
)

MODEL_MAP = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
}

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _is_retryable(error: anthropic.APIError) -> bool:
    """Check if an API error is worth retrying."""
    if isinstance(error, (anthropic.RateLimitError, anthropic.InternalServerError)):
        return True
    if isinstance(error, anthropic.APIStatusError) and error.status_code >= 500:
        return True
    return False


def _call_structured(
    prompt: str,
    *,
    model: str = "sonnet",
    screenshot_b64: str | None = None,
    max_tokens: int = 4096,
    result_type: type[BaseModel],
    retries: int = 2,
) -> dict | None:
    """Call Claude with forced tool_use for guaranteed structured output.

    Instead of asking the model to output JSON text and parsing it (fragile),
    we define a tool whose input_schema matches the desired output, then force
    the model to call it. The tool_use block's input is guaranteed valid JSON
    matching the schema.
    """
    client = get_client()
    model_id = MODEL_MAP.get(model, model)

    tool_name = f"record_{result_type.__name__}"
    tool = {
        "name": tool_name,
        "description": f"Record the structured {result_type.__name__} analysis result.",
        "input_schema": result_type.model_json_schema(),
    }

    content: list[dict] = []
    if screenshot_b64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": screenshot_b64,
            },
        })
    content.append({"type": "text", "text": prompt})

    for attempt in range(1 + retries):
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": content}],
                tools=[tool],
                tool_choice={"type": "tool", "name": tool_name},
            )
            for block in response.content:
                if block.type == "tool_use":
                    return block.input

            # No tool_use block — retry
            if attempt < retries:
                print("  [WARN] No tool_use in response, retrying...", file=sys.stderr)
                time.sleep(2 ** attempt)
                continue
            return None

        except anthropic.APIError as e:
            if attempt < retries and _is_retryable(e):
                wait = 2 ** attempt
                print(
                    f"  [WARN] API error (attempt {attempt + 1}): {e}, "
                    f"retrying in {wait}s...",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue
            print(f"  [FAIL] API error: {e}", file=sys.stderr)
            return None

    return None


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------
def analyze_hero(
    url: str,
    page_content: str,
    *,
    model: str = "sonnet",
    headline: str | None = None,
    icp: ICPProfile | None = None,
    positioning_content: str | None = None,
    screenshot_b64: str | None = None,
) -> HeroAnalysis | None:
    """Analyze a single hero section."""
    prompt = build_analysis_prompt(
        url,
        page_content,
        icp=icp,
        positioning_content=positioning_content,
        headline=headline,
        has_screenshot=bool(screenshot_b64),
    )

    result_data = _call_structured(
        prompt,
        model=model,
        screenshot_b64=screenshot_b64,
        result_type=HeroAnalysis,
    )

    if not result_data:
        return None

    # Override caller-controlled fields
    result_data["url"] = url
    if screenshot_b64:
        result_data["layout_source"] = "screenshot"
    if icp:
        result_data["persona_name"] = icp.name
    if not positioning_content:
        result_data.pop("positioning_check", None)

    try:
        return HeroAnalysis(**result_data)
    except ValidationError as e:
        print(f"  [FAIL] Validation error: {e}", file=sys.stderr)
        return None


def compare_heroes(
    analyses: list[HeroAnalysis],
    primary_url: str,
    *,
    model: str = "sonnet",
    icp: ICPProfile | None = None,
) -> CompetitiveReport | None:
    """Generate a competitive comparison from individual analyses."""
    persona_name = icp.name if icp else "Generic Buyer"
    analyses_json = json.dumps([a.model_dump() for a in analyses], indent=2)

    prompt = build_comparison_prompt(
        analyses_json=analyses_json,
        primary_url=primary_url,
        persona_name=persona_name,
        icp=icp,
    )

    result_data = _call_structured(
        prompt, model=model, max_tokens=8192, result_type=CompetitiveReport,
    )

    if not result_data:
        return None

    try:
        return CompetitiveReport(**result_data)
    except ValidationError as e:
        print(f"  [FAIL] Comparison validation error: {e}", file=sys.stderr)
        return None


def synthesize_committee(
    analyses: list[HeroAnalysis],
    url: str,
    *,
    model: str = "sonnet",
) -> CommitteeSynthesis | None:
    """Synthesize multiple persona analyses into consensus/tension."""
    analyses_json = json.dumps([a.model_dump() for a in analyses], indent=2)
    prompt = build_synthesis_prompt(analyses_json=analyses_json, url=url)

    result_data = _call_structured(
        prompt, model=model, max_tokens=8192, result_type=CommitteeSynthesis,
    )

    if not result_data:
        return None

    result_data["url"] = url

    try:
        return CommitteeSynthesis(**result_data)
    except ValidationError as e:
        print(f"  [FAIL] Synthesis validation error: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Parallel execution
# ---------------------------------------------------------------------------
def run_parallel(fn, task_kwargs: list[dict], *, max_workers: int = 6) -> list:
    """Run a callable with multiple kwarg sets in parallel.

    Returns results in the same order as task_kwargs. Failed tasks return None.
    """
    results: list = [None] * len(task_kwargs)
    with ThreadPoolExecutor(max_workers=min(len(task_kwargs), max_workers)) as pool:
        future_to_idx = {
            pool.submit(fn, **kwargs): i for i, kwargs in enumerate(task_kwargs)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                print(f"  [FAIL] Parallel task error: {e}", file=sys.stderr)
    return results
