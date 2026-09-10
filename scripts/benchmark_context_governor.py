"""Synthetic benchmark for Context Governor compaction.

This deliberately measures the governor in isolation. It is not a production
browser benchmark; real browser measurements should be collected locally
against representative pages before changing default limits.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from plugins._context_governor.helpers.governor import GovernorConfig, format_browser_result


def main() -> None:
    repeated = "\n".join(
        [
            "Dashboard",
            "Navigation and account settings",
            "[12] Create post",
            "[17] Search",
            "[23] Notifications",
            "Recent activity and recommendations",
        ]
        * 120
    )
    result = {
        "browser_id": 2,
        "url": "https://example.test/dashboard",
        "title": "Example Dashboard",
        "success": True,
        "document": repeated,
    }
    config = GovernorConfig(max_chars=12000, max_visible_text_chars=6000, max_interactive_elements=80)
    governed = format_browser_result("click", result, config)
    raw = json.dumps(result, ensure_ascii=False, default=str)
    raw_chars = len(raw)
    governed_chars = len(governed)
    reduction = 0.0 if raw_chars == 0 else (1 - governed_chars / raw_chars) * 100
    report = {
        "type": "synthetic",
        "raw_chars": raw_chars,
        "governed_chars": governed_chars,
        "character_reduction_percent": round(reduction, 2),
        "interactive_refs_preserved": sum(1 for ref in ("[12]", "[17]", "[23]") if ref in governed),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
