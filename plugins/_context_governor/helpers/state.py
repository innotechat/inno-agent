from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass


@dataclass
class BrowserSnapshot:
    session_id: str
    observation_id: str
    browser_id: str
    url: str
    title: str
    artifact_ref: str
    sequence: int
    changed: bool
    diff: str
    created_at: float
    fingerprint: str
    content: str = ""


class BrowserStateStore:
    """Bounded process-local browser state index for change detection and retrieval."""

    def __init__(self, *, max_snapshots: int = 256):
        self.max_snapshots = max(int(max_snapshots), 1)
        self._sessions: dict[str, str] = {}
        self._latest: dict[str, BrowserSnapshot] = {}
        self._snapshots: dict[str, BrowserSnapshot] = {}

    @staticmethod
    def _key(browser_id: object) -> str:
        return str(browser_id or "").strip() or "unknown"

    @staticmethod
    def _fingerprint(url: str, title: str, content: str) -> str:
        return hashlib.sha256(f"{url}\n{title}\n{content}".encode("utf-8")).hexdigest()

    @staticmethod
    def _diff(previous: str, current: str) -> str:
        old = previous.splitlines()
        new = current.splitlines()
        old_set = set(old)
        new_set = set(new)
        removed = [line for line in old if line not in new_set][:20]
        added = [line for line in new if line not in old_set][:20]
        parts = []
        if added:
            parts.append("added:\n" + "\n".join(f"+ {line}" for line in added))
        if removed:
            parts.append("removed:\n" + "\n".join(f"- {line}" for line in removed))
        return "\n".join(parts) or "unchanged"

    def snapshot(self, *, browser_id: object, url: str, title: str, content: str, artifact_ref: str = "") -> BrowserSnapshot:
        key = self._key(browser_id)
        session_id = self._sessions.setdefault(key, f"bsess_{secrets.token_urlsafe(9)}")
        previous = self._latest.get(key)
        current_fp = self._fingerprint(url, title, content)
        changed = previous is None or current_fp != previous.fingerprint
        sequence = previous.sequence + 1 if previous else 1
        observation_id = f"bobs_{secrets.token_urlsafe(10)}"
        diff = self._diff(previous.content, content) if previous else "initial"
        snapshot = BrowserSnapshot(session_id, observation_id, key, url, title, artifact_ref, sequence, changed, diff, time.time(), current_fp, content)
        self._latest[key] = snapshot
        self._snapshots[observation_id] = snapshot
        while len(self._snapshots) > self.max_snapshots:
            oldest = next(iter(self._snapshots))
            self._snapshots.pop(oldest, None)
        return snapshot

    def get(self, observation_id: str) -> BrowserSnapshot:
        snapshot = self._snapshots.get(str(observation_id or "").strip())
        if snapshot is None:
            raise KeyError("unknown or expired browser observation reference")
        return snapshot

    def latest(self, browser_id: object) -> BrowserSnapshot | None:
        return self._latest.get(self._key(browser_id))

    def clear(self) -> None:
        self._sessions.clear()
        self._latest.clear()
        self._snapshots.clear()


BROWSER_STATE_STORE = BrowserStateStore()
