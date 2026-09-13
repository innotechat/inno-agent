from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from .adapters import PublishResult, SocialPlatformAdapter
from .models import ApprovalState, SocialAccount, SocialAction, SocialActionType, SocialDraft, SocialPlatform


class SocialAutomationCore:
    """Orchestrates draft/approval/publish without knowing platform-specific UI."""

    def __init__(self, adapters: dict[SocialPlatform, SocialPlatformAdapter] | None = None):
        self._adapters = adapters or {}
        self._drafts: dict[str, SocialDraft] = {}
        self._published_keys: set[str] = set()

    def register_adapter(self, adapter: SocialPlatformAdapter) -> None:
        self._adapters[adapter.platform] = adapter

    def adapter_for(self, platform: SocialPlatform) -> SocialPlatformAdapter:
        try:
            return self._adapters[platform]
        except KeyError as exc:
            raise ValueError(f"No social adapter registered for {platform.value}") from exc

    def create_draft(
        self,
        account: SocialAccount,
        text: str,
        *,
        media_refs: tuple[str, ...] = (),
        metadata: dict | None = None,
    ) -> SocialDraft:
        text = text.strip()
        if not text:
            raise ValueError("Social draft text cannot be empty")
        draft = SocialDraft(
            draft_id=f"draft-{uuid4().hex[:16]}",
            account_id=account.account_id,
            platform=account.platform,
            text=text,
            media_refs=media_refs,
            metadata=metadata or {},
        )
        valid, reason = self.adapter_for(account.platform).validate_draft(account, draft)
        if not valid:
            raise ValueError(f"Draft validation failed: {reason}")
        self._drafts[draft.draft_id] = draft
        return draft

    def request_approval(self, draft_id: str) -> SocialDraft:
        draft = self._get_draft(draft_id)
        if draft.state != ApprovalState.DRAFT:
            raise ValueError(f"Draft {draft_id} is not in draft state")
        updated = replace(draft, state=ApprovalState.PENDING)
        self._drafts[draft_id] = updated
        return updated

    def approve(self, draft_id: str) -> SocialDraft:
        draft = self._get_draft(draft_id)
        if draft.state != ApprovalState.PENDING:
            raise ValueError(f"Draft {draft_id} is not awaiting approval")
        updated = replace(draft, state=ApprovalState.APPROVED)
        self._drafts[draft_id] = updated
        return updated

    def reject(self, draft_id: str) -> SocialDraft:
        draft = self._get_draft(draft_id)
        if draft.state not in {ApprovalState.PENDING, ApprovalState.DRAFT}:
            raise ValueError(f"Draft {draft_id} cannot be rejected from {draft.state.value}")
        updated = replace(draft, state=ApprovalState.REJECTED)
        self._drafts[draft_id] = updated
        return updated

    def publish(self, action: SocialAction) -> PublishResult:
        if action.action_type != SocialActionType.PUBLISH:
            raise ValueError("SocialAutomationCore.publish requires a publish action")
        if action.draft is None:
            raise ValueError("Publish action requires a draft")
        draft = self._get_draft(action.draft.draft_id)
        if draft.state != ApprovalState.APPROVED:
            raise ValueError("Publishing requires explicit approval")
        key = action.idempotency_key or draft.draft_id
        if key in self._published_keys:
            raise ValueError("Duplicate publish blocked by idempotency key")
        result = self.adapter_for(action.account.platform).publish(action.account, draft, idempotency_key=key)
        if result.success:
            self._published_keys.add(key)
            self._drafts[draft.draft_id] = replace(draft, state=ApprovalState.PUBLISHED)
        else:
            self._drafts[draft.draft_id] = replace(draft, state=ApprovalState.FAILED)
        return result

    def get_draft(self, draft_id: str) -> SocialDraft:
        return self._get_draft(draft_id)

    def _get_draft(self, draft_id: str) -> SocialDraft:
        try:
            return self._drafts[draft_id]
        except KeyError as exc:
            raise ValueError(f"Unknown social draft: {draft_id}") from exc
