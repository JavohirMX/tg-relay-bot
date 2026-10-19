import logging
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, ReactionTypeEmoji

from relay_bot.config import Settings
from relay_bot.keyboards.admin import relay_actions
from relay_bot.repositories.store import Store
from relay_bot.services.message_metadata import (
    compact_message_text,
    extract_file_id,
    message_type,
    raw_message_json,
)
from relay_bot.utils.datetime import format_date, format_datetime, format_time, parse_datetime
from relay_bot.utils.history import compact_media_groups, history_legend, sender_emoji

logger = logging.getLogger(__name__)
SENT_REACTION_EMOJI = "👌"


def _split_line(line: str, max_chars: int) -> list[str]:
    """Split one very long (already HTML-escaped) line without cutting an entity like &lt;."""
    pieces: list[str] = []
    while len(line) > max_chars:
        cut = max_chars
        amp = line.rfind("&", 0, cut)
        if amp != -1 and ";" not in line[amp:cut]:
            cut = amp or max_chars
        pieces.append(line[:cut])
        line = line[cut:]
    pieces.append(line)
    return pieces


class RelayService:
    def __init__(self, *, settings: Settings, store: Store) -> None:
        self.settings = settings
        self.store = store

    async def relay_from_user(self, bot: Bot, message: Message) -> None:
        if message.from_user is None:
            return

        user = await self.store.upsert_user(message.from_user)
        conversation_id = await self.store.ensure_conversation(message.from_user.id)
        card = await bot.send_message(
            chat_id=self.settings.admin_telegram_id,
            text=self._admin_card(user),
            reply_markup=relay_actions(
                message.from_user.id,
                blocked=bool(user["is_blocked"]),
                muted=bool(user["is_muted"]),
            ),
        )
        try:
            copied = await bot.copy_message(
                chat_id=self.settings.admin_telegram_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                reply_to_message_id=card.message_id,
            )
            admin_message_id = copied.message_id
        except TelegramAPIError as error:
            fallback = await bot.send_message(
                chat_id=self.settings.admin_telegram_id,
                text=(
                    "<b>Could not copy the original Telegram message.</b>\n"
                    f"Type: <code>{escape(message_type(message))}</code>\n"
                    f"Preview: {escape(self.preview(message))}\n"
                    f"Telegram error: <code>{escape(str(error))}</code>"
                ),
                reply_to_message_id=card.message_id,
            )
            admin_message_id = fallback.message_id
        stored_message_id = await self.store.record_message(
            conversation_id=conversation_id,
            user_id=message.from_user.id,
            direction="inbound",
            telegram_chat_id=message.chat.id,
            telegram_message_id=message.message_id,
            admin_chat_id=self.settings.admin_telegram_id,
            admin_message_id=admin_message_id,
            message_type=message_type(message),
            text=message.text,
            caption=message.caption,
            file_id=extract_file_id(message),
            media_group_id=message.media_group_id,
            raw=raw_message_json(message),
        )
        for mapped_admin_message_id in (card.message_id, admin_message_id):
            await self.store.add_relay_mapping(
                admin_chat_id=self.settings.admin_telegram_id,
                admin_message_id=mapped_admin_message_id,
                user_id=message.from_user.id,
                conversation_id=conversation_id,
                message_id=stored_message_id,
            )

    async def relay_from_admin_reply(self, bot: Bot, message: Message) -> bool:
        if message.reply_to_message is None:
            return False
        mapping = await self.store.get_relay_mapping(
            admin_chat_id=message.chat.id,
            admin_message_id=message.reply_to_message.message_id,
        )
        if mapping is None:
            return False

        try:
            sent = await bot.copy_message(
                chat_id=mapping["user_id"],
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            telegram_message_id = sent.message_id
        except TelegramAPIError as error:
            await message.reply(
                "Could not deliver that reply. The user may have blocked the bot, "
                "deleted the chat, or Telegram rejected the message.\n"
                f"<code>{escape(str(error))}</code>"
            )
            return True
        await self.store.record_message(
            conversation_id=mapping["conversation_id"],
            user_id=mapping["user_id"],
            direction="outbound",
            telegram_chat_id=mapping["user_id"],
            telegram_message_id=telegram_message_id,
            admin_chat_id=message.chat.id,
            admin_message_id=message.message_id,
            message_type=message_type(message),
            text=message.text,
            caption=message.caption,
            file_id=extract_file_id(message),
            media_group_id=message.media_group_id,
            raw=raw_message_json(message),
        )
        await self._react_sent(bot, message)
        return True

    async def record_inbound_only(self, message: Message) -> None:
        if message.from_user is None:
            return
        await self.store.upsert_user(message.from_user)
        conversation_id = await self.store.ensure_conversation(message.from_user.id)
        await self.store.record_message(
            conversation_id=conversation_id,
            user_id=message.from_user.id,
            direction="inbound",
            telegram_chat_id=message.chat.id,
            telegram_message_id=message.message_id,
            message_type=message_type(message),
            text=message.text,
            caption=message.caption,
            file_id=extract_file_id(message),
            media_group_id=message.media_group_id,
            raw=raw_message_json(message),
        )

    async def _react_sent(self, bot: Bot, message: Message) -> None:
        try:
            await bot.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reaction=[ReactionTypeEmoji(emoji=SENT_REACTION_EMOJI)],
            )
        except TelegramAPIError as error:
            logger.warning("Could not set sent reaction on admin message: %s", error)

    def _admin_card(self, user: dict) -> str:
        username = f"@{escape(user['username'])}" if user.get("username") else "No username"
        notes = escape(user["notes"]) if user.get("notes") else "No notes yet"
        blocked = "yes" if user.get("is_blocked") else "no"
        muted = "yes" if user.get("is_muted") else "no"
        if user.get("muted_until"):
            muted = f"until {escape(format_datetime(user['muted_until']))}"
        return (
            "<b>New relay message</b>\n"
            f"From: <b>{escape(user['display_name'])}</b>\n"
            f"Username: {username}\n"
            f"Telegram ID: <code>{user['telegram_id']}</code>\n"
            f"First seen: {escape(format_datetime(user['first_seen_at']))}\n"
            f"Last seen: {escape(format_datetime(user['last_seen_at']))}\n"
            f"Blocked: {blocked}\n"
            f"Muted: {muted}\n"
            f"Notes: {notes}\n\n"
            "Reply to this relay thread to respond."
        )

    async def short_history(self, user_id: int, limit: int = 5) -> str:
        messages = await self.store.conversation_messages(user_id, limit=limit)
        if not messages:
            return "No stored messages for this user yet."
        return "\n".join(self._history_lines(messages[-limit:]))

    async def full_history_chunks(self, user_id: int, max_chars: int = 3500) -> list[str]:
        return await self.history_chunks(user_id, limit=None, max_chars=max_chars)

    async def history_chunks(
        self, user_id: int, limit: int | None = 20, max_chars: int = 3500
    ) -> list[str]:
        messages = await self.store.conversation_messages(user_id, limit=None)
        if not messages:
            return ["No stored messages for this user yet."]
        if limit is not None:
            messages = messages[-limit:]
        lines = [
            piece
            for line in self._history_lines(messages)
            for piece in _split_line(line, max_chars)
        ]
        chunks: list[str] = []
        current = ""
        for line in lines:
            next_value = f"{current}\n{line}" if current else line
            if len(next_value) > max_chars and current:
                chunks.append(current)
                current = line
            else:
                current = next_value
        if current:
            chunks.append(current)
        return chunks

    def _history_lines(self, messages: list[dict]) -> list[str]:
        lines = [f"<b>{escape(history_legend())}</b>"]
        current_date = None
        for item in compact_media_groups(messages):
            direction = sender_emoji(item["direction"])
            body = item["text"] or item["caption"] or f"[{item['message_type']}]"
            timestamp = parse_datetime(item["created_at"])
            if timestamp is None:
                fallback_timestamp = escape(format_datetime(item["created_at"]))
                lines.append(f"{fallback_timestamp} {direction}: {escape(body)}")
                continue
            if timestamp.date() != current_date:
                current_date = timestamp.date()
                lines.append(f"<b>{escape(format_date(timestamp))}</b>")
            lines.append(f"{escape(format_time(timestamp))} {direction}: {escape(body)}")
        return lines

    def preview(self, message: Message) -> str:
        return compact_message_text(message)
