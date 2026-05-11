from pathlib import Path

from relay_bot.repositories.store import Store
from relay_bot.utils.datetime import format_datetime
from relay_bot.utils.history import compact_media_groups, sender_label


class ExportService:
    def __init__(self, store: Store, export_dir: Path | str = "exports") -> None:
        self.store = store
        self.export_dir = Path(export_dir)

    async def export_conversation_text(self, user_id: int) -> Path:
        user = await self.store.get_user(user_id)
        if user is None:
            raise ValueError(f"unknown user {user_id}")
        messages = await self.store.conversation_messages(user_id, limit=10_000)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        path = self.export_dir / f"conversation-{user_id}.txt"
        lines = [
            f"Conversation export for {user['display_name']} ({user_id})",
            f"Username: @{user['username']}" if user.get("username") else "Username: none",
            f"Blocked: {'yes' if user['is_blocked'] else 'no'}",
            f"Notes: {user['notes'] or 'none'}",
            "",
        ]
        for item in compact_media_groups(messages):
            direction = sender_label(item["direction"], style="long")
            body = item["text"] or item["caption"] or f"[{item['message_type']}]"
            lines.append(f"[{format_datetime(item['created_at'])}] {direction}: {body}")
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
