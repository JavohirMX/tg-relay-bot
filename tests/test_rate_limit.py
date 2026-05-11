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
