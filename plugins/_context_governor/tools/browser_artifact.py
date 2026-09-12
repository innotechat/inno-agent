from __future__ import annotations

from typing import Any

from helpers.tool import Response, Tool
from plugins._context_governor.helpers.artifacts import get_artifact


class BrowserArtifact(Tool):
    """Explicitly retrieve a retained browser artifact, optionally by text/ref query."""

    async def execute(self, ref: str = "", query: str = "", max_chars: int = 6000, context_lines: int = 1, **kwargs: Any) -> Response:
        try:
            value = get_artifact(ref)
        except KeyError as exc:
            return Response(message=str(exc), break_loop=False)
        query = str(query or "").strip()
        if query:
            needle = query.casefold()
            lines = value.splitlines()
            matched: set[int] = set()
            for index, line in enumerate(lines):
                if needle in line.casefold():
                    window = max(int(context_lines), 0)
                    matched.update(range(max(0, index - window), min(len(lines), index + window + 1)))
            value = "\n".join(lines[index] for index in sorted(matched)) or f"No artifact lines matched query: {query}"
        limit = max(int(max_chars), 1)
        if len(value) > limit:
            value = value[:limit] + "\n...[targeted artifact result truncated]"
        return Response(message=value, break_loop=False)
