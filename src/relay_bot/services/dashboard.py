from html import escape

from relay_bot.repositories.store import Store
from relay_bot.utils.datetime import format_datetime
from relay_bot.utils.history import sender_label

DASHBOARD_PAGE_SIZE = 8


async def dashboard_text(store: Store) -> str:
    paused = await store.is_paused()
    active = await store.active_conversation_count()
    blocked = await store.blocked_user_count()
    muted = await store.muted_user_count()
    messages = await store.message_count()
    return (
        "<b>💎 Relay Dashboard</b>\n\n"
        f"{'⏸' if paused else '✅'} Status: {'Paused' if paused else 'Active'}\n"
        f"💬 Chats: {active}\n"
        f"🚫 Blocked: {blocked}\n"
        f"🔕 Muted: {muted}\n"
        f"🗄 Stored messages: {messages}\n\n"
        "Use the buttons below for common actions."
    )


async def status_text(store: Store) -> str:
    paused = await store.is_paused()
    active = await store.active_conversation_count()
    blocked = await store.blocked_user_count()
    muted = await store.muted_user_count()
    messages = await store.message_count()
    return (
        "<b>📊 Relay bot status</b>\n"
        f"{'⏸' if paused else '✅'} Paused: {'yes' if paused else 'no'}\n"
        f"💬 Active conversations: {active}\n"
        f"🚫 Blocked users: {blocked}\n"
        f"🔕 Muted users: {muted}\n"
        f"🗄 Stored messages: {messages}"
    )


async def chats_page(store: Store, page: int) -> tuple[str, list[dict], bool]:
    page = max(0, page)
    limit = DASHBOARD_PAGE_SIZE + 1
    rows = await store.recent_chats(limit=(page + 1) * limit)
    page_rows = rows[page * DASHBOARD_PAGE_SIZE : (page + 1) * DASHBOARD_PAGE_SIZE]
    has_next = len(rows) > (page + 1) * DASHBOARD_PAGE_SIZE
    if not page_rows:
        return ("<b>💬 Recent chats</b>\n\nNo conversations yet.", [], False)

    lines = [f"<b>💬 Recent chats</b> (page {page + 1})"]
    for row in page_rows:
        status_bits = []
        if row["is_blocked"]:
            status_bits.append("🚫 blocked")
        if row["is_muted"]:
            status_bits.append("🔕 muted")
        status = f" ({', '.join(status_bits)})" if status_bits else ""
        message_type = row["last_message_type"] or "no messages"
        preview = row["last_text"] or row["last_caption"] or f"[{message_type}]"
        timestamp = format_datetime(row["last_message_at"])
        lines.append(
            f"👤 <code>{row['telegram_id']}</code> {escape(row['display_name'])}{status}\n"
            f"{escape(timestamp)} {sender_label(row['last_direction'] or 'system')}: "
            f"{escape(preview[:100])}"
        )
    return "\n\n".join(lines), page_rows, has_next


async def chat_detail_text(store: Store, user_id: int) -> tuple[str, dict | None]:
    user = await store.get_user(user_id)
    if user is None:
        return f"No stored conversation found for <code>{user_id}</code>.", None

    messages = await store.conversation_messages(user_id, limit=1)
    last = messages[-1] if messages else None
    notes = escape(user["notes"]) if user.get("notes") else "none"
    muted = "yes" if user["is_muted"] else "no"
    if user.get("muted_until"):
        muted = f"until {escape(format_datetime(user['muted_until']))}"
    username = (
        f"🔗 Username: @{escape(user['username'])}" if user.get("username") else "🔗 Username: none"
    )
    lines = [
        f"<b>👤 {escape(user['display_name'])}</b>",
        f"🆔 ID: <code>{user_id}</code>",
        username,
        f"🌱 First seen: {escape(format_datetime(user['first_seen_at']))}",
        f"🕒 Last seen: {escape(format_datetime(user['last_seen_at']))}",
        f"🚫 Blocked: {'yes' if user['is_blocked'] else 'no'}",
        f"🔕 Muted: {muted}",
        f"📝 Notes: {notes}",
    ]
    if last:
        body = last["text"] or last["caption"] or f"[{last['message_type']}]"
        lines.extend(
            [
                "",
                "<b>💬 Last message</b>",
                f"{escape(format_datetime(last['created_at']))} "
                f"{sender_label(last['direction'])}: {escape(body[:300])}",
            ]
        )
    return "\n".join(lines), user


def help_text() -> str:
    return (
        "<b>❓ Relay bot commands</b>\n"
        "🏠 /dashboard - open the button dashboard\n"
        "📊 /status - bot health and counters\n"
        "💬 /chats - recent conversations\n"
        "📜 /history - history for a replied relay, or /history USER_ID [full|N]\n"
        "🚫 /block, /unblock - block by reply or user ID\n"
        "🔕 /mute, /unmute - mute by reply or user ID; /mute USER_ID 60 snoozes for 60 minutes\n"
        "📝 /note - add a note by reply, or /note USER_ID text\n"
        "🔎 /search QUERY - search stored messages\n"
        "📤 /export - export one conversation by reply or user ID\n"
        "💾 /backup - send the SQLite database file\n"
        "🗑 /forget - delete a conversation by reply or user ID\n"
        "⏸ /pause, /resume - globally pause or resume incoming relays"
    )
