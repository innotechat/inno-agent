from __future__ import annotations

import pytest

from plugins._social_automation.adapters import PublishResult, SocialPlatformAdapter
from plugins._social_automation.core import SocialAutomationCore
from plugins._social_automation.models import SocialAccount, SocialAction, SocialActionType, SocialDraft, SocialPlatform


class FakeAdapter(SocialPlatformAdapter):
    platform = SocialPlatform.GENERIC

    def capabilities(self, account):
        return frozenset({"compose", "save_draft", "publish"})

    def validate_draft(self, account, draft):
        return bool(draft.text), "text is required"

    def save_draft(self, account, draft):
        return f"remote-{draft.draft_id}"

    def publish(self, account, draft, *, idempotency_key):
        return PublishResult(success=True, external_id=f"post-{idempotency_key}", message="published")


@pytest.fixture
def core():
    value = SocialAutomationCore()
    value.register_adapter(FakeAdapter())
    return value


def account():
    return SocialAccount(account_id="acct-1", platform=SocialPlatform.GENERIC, profile_id="profile-1")


def test_draft_approval_publish_lifecycle(core):
    draft = core.create_draft(account(), "hello world")
    assert draft.state.value == "draft"
    draft = core.request_approval(draft.draft_id)
    draft = core.approve(draft.draft_id)
    result = core.publish(SocialAction("action-1", SocialActionType.PUBLISH, account(), draft, idempotency_key="key-1"))
    assert result.success is True
    assert core.get_draft(draft.draft_id).state.value == "published"


def test_publish_requires_approval(core):
    draft = core.create_draft(account(), "hello")
    with pytest.raises(ValueError, match="approval"):
        core.publish(SocialAction("action-1", SocialActionType.PUBLISH, account(), draft, idempotency_key="key-1"))


def test_duplicate_publish_is_blocked(core):
    draft = core.create_draft(account(), "hello")
    draft = core.approve(core.request_approval(draft.draft_id).draft_id)
    action = SocialAction("action-1", SocialActionType.PUBLISH, account(), draft, idempotency_key="key-1")
    core.publish(action)
    with pytest.raises(ValueError, match="Duplicate publish"):
        core.publish(action)


def test_empty_draft_rejected(core):
    with pytest.raises(ValueError, match="empty"):
        core.create_draft(account(), "  ")
