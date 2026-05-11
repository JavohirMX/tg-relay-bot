from aiogram import Bot, F, Router
from aiogram.types import Message

from relay_bot.config import Settings
from relay_bot.services.relay import RelayService

router = Router(name="admin_replies")


@router.message(F.reply_to_message)
async def handle_admin_reply(
    message: Message,
    bot: Bot,
    settings: Settings,
    relay_service: RelayService,
) -> None:
    if message.from_user is None or message.from_user.id != settings.admin_telegram_id:
        return
    if message.text and message.text.startswith("/"):
        return
    relayed = await relay_service.relay_from_admin_reply(bot, message)
    if not relayed:
        await message.reply("I could not find a relay mapping for that message.")
