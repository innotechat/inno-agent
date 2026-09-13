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
    """Bounded process-local browser state index with TTL and safe session lifecycle."""

    def __init__(self, *, max_snapshots: int = 256, ttl_seconds: int = 900, max_content_chars: int = 65536):
        self.max_snapshots = max(int(max_snapshots), 1)
        self.ttl_seconds = max(int(ttl_seconds), 1)
        self.max_content_chars = max(int(max_content_chars), 1024)
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
        removed = [line[:500] for line in old if line not in new_set][:20]
        added = [line[:500] for line in new if line not in old_set][:20]
        parts = []
        if added:
            parts.append("added:\n" + "\n".join(f"+ {line}" for line in added))
        if removed:
            parts.append("removed:\n" + "\n".join(f"- {line}" for line in removed))
        return "\n".join(parts) or "unchanged"

    def _purge_expired(self) -> None:
        cutoff = time.time() - self.ttl_seconds
        expired = [oid for oid, snapshot in self._snapshots.items() if snapshot.created_at < cutoff]
        for observation_id in expired:
            self._snapshots.pop(observation_id, None)
        for key, snapshot in list(self._latest.items()):
            if snapshot.created_at < cutoff or snapshot.observation_id not in self._snapshots:
                self._latest.pop(key, None)
                self._sessions.pop(key, None)

    def snapshot(
        self,
        *,
        browser_id: object,
        url: str,
        title: str,
        content: str,
        artifact_ref: str = "",
    ) -> BrowserSnapshot:
        self._purge_expired()
        key = self._key(browser_id)
        session_id = self._sessions.setdefault(key, f"bsess_{secrets.token_urlsafe(9)}")
        previous = self._latest.get(key)
        current_fp = self._fingerprint(url, title, content)
        changed = previous is None or current_fp != previous.fingerprint
        sequence = previous.sequence + 1 if previous else 1
        observation_id = f"bobs_{secrets.token_urlsafe(10)}"
        bounded_content = str(content or "")[: self.max_content_chars]
        diff = self._diff(previous.content, bounded_content) if previous else "initial"
        snapshot = BrowserSnapshot(
            session_id=session_id,
            observation_id=observation_id,
            browser_id=key,
            url=url,
            title=title,
            artifact_ref=artifact_ref,
            sequence=sequence,
            changed=changed,
            diff=diff,
            created_at=time.time(),
            fingerprint=current_fp,
            content=bounded_content,
        )
        self._latest[key] = snapshot
        self._snapshots[observation_id] = snapshot
        while len(self._snapshots) > self.max_snapshots:
            oldest_id = next(iter(self._snapshots))
            self._snapshots.pop(oldest_id, None)
            for latest_key, latest_snapshot in list(self._latest.items()):
                if latest_snapshot.observation_id == oldest_id:
                    self._latest.pop(latest_key, None)
                    self._sessions.pop(latest_key, None)
        return snapshot

    def get(self, observation_id: str) -> BrowserSnapshot:
        self._purge_expired()
        snapshot = self._snapshots.get(str(observation_id or "").strip())
        if snapshot is None:
            raise KeyError("unknown or expired browser observation reference")
        return snapshot

    def latest(self, browser_id: object) -> BrowserSnapshot | None:
        self._purge_expired()
        return self._latest.get(self._key(browser_id))

    def close(self, browser_id: object) -> None:
        """Invalidate every state snapshot for the closed browser session."""
        self._purge_expired()
        key = self._key(browser_id)
        self._latest.pop(key, None)
        self._sessions.pop(key, None)
        stale_ids = [oid for oid, snapshot in self._snapshots.items() if snapshot.browser_id == key]
        for observation_id in stale_ids:
            self._snapshots.pop(observation_id, None)

    def clear(self) -> None:
        self._sessions.clear()
        self._latest.clear()
        self._snapshots.clear()


BROWSER_STATE_STORE = BrowserStateStore()
