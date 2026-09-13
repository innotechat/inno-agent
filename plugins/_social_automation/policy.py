from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .models import ApprovalState, SocialAction, SocialActionType, SocialDraft


class ApprovalDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ExecutionPolicy:
    """Platform-independent safety contract for social execution."""

    require_approval_for_publish: bool = True
    require_fresh_observation: bool = True
    allow_automatic_publish: bool = False
    max_text_chars: int = 10000

    def validate_draft(self, draft: SocialDraft) -> tuple[bool, str]:
        if not draft.text.strip():
            return False, "draft text is empty"
        if len(draft.text) > self.max_text_chars:
            return False, "draft exceeds configured text limit"
        return True, "ok"

    def can_execute(self, action: SocialAction, draft: SocialDraft) -> tuple[bool, str]:
        if action.action_type != SocialActionType.PUBLISH:
            return True, "non-publish action"
        if self.require_approval_for_publish and draft.state != ApprovalState.APPROVED:
            return False, "publish requires explicit approval"
        if not self.allow_automatic_publish and action.metadata.get("automatic", False):
            return False, "automatic publishing is disabled by policy"
        return True, "approved for execution"


def compact_execution_context(
    *,
    platform: str,
    account_id: str,
    draft_id: str,
    state: str,
    action: str,
    target_id: str = "",
) -> dict[str, Any]:
    """Return a small LLM-facing context; never include DOM or credentials."""
    return {
        "platform": platform,
        "account_id": account_id,
        "draft_id": draft_id,
        "state": state,
        "action": action,
        "target_id": target_id,
    }
