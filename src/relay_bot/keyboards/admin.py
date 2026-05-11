from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def dashboard_keyboard(paused: bool) -> InlineKeyboardMarkup:
    pause_text = "▶️ Resume" if paused else "⏸ Pause"
    pause_action = "resume" if paused else "pause"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💬 Recent Chats", callback_data="dashboard:chats:0"),
                InlineKeyboardButton(text="📊 Status", callback_data="dashboard:status"),
            ],
            [
                InlineKeyboardButton(text=pause_text, callback_data=f"dashboard:{pause_action}"),
                InlineKeyboardButton(text="💾 Backup", callback_data="dashboard:backup"),
            ],
            [
                InlineKeyboardButton(text="❓ Help", callback_data="dashboard:help"),
            ],
        ]
    )


def chats_keyboard(chats: list[dict], *, page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=chat_button_text(chat),
                callback_data=f"dashboard:chat:{chat['telegram_id']}",
            )
        ]
        for chat in chats
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"dashboard:chats:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"dashboard:chats:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🏠 Dashboard", callback_data="dashboard:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def chat_detail_keyboard(user: dict) -> InlineKeyboardMarkup:
    user_id = user["telegram_id"]
    block_text = "✅ Unblock" if user["is_blocked"] else "🚫 Block"
    block_action = "unblock" if user["is_blocked"] else "block"
    mute_text = "🔔 Unmute" if user["is_muted"] else "🔕 Mute"
    mute_action = "unmute" if user["is_muted"] else "mute"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📜 History",
                    callback_data=f"dashboard:history:{user_id}",
                ),
                InlineKeyboardButton(text="📤 Export", callback_data=f"dashboard:export:{user_id}"),
            ],
            [
                InlineKeyboardButton(
                    text=block_text,
                    callback_data=f"dashboard:{block_action}:{user_id}",
                ),
                InlineKeyboardButton(
                    text=mute_text,
                    callback_data=f"dashboard:{mute_action}:{user_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📝 Note Help",
                    callback_data=f"dashboard:note_help:{user_id}",
                ),
                InlineKeyboardButton(
                    text="🗑 Forget",
                    callback_data=f"dashboard:forget_confirm:{user_id}",
                ),
            ],
            [
                InlineKeyboardButton(text="⬅️ Chats", callback_data="dashboard:chats:0"),
                InlineKeyboardButton(text="🏠 Dashboard", callback_data="dashboard:home"),
            ],
        ]
    )


def forget_confirm_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Yes, delete history",
                    callback_data=f"dashboard:forget:{user_id}",
                )
            ],
            [
                InlineKeyboardButton(text="Cancel", callback_data=f"dashboard:chat:{user_id}"),
            ],
        ]
    )


def relay_actions(user_id: int, blocked: bool = False, muted: bool = False) -> InlineKeyboardMarkup:
    block_text = "✅ Unblock" if blocked else "🚫 Block"
    block_action = "unblock" if blocked else "block"
    mute_text = "🔔 Unmute" if muted else "🔕 Mute"
    mute_action = "unmute" if muted else "mute"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=block_text,
                    callback_data=f"admin:{block_action}:{user_id}",
                ),
                InlineKeyboardButton(
                    text=mute_text,
                    callback_data=f"admin:{mute_action}:{user_id}",
                ),
            ],
            [
                InlineKeyboardButton(text="📜 History", callback_data=f"admin:history:{user_id}"),
                InlineKeyboardButton(text="📤 Export", callback_data=f"admin:export:{user_id}"),
            ],
            [
                InlineKeyboardButton(
                    text="📝 Add note",
                    callback_data=f"admin:note_help:{user_id}",
                ),
            ],
        ]
    )


def chat_button_text(chat: dict) -> str:
    status = ""
    if chat["is_blocked"]:
        status = " 🚫"
    elif chat["is_muted"]:
        status = " 🔕"
    name = str(chat["display_name"])[:28]
    return f"👤 {name}{status}"
