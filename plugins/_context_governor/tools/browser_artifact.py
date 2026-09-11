from __future__ import annotations

from typing import Any

from helpers.tool import Response, Tool
from plugins._context_governor.helpers.artifacts import get_artifact


class BrowserArtifact(Tool):
    """Explicitly retrieve a full browser artifact retained by the Context Governor."""

    async def execute(self, ref: str = "", **kwargs: Any) -> Response:
        try:
            value = get_artifact(ref)
        except KeyError as exc:
            return Response(message=str(exc), break_loop=False)
        return Response(message=value, break_loop=False)
