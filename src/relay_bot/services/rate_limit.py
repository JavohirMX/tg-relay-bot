from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from relay_bot.repositories.store import Store, utc_now_iso


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int | None = None
    warning_message: str | None = None


class RateLimiter:
    def __init__(
        self,
        *,
        store: Store,
        window_seconds: int,
        max_messages: int,
        cooldown_seconds: int,
    ) -> None:
        self.store = store
        self.window_seconds = window_seconds
        self.max_messages = max_messages
        self.cooldown_seconds = cooldown_seconds

    async def check(self, user_id: int) -> RateLimitDecision:
        now = datetime.now(UTC).replace(microsecond=0)
        state = await self.store.get_rate_limit(user_id)
        if state is None:
            await self.store.set_rate_limit(
                user_id=user_id,
                window_started_at=utc_now_iso(),
                message_count=1,
                cooldown_until=None,
            )
            return RateLimitDecision(allowed=True)

        cooldown_until = parse_datetime(state["cooldown_until"])
        if cooldown_until is not None and cooldown_until > now:
            return RateLimitDecision(
                allowed=False,
                retry_after_seconds=max(1, int((cooldown_until - now).total_seconds())),
            )

        window_started_at = parse_datetime(state["window_started_at"]) or now
        if now - window_started_at > timedelta(seconds=self.window_seconds):
            await self.store.set_rate_limit(
                user_id=user_id,
                window_started_at=utc_now_iso(),
                message_count=1,
                cooldown_until=None,
            )
            return RateLimitDecision(allowed=True)

        message_count = int(state["message_count"]) + 1
        if message_count <= self.max_messages:
            await self.store.set_rate_limit(
                user_id=user_id,
                window_started_at=state["window_started_at"],
                message_count=message_count,
                cooldown_until=None,
            )
            return RateLimitDecision(allowed=True)

        if message_count == self.max_messages + 1:
            await self.store.set_rate_limit(
                user_id=user_id,
                window_started_at=state["window_started_at"],
                message_count=message_count,
                cooldown_until=None,
            )
            return RateLimitDecision(
                allowed=True,
                warning_message=(
                    "You are sending messages quickly. I delivered this one, "
                    "but the next burst may be cooled down."
                ),
            )

        cooldown_until = now + timedelta(seconds=self.cooldown_seconds)
        await self.store.set_rate_limit(
            user_id=user_id,
            window_started_at=state["window_started_at"],
            message_count=message_count,
            cooldown_until=cooldown_until.isoformat(),
        )
        return RateLimitDecision(allowed=False, retry_after_seconds=self.cooldown_seconds)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
