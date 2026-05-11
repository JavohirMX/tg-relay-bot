from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile, Message

from relay_bot.config import Settings
from relay_bot.keyboards.admin import (
    chat_detail_keyboard,
    chats_keyboard,
    dashboard_keyboard,
    forget_confirm_keyboard,
    relay_actions,
)
from relay_bot.repositories.store import Store
from relay_bot.services.dashboard import (
    chat_detail_text,
    chats_page,
    dashboard_text,
    help_text,
    status_text,
)
from relay_bot.services.export import ExportService
from relay_bot.services.relay import RelayService

router = Router(name="admin_callbacks")


@router.callback_query()
async def admin_callback(
    callback: CallbackQuery,
    settings: Settings,
    store: Store,
    relay_service: RelayService,
) -> None:
    if callback.from_user.id != settings.admin_telegram_id:
        await callback.answer("Not authorized.", show_alert=True)
        return
    if callback.data and callback.data.startswith("dashboard:"):
        await handle_dashboard_callback(callback, settings, store, relay_service)
        return
    if not callback.data or not callback.data.startswith("admin:"):
        return

    try:
        _, action, raw_user_id = callback.data.split(":", maxsplit=2)
        user_id = int(raw_user_id)
    except ValueError:
        await callback.answer("Invalid action.", show_alert=True)
        return
    reply_target = callback.message if isinstance(callback.message, Message) else None

    if action == "block":
        await store.set_user_blocked(user_id, True)
        user = await store.get_user(user_id)
        await callback.answer("Blocked.")
        if reply_target and user:
            await reply_target.edit_reply_markup(
                reply_markup=relay_actions(user_id, blocked=True, muted=bool(user["is_muted"]))
            )
        return
    if action == "unblock":
        await store.set_user_blocked(user_id, False)
        user = await store.get_user(user_id)
        await callback.answer("Unblocked.")
        if reply_target and user:
            await reply_target.edit_reply_markup(
                reply_markup=relay_actions(user_id, blocked=False, muted=bool(user["is_muted"]))
            )
        return
    if action == "mute":
        await store.set_user_muted(user_id, True)
        user = await store.get_user(user_id)
        await callback.answer("Muted.")
        if reply_target and user:
            await reply_target.edit_reply_markup(
                reply_markup=relay_actions(user_id, blocked=bool(user["is_blocked"]), muted=True)
            )
        return
    if action == "unmute":
        await store.set_user_muted(user_id, False)
        user = await store.get_user(user_id)
        await callback.answer("Unmuted.")
        if reply_target and user:
            await reply_target.edit_reply_markup(
                reply_markup=relay_actions(user_id, blocked=bool(user["is_blocked"]), muted=False)
            )
        return
    if action == "history":
        await callback.answer()
        if reply_target:
            chunks = await relay_service.full_history_chunks(user_id)
            total = len(chunks)
            for index, chunk in enumerate(chunks, start=1):
                title = f"<b>Full history for {user_id}</b>"
                if total > 1:
                    title = f"{title} ({index}/{total})"
                await reply_target.answer(f"{title}\n{chunk}")
        return
    if action == "export":
        path = await ExportService(store).export_conversation_text(user_id)
        await callback.answer("Export ready.")
        if reply_target:
            await reply_target.answer_document(FSInputFile(path), caption=f"Export for {user_id}")
        return
    if action == "note_help":
        await callback.answer()
        if reply_target:
            await reply_target.answer(
                f"Reply to a relay message with <code>/note your note</code>, "
                f"or use <code>/note {user_id} your note</code>."
            )
        return

    await callback.answer("Unknown action.", show_alert=True)


async def handle_dashboard_callback(
    callback: CallbackQuery,
    settings: Settings,
    store: Store,
    relay_service: RelayService,
) -> None:
    if not callback.data:
        return
    reply_target = callback.message if isinstance(callback.message, Message) else None
    parts = callback.data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action == "home":
        await callback.answer()
        await edit_or_answer(
            reply_target,
            await dashboard_text(store),
            dashboard_keyboard(await store.is_paused()),
        )
        return

    if action == "status":
        await callback.answer()
        await edit_or_answer(
            reply_target,
            await status_text(store),
            dashboard_keyboard(await store.is_paused()),
        )
        return

    if action == "help":
        await callback.answer()
        await edit_or_answer(reply_target, help_text(), dashboard_keyboard(await store.is_paused()))
        return

    if action == "chats":
        page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        text, rows, has_next = await chats_page(store, page=page)
        await callback.answer()
        await edit_or_answer(reply_target, text, chats_keyboard(rows, page=page, has_next=has_next))
        return

    if action == "pause":
        await store.set_paused(True)
        await callback.answer("Paused.")
        await edit_or_answer(
            reply_target,
            await dashboard_text(store),
            dashboard_keyboard(paused=True),
        )
        return

    if action == "resume":
        await store.set_paused(False)
        await callback.answer("Resumed.")
        await edit_or_answer(
            reply_target,
            await dashboard_text(store),
            dashboard_keyboard(paused=False),
        )
        return

    if action == "backup":
        await callback.answer("Preparing backup.")
        if reply_target:
            if settings.database_path.exists():
                await reply_target.answer_document(
                    FSInputFile(settings.database_path),
                    caption="SQLite backup",
                )
            else:
                await reply_target.answer("Database file does not exist yet.")
        return

    if len(parts) < 3 or not parts[2].isdigit():
        await callback.answer("Invalid dashboard action.", show_alert=True)
        return

    user_id = int(parts[2])

    if action == "chat":
        await callback.answer()
        text, user = await chat_detail_text(store, user_id)
        await edit_or_answer(reply_target, text, chat_detail_keyboard(user) if user else None)
        return

    if action in {"block", "unblock", "mute", "unmute"}:
        if action == "block":
            await store.set_user_blocked(user_id, True)
            await callback.answer("Blocked.")
        elif action == "unblock":
            await store.set_user_blocked(user_id, False)
            await callback.answer("Unblocked.")
        elif action == "mute":
            await store.set_user_muted(user_id, True)
            await callback.answer("Muted.")
        else:
            await store.set_user_muted(user_id, False)
            await callback.answer("Unmuted.")
        text, user = await chat_detail_text(store, user_id)
        await edit_or_answer(reply_target, text, chat_detail_keyboard(user) if user else None)
        return

    if action == "history":
        await callback.answer()
        if reply_target:
            chunks = await relay_service.full_history_chunks(user_id)
            await send_history(reply_target, user_id, chunks)
        return

    if action == "export":
        path = await ExportService(store).export_conversation_text(user_id)
        await callback.answer("Export ready.")
        if reply_target:
            await reply_target.answer_document(FSInputFile(path), caption=f"Export for {user_id}")
        return

    if action == "note_help":
        await callback.answer()
        if reply_target:
            await reply_target.answer(
                f"Use <code>/note {user_id} your note</code>, or reply to a relay with "
                "<code>/note your note</code>."
            )
        return

    if action == "forget_confirm":
        await callback.answer()
        await edit_or_answer(
            reply_target,
            f"<b>Delete all stored history for <code>{user_id}</code>?</b>\n\n"
            "This cannot be undone.",
            forget_confirm_keyboard(user_id),
        )
        return

    if action == "forget":
        deleted = await store.forget_user(user_id)
        await callback.answer("Deleted." if deleted else "Nothing to delete.")
        await edit_or_answer(
            reply_target,
            (
                f"Deleted conversation and history for <code>{user_id}</code>."
                if deleted
                else f"No stored conversation found for <code>{user_id}</code>."
            ),
            dashboard_keyboard(await store.is_paused()),
        )
        return

    await callback.answer("Unknown dashboard action.", show_alert=True)


async def edit_or_answer(
    message: Message | None,
    text: str,
    reply_markup=None,
) -> None:
    if message is None:
        return
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        await message.answer(text, reply_markup=reply_markup)


async def send_history(message: Message, user_id: int, chunks: list[str]) -> None:
    total = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        title = f"<b>Full history for {user_id}</b>"
        if total > 1:
            title = f"{title} ({index}/{total})"
        await message.answer(f"{title}\n{chunk}")
