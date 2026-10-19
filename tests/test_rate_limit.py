from datetime import UTC, datetime, timedelta

from aiogram.types import User

from relay_bot.db.database import Database
from relay_bot.repositories.store import Store
from relay_bot.services.rate_limit import RateLimiter


async def test_rate_limiter_allows_normal_messages_and_cools_down_bursts(tmp_path):
    database = Database(tmp_path / "relay.sqlite3")
    await database.initialize()
    store = Store(database)
    await store.upsert_user(User(id=1001, is_bot=False, first_name="Guest"))

    limiter = RateLimiter(store=store, window_seconds=60, max_messages=2, cooldown_seconds=30)

    first = await limiter.check(1001)
    second = await limiter.check(1001)
    third = await limiter.check(1001)
    fourth = await limiter.check(1001)

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is True
    assert third.warning_message is not None
    assert fourth.allowed is False
    assert fourth.retry_after_seconds == 30

    await database.close()


async def _limiter(tmp_path):
    database = Database(tmp_path / "relay.sqlite3")
    await database.initialize()
    store = Store(database)
    await store.upsert_user(User(id=1001, is_bot=False, first_name="Guest"))
    limiter = RateLimiter(store=store, window_seconds=60, max_messages=2, cooldown_seconds=30)
    return database, store, limiter


async def test_rate_limiter_resets_after_window_expires(tmp_path):
    database, store, limiter = await _limiter(tmp_path)
    for _ in range(4):
        await limiter.check(1001)
    old = (datetime.now(UTC) - timedelta(seconds=120)).isoformat()
    await store.set_rate_limit(
        user_id=1001, window_started_at=old, message_count=9, cooldown_until=None
    )

    decision = await limiter.check(1001)

    assert decision.allowed is True
    assert decision.warning_message is None
    assert (await store.get_rate_limit(1001))["message_count"] == 1
    await database.close()


async def test_rate_limiter_blocks_during_cooldown_then_allows_after_it(tmp_path):
    database, store, limiter = await _limiter(tmp_path)
    now = datetime.now(UTC)
    await store.set_rate_limit(
        user_id=1001,
        window_started_at=(now - timedelta(seconds=120)).isoformat(),
        message_count=5,
        cooldown_until=(now + timedelta(seconds=20)).isoformat(),
    )
    blocked = await limiter.check(1001)
    assert blocked.allowed is False
    assert 1 <= blocked.retry_after_seconds <= 20

    await store.set_rate_limit(
        user_id=1001,
        window_started_at=(now - timedelta(seconds=120)).isoformat(),
        message_count=5,
        cooldown_until=(now - timedelta(seconds=1)).isoformat(),
    )
    assert (await limiter.check(1001)).allowed is True
    await database.close()
