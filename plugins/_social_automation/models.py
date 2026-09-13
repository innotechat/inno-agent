from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SocialPlatform(str, Enum):
    LINKEDIN = "linkedin"
    X = "x"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    GENERIC = "generic"


class SocialActionType(str, Enum):
    COMPOSE = "compose"
    SAVE_DRAFT = "save_draft"
    PUBLISH = "publish"
    COMMENT = "comment"
    REPLY = "reply"
    SEARCH = "search"
    READ_NOTIFICATIONS = "read_notifications"


class ApprovalState(str, Enum):
    DRAFT = "draft"
    PENDING = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"


@dataclass(frozen=True)
class SocialAccount:
    account_id: str
    platform: SocialPlatform
    profile_id: str = ""
    display_name: str = ""
    capabilities: frozenset[str] = frozenset()


@dataclass(frozen=True)
class SocialDraft:
    draft_id: str
    account_id: str
    platform: SocialPlatform
    text: str
    media_refs: tuple[str, ...] = ()
    state: ApprovalState = ApprovalState.DRAFT
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SocialAction:
    action_id: str
    action_type: SocialActionType
    account: SocialAccount
    draft: SocialDraft | None = None
    target_id: str = ""
    idempotency_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
