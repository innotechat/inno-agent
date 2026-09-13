import time

from plugins._context_governor.helpers.action_safety import (
    ActionIdempotencyStore,
    browser_action_fingerprint,
)


def test_action_fingerprint_is_deterministic_and_changes_with_target():
    base = {"context_id": "ctx", "browser_id": 2, "action": "click", "ref": 12, "url": "https://example.com"}
    assert browser_action_fingerprint(base) == browser_action_fingerprint(dict(base))
    changed = {**base, "ref": 13}
    assert browser_action_fingerprint(base) != browser_action_fingerprint(changed)


def test_idempotency_store_tracks_completed_actions_with_ttl():
    store = ActionIdempotencyStore(ttl_seconds=0.01)
    fp = browser_action_fingerprint({"action": "submit", "ref": 12})
    assert not store.seen(fp)
    store.mark_completed(fp)
    assert store.seen(fp)
    time.sleep(0.02)
    assert not store.seen(fp)
