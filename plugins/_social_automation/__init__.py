"""Platform-agnostic social automation core."""

from .models import (
    ApprovalState,
    SocialAccount,
    SocialAction,
    SocialActionType,
    SocialDraft,
    SocialPlatform,
)
from .adapters import SocialPlatformAdapter
from .core import SocialAutomationCore

__all__ = [
    "ApprovalState",
    "SocialAccount",
    "SocialAction",
    "SocialActionType",
    "SocialDraft",
    "SocialPlatform",
    "SocialPlatformAdapter",
    "SocialAutomationCore",
]
