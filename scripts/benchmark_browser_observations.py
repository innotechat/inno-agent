"""Realistic browser-observation benchmark for the Context Governor.

The fixtures model common browser payloads (dashboard, social composer, and
search/results pages) with realistic metadata, interactive refs, repeated DOM
noise, and visible text. This is still an offline fixture benchmark: it does
not claim to measure a live website or provider token billing.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from helpers.tokens import approximate_prompt_tokens
from plugins._context_governor.helpers.governor import GovernorConfig, format_browser_result
from plugins._context_governor.helpers.state import BROWSER_STATE_STORE


def _dashboard() -> dict:
    controls = "\n".join(
        f"[{100 + i}] {'Open details' if i % 3 == 0 else 'View report' if i % 3 == 1 else 'More actions'}"
        for i in range(1, 96)
    )
    rows = "\n".join(
        f"Account {i:03d} | status active | last activity 2026-09-{(i % 28) + 1:02d} | "
        "recommendation and navigation metadata repeated by application DOM"
        for i in range(1, 260)
    )
    return {
        "browser_id": 2,
        "currentUrl": "https://example.test/dashboard/accounts",
        "title": "Accounts Dashboard",
        "success": True,
        "document": (
            "Accounts Dashboard\nNavigation\nProfile\nSettings\n"
            + controls
            + "\nRecent accounts\n"
            + rows
        ),
    }


def _social_composer() -> dict:
    controls = "\n".join(
        [
            "[12] Create post",
            "[13] Add media",
            "[14] Schedule",
            "[15] Save draft",
            "[16] Cancel",
            "[17] Audience selector",
            "[18] Add location",
            "[19] Add alt text",
        ]
        + [f"[{200 + i}] Suggested action" for i in range(1, 45)]
    )
    noise = "\n".join(
        f"Composer component {i}: accessibility metadata, layout classes, tracking attributes, "
        "hidden responsive variants and duplicated framework markup"
        for i in range(1, 150)
    )
    return {
        "browser_id": 3,
        "url": "https://example.test/social/compose",
        "title": "Create Post",
        "success": True,
        "document": (
            "Create Post\nWrite something\nDraft status\n"
            + controls
            + "\nPost content area\n"
            + noise
        ),
    }


def _search_results() -> dict:
    results = "\n".join(
        f"[{500 + i}] Open result {i}: Example organization, recent update, navigation and metadata"
        for i in range(1, 180)
    )
    return {
        "browser_id": 4,
        "url": "https://example.test/search?q=automation",
        "title": "Search results",
        "success": True,
        "document": (
            "Search results for automation\n[21] Search\n[22] Filters\n[23] Next page\n"
            + results
            + "\nFooter navigation\nPrivacy\nTerms\nHelp\n"
        ),
    }


def _measure(result: dict, config: GovernorConfig) -> dict:
    raw = json.dumps(result, ensure_ascii=False, default=str)
    first = format_browser_result("click", result, config)
    second = format_browser_result("click", result, config)
    raw_tokens = approximate_prompt_tokens(raw)
    first_tokens = approximate_prompt_tokens(first)
    second_tokens = approximate_prompt_tokens(second)
    reduction = 0.0 if raw_tokens == 0 else (1 - first_tokens / raw_tokens) * 100
    repeated_reduction = 0.0 if first_tokens == 0 else (1 - second_tokens / first_tokens) * 100
    return {
        "raw_chars": len(raw),
        "governed_chars": len(first),
        "repeated_governed_chars": len(second),
        "raw_tokens_approx": raw_tokens,
        "governed_tokens_approx": first_tokens,
        "repeated_governed_tokens_approx": second_tokens,
        "token_reduction_percent": round(reduction, 2),
        "repeated_context_reduction_percent": round(repeated_reduction, 2),
        "artifact_preserved": "artifact_ref: browser://" in first,
        "repeated_observation_compacted": "state: unchanged" in second,
    }


def main() -> None:
    BROWSER_STATE_STORE.clear()
    config = GovernorConfig(
        max_chars=12000,
        max_visible_text_chars=6000,
        max_interactive_elements=80,
    )
    scenarios = {
        "dashboard": _dashboard(),
        "social_composer": _social_composer(),
        "search_results": _search_results(),
    }
    measurements = {name: _measure(result, config) for name, result in scenarios.items()}
    total_raw = sum(item["raw_tokens_approx"] for item in measurements.values())
    total_governed = sum(item["governed_tokens_approx"] for item in measurements.values())
    total_repeated = sum(item["repeated_governed_tokens_approx"] for item in measurements.values())
    overall = 0.0 if total_raw == 0 else (1 - total_governed / total_raw) * 100
    repeated_overall = 0.0 if total_governed == 0 else (1 - total_repeated / total_governed) * 100
    report = {
        "type": "realistic_offline_browser_fixture",
        "note": "Representative fixtures, not live-site/provider billing measurements.",
        "scenarios": measurements,
        "overall_raw_tokens_approx": total_raw,
        "overall_governed_tokens_approx": total_governed,
        "overall_repeated_governed_tokens_approx": total_repeated,
        "overall_token_reduction_percent": round(overall, 2),
        "overall_repeated_context_reduction_percent": round(repeated_overall, 2),
        "all_artifacts_preserved": all(item["artifact_preserved"] for item in measurements.values()),
        "all_repeated_observations_compacted": all(item["repeated_observation_compacted"] for item in measurements.values()),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
