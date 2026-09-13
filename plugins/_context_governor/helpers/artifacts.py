from __future__ import annotations

import secrets
import time
from dataclasses import dataclass


@dataclass
class _Artifact:
    value: str
    created_at: float
    expires_at: float


class ArtifactStore:
    """Small process-local store for full browser observations kept out of history."""

    def __init__(self, *, ttl_seconds: int = 900, max_artifacts: int = 256, max_chars: int = 1_000_000):
        self.ttl_seconds = max(int(ttl_seconds), 1)
        self.max_artifacts = max(int(max_artifacts), 1)
        self.max_chars = max(int(max_chars), 1)
        self._items: dict[str, _Artifact] = {}

    def _purge(self) -> None:
        now = time.monotonic()
        expired = [key for key, item in self._items.items() if item.expires_at <= now]
        for key in expired:
            self._items.pop(key, None)

    def put(self, value: str) -> str:
        text = str(value or "")
        if len(text) > self.max_chars:
            raise ValueError("artifact exceeds configured size limit")
        self._purge()
        while len(self._items) >= self.max_artifacts:
            oldest = min(self._items, key=lambda key: self._items[key].created_at)
            self._items.pop(oldest, None)
        token = secrets.token_urlsafe(18)
        ref = f"browser://{token}"
        now = time.monotonic()
        self._items[ref] = _Artifact(text, now, now + self.ttl_seconds)
        return ref

    def get(self, ref: str) -> str:
        self._purge()
        key = str(ref or "").strip()
        if not key.startswith("browser://") or key not in self._items:
            raise KeyError("unknown or expired browser artifact reference")
        return self._items[key].value

    def clear(self) -> None:
        self._items.clear()


ARTIFACT_STORE = ArtifactStore()


def put_artifact(value: str) -> str:
    return ARTIFACT_STORE.put(value)


def get_artifact(ref: str) -> str:
    return ARTIFACT_STORE.get(ref)
