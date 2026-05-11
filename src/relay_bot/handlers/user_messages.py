from aiogram import Bot, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from relay_bot.config import Settings
from relay_bot.keyboards.admin import dashboard_keyboard
from relay_bot.repositories.store import Store
from relay_bot.services.dashboard import dashboard_text
from relay_bot.services.rate_limit import RateLimitDecision, RateLimiter
from relay_bot.services.relay import RelayService

router = Router(name="user_messages")


@router.message(CommandStart())
async def start(message: Message, settings: Settings, store: Store) -> None:
    if message.from_user is None:
        return
    if message.from_user.id == settings.admin_telegram_id:
        await message.answer(
            await dashboard_text(store),
            reply_markup=dashboard_keyboard(await store.is_paused()),
        )
        return
    await store.upsert_user(message.from_user)
    await store.ensure_conversation(message.from_user.id)
    await message.answer(settings.welcome_text)


@router.message()
async def relay_user_message(
    message: Message,
    bot: Bot,
    settings: Settings,
    store: Store,
    relay_service: RelayService,
    rate_limiter: RateLimiter,
) -> None:
    if message.from_user is None or message.from_user.id == settings.admin_telegram_id:
        return

    user = await store.upsert_user(message.from_user)
    await store.ensure_conversation(message.from_user.id)

    if user["is_blocked"]:
        await message.answer("This conversation is currently blocked.")
        return
    if await store.is_paused():
        await message.answer("Messages are paused right now. Please try again later.")
        return
    if await store.is_user_muted(message.from_user.id):
        await relay_service.record_inbound_only(message)
        return

    decision = await rate_limiter.check(message.from_user.id)
    if not decision.allowed:
        await message.answer(rate_limit_message(decision))
        return

    await relay_service.relay_from_user(bot, message)
    if decision.warning_message:
        await message.answer(decision.warning_message)


def rate_limit_message(decision: RateLimitDecision) -> str:
    if decision.retry_after_seconds is None:
        return "You are sending messages too quickly. Please slow down."
    return (
        "You are sending messages too quickly. "
        f"Please try again in {decision.retry_after_seconds}s."
    )
