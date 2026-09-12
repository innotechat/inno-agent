from __future__ import annotations

from typing import Any

from helpers.tool import Response, Tool
from plugins._context_governor.helpers.state import BROWSER_STATE_STORE


class BrowserState(Tool):
    """Retrieve compact browser state or a state diff without reloading the page."""

    async def execute(self, observation_id: str = "", browser_id: str = "", mode: str = "latest", **kwargs: Any) -> Response:
        try:
            if observation_id:
                snapshot = BROWSER_STATE_STORE.get(observation_id)
            else:
                snapshot = BROWSER_STATE_STORE.latest(browser_id)
                if snapshot is None:
                    return Response(message="No browser state snapshot available", break_loop=False)
        except KeyError as exc:
            return Response(message=str(exc), break_loop=False)

        mode = str(mode or "latest").strip().lower()
        if mode == "diff":
            message = f"BROWSER_STATE_DIFF\nobservation_id: {snapshot.observation_id}\nsequence: {snapshot.sequence}\nchanged: {str(snapshot.changed).lower()}\n{snapshot.diff}"
        elif mode == "artifact":
            message = f"BROWSER_STATE\nobservation_id: {snapshot.observation_id}\nartifact_ref: {snapshot.artifact_ref}"
        else:
            message = (
                "BROWSER_STATE\n"
                f"session_id: {snapshot.session_id}\n"
                f"observation_id: {snapshot.observation_id}\n"
                f"browser_id: {snapshot.browser_id}\n"
                f"sequence: {snapshot.sequence}\n"
                f"changed: {str(snapshot.changed).lower()}\n"
                f"url: {snapshot.url}\n"
                f"title: {snapshot.title}\n"
                f"artifact_ref: {snapshot.artifact_ref}"
            )
        return Response(message=message, break_loop=False)
