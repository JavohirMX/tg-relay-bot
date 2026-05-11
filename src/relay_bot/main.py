import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand

from relay_bot.config import get_settings
from relay_bot.db.database import Database
from relay_bot.handlers import admin_callbacks, admin_commands, admin_replies, user_messages
from relay_bot.middlewares.dependencies import DependencyMiddleware
from relay_bot.repositories.store import Store
from relay_bot.services.rate_limit import RateLimiter
from relay_bot.services.relay import RelayService

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    settings = get_settings()
    database = Database(settings.database_path)
    await database.initialize()

    store = Store(database)
    relay_service = RelayService(settings=settings, store=store)
    rate_limiter = RateLimiter(
        store=store,
        window_seconds=settings.rate_limit_window_seconds,
        max_messages=settings.rate_limit_max_messages,
        cooldown_seconds=settings.rate_limit_cooldown_seconds,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.update.middleware(
        DependencyMiddleware(
            settings=settings,
            store=store,
            relay_service=relay_service,
            rate_limiter=rate_limiter,
        )
    )
    dispatcher.include_router(admin_commands.router)
    dispatcher.include_router(admin_callbacks.router)
    dispatcher.include_router(admin_replies.router)
    dispatcher.include_router(user_messages.router)

    try:
        await configure_bot_commands(bot)
        await notify_startup(bot, settings.admin_telegram_id)
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await bot.session.close()
        await database.close()


async def notify_startup(bot: Bot, admin_telegram_id: int) -> None:
    try:
        await bot.send_message(admin_telegram_id, "Relay bot started. Use /help for commands.")
    except TelegramAPIError as error:
        logger.warning("Could not send startup notification: %s", error)


async def configure_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="dashboard", description="Open admin dashboard"),
        BotCommand(command="chats", description="Show recent chats"),
        BotCommand(command="history", description="Show conversation history"),
        BotCommand(command="search", description="Search message history"),
        BotCommand(command="status", description="Show bot status"),
        BotCommand(command="help", description="Show help"),
    ]
    try:
        await bot.set_my_commands(commands)
    except TelegramAPIError as error:
        logger.warning("Could not configure bot commands: %s", error)


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
