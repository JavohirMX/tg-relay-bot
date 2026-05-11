from html import escape

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message

from relay_bot.config import Settings
from relay_bot.keyboards.admin import chats_keyboard, dashboard_keyboard
from relay_bot.repositories.store import Store
from relay_bot.services.dashboard import chats_page, dashboard_text, help_text, status_text
from relay_bot.services.export import ExportService
from relay_bot.services.relay import RelayService
from relay_bot.utils.datetime import format_datetime
from relay_bot.utils.history import sender_label

router = Router(name="admin_commands")


@router.message(Command("help"))
async def help_command(message: Message, settings: Settings) -> None:
    if not await is_admin(message, settings):
        return
    await message.answer(help_text())


@router.message(Command("dashboard"))
async def dashboard(message: Message, settings: Settings, store: Store) -> None:
    if not await is_admin(message, settings):
        return
    paused = await store.is_paused()
    await message.answer(await dashboard_text(store), reply_markup=dashboard_keyboard(paused))


@router.message(Command("status"))
async def status(message: Message, settings: Settings, store: Store) -> None:
    if not await is_admin(message, settings):
        return
    await message.answer(await status_text(store))


@router.message(Command("chats"))
async def chats(
    message: Message,
    settings: Settings,
    store: Store,
) -> None:
    if not await is_admin(message, settings):
        return
    text, rows, has_next = await chats_page(store, page=0)
    if not rows:
        await message.answer(text)
        return
    await message.answer(
        text,
        reply_markup=chats_keyboard(rows, page=0, has_next=has_next),
    )


@router.message(Command("pause"))
async def pause(message: Message, settings: Settings, store: Store) -> None:
    if not await is_admin(message, settings):
        return
    await store.set_paused(True)
    await message.answer("Incoming relays are paused.")


@router.message(Command("resume"))
async def resume(message: Message, settings: Settings, store: Store) -> None:
    if not await is_admin(message, settings):
        return
    await store.set_paused(False)
    await message.answer("Incoming relays are resumed.")


@router.message(Command("block"))
async def block(
    message: Message,
    command: CommandObject,
    settings: Settings,
    store: Store,
) -> None:
    if not await is_admin(message, settings):
        return
    user_id = await resolve_user_id(message, command.args, store)
    if user_id is None:
        await message.answer("Reply to a relay message or use /block USER_ID.")
        return
    await store.set_user_blocked(user_id, True)
    await message.answer(f"Blocked <code>{user_id}</code>.")


@router.message(Command("unblock"))
async def unblock(
    message: Message,
    command: CommandObject,
    settings: Settings,
    store: Store,
) -> None:
    if not await is_admin(message, settings):
        return
    user_id = await resolve_user_id(message, command.args, store)
    if user_id is None:
        await message.answer("Reply to a relay message or use /unblock USER_ID.")
        return
    await store.set_user_blocked(user_id, False)
    await message.answer(f"Unblocked <code>{user_id}</code>.")


@router.message(Command("mute"))
async def mute(
    message: Message,
    command: CommandObject,
    settings: Settings,
    store: Store,
) -> None:
    if not await is_admin(message, settings):
        return
    user_id = await resolve_user_id(message, command.args, store)
    if user_id is None:
        await message.answer("Reply to a relay message or use /mute USER_ID [MINUTES].")
        return
    minutes = mute_minutes_from_args(message, command.args or "")
    await store.set_user_muted(user_id, True, minutes=minutes)
    suffix = f" for {minutes} minutes" if minutes else ""
    await message.answer(f"Muted <code>{user_id}</code>{suffix}.")


@router.message(Command("unmute"))
async def unmute(
    message: Message,
    command: CommandObject,
    settings: Settings,
    store: Store,
) -> None:
    if not await is_admin(message, settings):
        return
    user_id = await resolve_user_id(message, command.args, store)
    if user_id is None:
        await message.answer("Reply to a relay message or use /unmute USER_ID.")
        return
    await store.set_user_muted(user_id, False)
    await message.answer(f"Unmuted <code>{user_id}</code>.")


@router.message(Command("note"))
async def note(
    message: Message,
    command: CommandObject,
    settings: Settings,
    store: Store,
) -> None:
    if not await is_admin(message, settings):
        return
    args = (command.args or "").strip()
    user_id = await resolve_user_id(message, args, store)
    note_text = note_text_from_args(message, args, user_id)
    if user_id is None or not note_text:
        await message.answer("Reply with /note NOTE_TEXT, or use /note USER_ID NOTE_TEXT.")
        return
    await store.append_note(user_id, note_text)
    await message.answer(f"Saved note for <code>{user_id}</code>.")


@router.message(Command("search"))
async def search(
    message: Message,
    command: CommandObject,
    settings: Settings,
    store: Store,
) -> None:
    if not await is_admin(message, settings):
        return
    query = (command.args or "").strip()
    if not query:
        await message.answer("Use /search QUERY.")
        return
    results = await store.search_messages(query, limit=10)
    if not results:
        await message.answer("No matches.")
        return
    lines = ["<b>Search results</b>"]
    for item in results:
        sender = escape(item["display_name"])
        body = item["text"] or item["caption"] or f"[{item['message_type']}]"
        direction = sender_label(item["direction"])
        lines.append(
            f"{escape(format_datetime(item['created_at']))} | {sender} | "
            f"{direction}: {escape(body[:120])}"
        )
    await message.answer("\n".join(lines))


@router.message(Command("history"))
async def history(
    message: Message,
    command: CommandObject,
    settings: Settings,
    store: Store,
    relay_service: RelayService,
) -> None:
    if not await is_admin(message, settings):
        return
    user_id = await resolve_user_id(message, command.args, store)
    if user_id is None:
        await message.answer("Reply to a relay message or use /history USER_ID [full|N].")
        return
    limit = history_limit_from_args(message, command.args or "")
    chunks = await relay_service.history_chunks(user_id, limit=limit)
    await send_history_chunks(message, user_id, chunks)


@router.message(Command("export"))
async def export(
    message: Message,
    command: CommandObject,
    settings: Settings,
    store: Store,
) -> None:
    if not await is_admin(message, settings):
        return
    user_id = await resolve_user_id(message, command.args, store)
    if user_id is None:
        await message.answer("Reply to a relay message or use /export USER_ID.")
        return
    export_service = ExportService(store)
    path = await export_service.export_conversation_text(user_id)
    await message.answer_document(FSInputFile(path), caption=f"Export for {user_id}")


@router.message(Command("backup"))
async def backup(message: Message, settings: Settings) -> None:
    if not await is_admin(message, settings):
        return
    if not settings.database_path.exists():
        await message.answer("Database file does not exist yet.")
        return
    await message.answer_document(FSInputFile(settings.database_path), caption="SQLite backup")


@router.message(Command("forget"))
async def forget(
    message: Message,
    command: CommandObject,
    settings: Settings,
    store: Store,
) -> None:
    if not await is_admin(message, settings):
        return
    user_id = await resolve_user_id(message, command.args, store)
    if user_id is None:
        await message.answer("Reply to a relay message or use /forget USER_ID.")
        return
    deleted = await store.forget_user(user_id)
    if deleted:
        await message.answer(f"Deleted conversation and history for <code>{user_id}</code>.")
    else:
        await message.answer(f"No stored conversation found for <code>{user_id}</code>.")


async def resolve_user_id(message: Message, args: str | None, store: Store) -> int | None:
    if message.reply_to_message is not None:
        mapping = await store.get_relay_mapping(
            admin_chat_id=message.chat.id,
            admin_message_id=message.reply_to_message.message_id,
        )
        if mapping is not None:
            return int(mapping["user_id"])
    if not args:
        return None
    first = args.split(maxsplit=1)[0]
    return int(first) if first.isdigit() else None


def note_text_from_args(message: Message, args: str, user_id: int | None) -> str:
    if user_id is None:
        return ""
    if message.reply_to_message is not None:
        return args
    parts = args.split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


def mute_minutes_from_args(message: Message, args: str) -> int | None:
    parts = args.split()
    if message.reply_to_message is not None:
        candidate = parts[0] if parts else ""
    else:
        candidate = parts[1] if len(parts) > 1 else ""
    return int(candidate) if candidate.isdigit() and int(candidate) > 0 else None


def history_limit_from_args(message: Message, args: str) -> int | None:
    parts = args.split()
    if not parts:
        return 20
    if message.reply_to_message is not None:
        candidate = parts[0]
    else:
        candidate = parts[1] if len(parts) > 1 else ""
    if candidate == "full":
        return None
    return int(candidate) if candidate.isdigit() and int(candidate) > 0 else 20


def parse_positive_int(value: str | None, *, default: int, maximum: int) -> int:
    if not value or not value.strip().isdigit():
        return default
    return min(int(value.strip()), maximum)


async def send_history_chunks(message: Message, user_id: int, chunks: list[str]) -> None:
    total = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        title = f"<b>History for {user_id}</b>"
        if total > 1:
            title = f"{title} ({index}/{total})"
        await message.answer(f"{title}\n{chunk}")


async def is_admin(message: Message, settings: Settings) -> bool:
    return message.from_user is not None and message.from_user.id == settings.admin_telegram_id
