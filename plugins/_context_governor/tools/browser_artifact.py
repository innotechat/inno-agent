from __future__ import annotations

import re
from typing import Any

from helpers.tool import Response, Tool
from plugins._context_governor.helpers.artifacts import get_artifact
from plugins._context_governor.helpers.budget import get_agent_governor


class BrowserArtifact(Tool):
    """Explicitly retrieve a retained browser artifact without full-context injection."""

    async def execute(
        self,
        ref: str = "",
        query: str = "",
        element_ref: str = "",
        start_line: int = 0,
        end_line: int = 0,
        max_chars: int = 6000,
        context_lines: int = 1,
        **kwargs: Any,
    ) -> Response:
        try:
            value = get_artifact(ref)
        except KeyError as exc:
            return Response(message=str(exc), break_loop=False)

        if getattr(self, "agent", None) is not None:
            governor = get_agent_governor(self.agent)
            governor.note_artifact_retrieval()
            if query or element_ref or start_line or end_line:
                governor.note_escalation()

        lines = value.splitlines()
        query = str(query or "").strip()
        element_ref = str(element_ref or "").strip()
        start = int(start_line)
        end = int(end_line)

        if start < 0 or end < 0 or (start and end and end < start):
            return Response(message="Invalid artifact line range", break_loop=False)

        if element_ref:
            match_pattern = re.compile(rf"^\s*(?:[-*]\s*)?\[{re.escape(element_ref.strip('[]'))}\]\s+.*$")
            matched = [index for index, line in enumerate(lines) if match_pattern.match(line)]
            if not matched:
                return Response(message=f"No artifact element matched ref: {element_ref}", break_loop=False)
            window = max(int(context_lines), 0)
            selected: set[int] = set()
            for index in matched:
                selected.update(range(max(0, index - window), min(len(lines), index + window + 1)))
            value = "\n".join(lines[index] for index in sorted(selected))
        elif query:
            needle = query.casefold()
            matched: set[int] = set()
            window = max(int(context_lines), 0)
            for index, line in enumerate(lines):
                if needle in line.casefold():
                    matched.update(range(max(0, index - window), min(len(lines), index + window + 1)))
            value = "\n".join(lines[index] for index in sorted(matched)) or f"No artifact lines matched query: {query}"
        elif start or end:
            line_start = max(start - 1, 0)
            line_end = end if end > 0 else len(lines)
            value = "\n".join(lines[line_start:line_end])

        limit = max(int(max_chars), 1)
        if len(value) > limit:
            marker = "\n...[targeted artifact result truncated]"
            if len(marker) >= limit:
                value = value[:limit]
            else:
                value = value[: limit - len(marker)] + marker
        return Response(message=value, break_loop=False)
