from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .models import SocialAccount, SocialDraft, SocialPlatform


@dataclass(frozen=True)
class PublishResult:
    success: bool
    external_id: str = ""
    message: str = ""


class SocialPlatformAdapter(ABC):
    """Small contract for platform adapters; browser/API details stay outside the core."""

    platform: SocialPlatform

    @abstractmethod
    def capabilities(self, account: SocialAccount) -> frozenset[str]:
        raise NotImplementedError

    @abstractmethod
    def validate_draft(self, account: SocialAccount, draft: SocialDraft) -> tuple[bool, str]:
        raise NotImplementedError

    @abstractmethod
    def save_draft(self, account: SocialAccount, draft: SocialDraft) -> str:
        raise NotImplementedError

    @abstractmethod
    def publish(self, account: SocialAccount, draft: SocialDraft, *, idempotency_key: str) -> PublishResult:
        raise NotImplementedError

    def health(self, account: SocialAccount) -> dict[str, Any]:
        return {"platform": self.platform.value, "account_id": account.account_id, "ready": True}
