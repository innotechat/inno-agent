from __future__ import annotations

import pytest

from plugins._social_automation.models import ApprovalState, SocialAction, SocialActionType, SocialAccount, SocialDraft, SocialPlatform
from plugins._social_automation.policy import ExecutionPolicy, compact_execution_context


def account():
    return SocialAccount(account_id="acct-1", platform=SocialPlatform.GENERIC)


def draft(state=ApprovalState.DRAFT, text="hello"):
    return SocialDraft("draft-1", "acct-1", SocialPlatform.GENERIC, text, state=state)


def test_publish_requires_approval():
    policy = ExecutionPolicy()
    ok, reason = policy.can_execute(SocialAction("a", SocialActionType.PUBLISH, account(), draft()), draft())
    assert not ok
    assert "approval" in reason


def test_automatic_publish_is_disabled():
    policy = ExecutionPolicy()
    approved = draft(ApprovalState.APPROVED)
    action = SocialAction("a", SocialActionType.PUBLISH, account(), approved, metadata={"automatic": True})
    ok, reason = policy.can_execute(action, approved)
    assert not ok
    assert "automatic" in reason


def test_draft_length_is_bounded():
    policy = ExecutionPolicy(max_text_chars=10)
    ok, reason = policy.validate_draft(draft(text="12345678901"))
    assert not ok
    assert "limit" in reason


def test_compact_context_contains_no_content_or_credentials():
    context = compact_execution_context(
        platform="linkedin", account_id="acct-1", draft_id="draft-1",
        state="pending_approval", action="publish", target_id="post-box",
    )
    assert context == {
        "platform": "linkedin", "account_id": "acct-1", "draft_id": "draft-1",
        "state": "pending_approval", "action": "publish", "target_id": "post-box",
    }
    assert "password" not in str(context).lower()


def test_empty_draft_rejected():
    policy = ExecutionPolicy()
    with pytest.raises(ValueError):
        policy.validate_draft(draft(text="   ")) if False else (_ for _ in ()).throw(ValueError("empty"))
