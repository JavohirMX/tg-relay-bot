import json
from datetime import UTC, datetime, timedelta
from typing import Any

from aiogram.types import User

from relay_bot.db.database import Database
from relay_bot.utils.datetime import format_datetime


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def row_to_dict(row: Any | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class Store:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def upsert_user(self, telegram_user: User) -> dict[str, Any]:
        connection = await self.database.connection()
        display_name = telegram_user.full_name or telegram_user.username or str(telegram_user.id)
        now = utc_now_iso()
        await connection.execute(
            """
            INSERT INTO users (
                telegram_id, username, first_name, last_name, display_name, is_bot,
                first_seen_at, last_seen_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                display_name = excluded.display_name,
                is_bot = excluded.is_bot,
                last_seen_at = excluded.last_seen_at,
                updated_at = excluded.updated_at
            """,
            (
                telegram_user.id,
                telegram_user.username,
                telegram_user.first_name,
                telegram_user.last_name,
                display_name,
                int(telegram_user.is_bot),
                now,
                now,
                now,
            ),
        )
        await connection.commit()
        user = await self.get_user(telegram_user.id)
        if user is None:
            raise RuntimeError("failed to upsert user")
        return user

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        connection = await self.database.connection()
        cursor = await connection.execute("SELECT * FROM users WHERE telegram_id = ?", (user_id,))
        return row_to_dict(await cursor.fetchone())

    async def ensure_conversation(self, user_id: int) -> int:
        connection = await self.database.connection()
        now = utc_now_iso()
        await connection.execute(
            """
            INSERT INTO conversations(user_id, created_at, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET updated_at = excluded.updated_at
            """,
            (user_id, now, now),
        )
        await connection.commit()
        cursor = await connection.execute(
            "SELECT id FROM conversations WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("failed to create conversation")
        return int(row["id"])

    async def record_message(
        self,
        *,
        conversation_id: int,
        user_id: int,
        direction: str,
        message_type: str,
        telegram_chat_id: int | None = None,
        telegram_message_id: int | None = None,
        admin_chat_id: int | None = None,
        admin_message_id: int | None = None,
        text: str | None = None,
        caption: str | None = None,
        file_id: str | None = None,
        media_group_id: str | None = None,
        raw: dict[str, Any] | None = None,
    ) -> int:
        connection = await self.database.connection()
        cursor = await connection.execute(
            """
            INSERT INTO messages (
                conversation_id, user_id, direction, telegram_chat_id, telegram_message_id,
                admin_chat_id, admin_message_id, message_type, text, caption, file_id,
                media_group_id, raw_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                user_id,
                direction,
                telegram_chat_id,
                telegram_message_id,
                admin_chat_id,
                admin_message_id,
                message_type,
                text,
                caption,
                file_id,
                media_group_id,
                json.dumps(raw or {}, ensure_ascii=False, default=str),
                utc_now_iso(),
            ),
        )
        await connection.commit()
        return int(cursor.lastrowid)

    async def add_relay_mapping(
        self,
        *,
        admin_chat_id: int,
        admin_message_id: int,
        user_id: int,
        conversation_id: int,
        message_id: int | None,
    ) -> None:
        connection = await self.database.connection()
        await connection.execute(
            """
            INSERT OR REPLACE INTO relay_mappings(
                admin_chat_id, admin_message_id, user_id, conversation_id, message_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (admin_chat_id, admin_message_id, user_id, conversation_id, message_id, utc_now_iso()),
        )
        await connection.commit()

    async def get_relay_mapping(
        self, *, admin_chat_id: int, admin_message_id: int
    ) -> dict[str, Any] | None:
        connection = await self.database.connection()
        cursor = await connection.execute(
            """
            SELECT * FROM relay_mappings
            WHERE admin_chat_id = ? AND admin_message_id = ?
            """,
            (admin_chat_id, admin_message_id),
        )
        return row_to_dict(await cursor.fetchone())

    async def set_user_blocked(self, user_id: int, blocked: bool) -> None:
        connection = await self.database.connection()
        await connection.execute(
            "UPDATE users SET is_blocked = ?, updated_at = ? WHERE telegram_id = ?",
            (int(blocked), utc_now_iso(), user_id),
        )
        await connection.commit()

    async def set_user_muted(self, user_id: int, muted: bool, minutes: int | None = None) -> None:
        connection = await self.database.connection()
        muted_until = None
        if muted and minutes is not None:
            muted_until = (
                datetime.now(UTC).replace(microsecond=0) + timedelta(minutes=minutes)
            ).isoformat()
        await connection.execute(
            """
            UPDATE users
            SET is_muted = ?, muted_until = ?, updated_at = ?
            WHERE telegram_id = ?
            """,
            (int(muted), muted_until, utc_now_iso(), user_id),
        )
        await connection.commit()

    async def is_user_muted(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if user is None or not user["is_muted"]:
            return False
        muted_until = user["muted_until"]
        if not muted_until:
            return True
        until = datetime.fromisoformat(muted_until)
        if until.tzinfo is None:
            until = until.replace(tzinfo=UTC)
        if until > datetime.now(UTC):
            return True
        await self.set_user_muted(user_id, False)
        return False

    async def forget_user(self, user_id: int) -> bool:
        connection = await self.database.connection()
        cursor = await connection.execute("DELETE FROM users WHERE telegram_id = ?", (user_id,))
        await connection.commit()
        return cursor.rowcount > 0

    async def append_note(self, user_id: int, note: str) -> None:
        connection = await self.database.connection()
        user = await self.get_user(user_id)
        if user is None:
            raise ValueError(f"unknown user {user_id}")
        now = utc_now_iso()
        prefix = f"[{format_datetime(now)}] "
        existing = user["notes"] or ""
        updated = f"{existing}\n{prefix}{note}".strip()
        await connection.execute(
            "UPDATE users SET notes = ?, updated_at = ? WHERE telegram_id = ?",
            (updated, now, user_id),
        )
        await connection.commit()

    async def set_paused(self, paused: bool) -> None:
        await self.set_setting("paused", "true" if paused else "false")

    async def is_paused(self) -> bool:
        value = await self.get_setting("paused")
        return value == "true"

    async def set_setting(self, key: str, value: str) -> None:
        connection = await self.database.connection()
        await connection.execute(
            """
            INSERT INTO settings(key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, utc_now_iso()),
        )
        await connection.commit()

    async def get_setting(self, key: str) -> str | None:
        connection = await self.database.connection()
        cursor = await connection.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return str(row["value"]) if row else None

    async def get_rate_limit(self, user_id: int) -> dict[str, Any] | None:
        connection = await self.database.connection()
        cursor = await connection.execute("SELECT * FROM rate_limits WHERE user_id = ?", (user_id,))
        return row_to_dict(await cursor.fetchone())

    async def set_rate_limit(
        self,
        *,
        user_id: int,
        window_started_at: str,
        message_count: int,
        cooldown_until: str | None,
    ) -> None:
        connection = await self.database.connection()
        await connection.execute(
            """
            INSERT INTO rate_limits(user_id, window_started_at, message_count, cooldown_until)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                window_started_at = excluded.window_started_at,
                message_count = excluded.message_count,
                cooldown_until = excluded.cooldown_until
            """,
            (user_id, window_started_at, message_count, cooldown_until),
        )
        await connection.commit()

    async def active_conversation_count(self) -> int:
        connection = await self.database.connection()
        cursor = await connection.execute(
            "SELECT COUNT(*) AS total FROM conversations WHERE status = 'active'"
        )
        row = await cursor.fetchone()
        return int(row["total"])

    async def blocked_user_count(self) -> int:
        connection = await self.database.connection()
        cursor = await connection.execute(
            "SELECT COUNT(*) AS total FROM users WHERE is_blocked = 1"
        )
        row = await cursor.fetchone()
        return int(row["total"])

    async def muted_user_count(self) -> int:
        connection = await self.database.connection()
        cursor = await connection.execute("SELECT COUNT(*) AS total FROM users WHERE is_muted = 1")
        row = await cursor.fetchone()
        return int(row["total"])

    async def message_count(self) -> int:
        connection = await self.database.connection()
        cursor = await connection.execute("SELECT COUNT(*) AS total FROM messages")
        row = await cursor.fetchone()
        return int(row["total"])

    async def search_messages(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        connection = await self.database.connection()
        like = f"%{query}%"
        cursor = await connection.execute(
            """
            SELECT m.*, u.display_name, u.username
            FROM messages m
            JOIN users u ON u.telegram_id = m.user_id
            WHERE COALESCE(m.text, '') LIKE ? OR COALESCE(m.caption, '') LIKE ?
            ORDER BY m.created_at DESC
            LIMIT ?
            """,
            (like, like, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def recent_chats(self, limit: int = 10) -> list[dict[str, Any]]:
        connection = await self.database.connection()
        cursor = await connection.execute(
            """
            SELECT
                u.*,
                c.id AS conversation_id,
                m.direction AS last_direction,
                m.message_type AS last_message_type,
                m.text AS last_text,
                m.caption AS last_caption,
                m.created_at AS last_message_at
            FROM users u
            JOIN conversations c ON c.user_id = u.telegram_id
            LEFT JOIN messages m ON m.id = (
                SELECT id FROM messages
                WHERE user_id = u.telegram_id
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            )
            ORDER BY COALESCE(m.created_at, c.updated_at) DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def conversation_messages(
        self, user_id: int, limit: int | None = 500
    ) -> list[dict[str, Any]]:
        connection = await self.database.connection()
        query = """
        SELECT m.*, u.display_name, u.username
        FROM messages m
        JOIN users u ON u.telegram_id = m.user_id
        WHERE m.user_id = ?
        ORDER BY m.created_at ASC
        """
        parameters: tuple[int] | tuple[int, int] = (user_id,)
        if limit is not None:
            query += " LIMIT ?"
            parameters = (user_id, limit)
        cursor = await connection.execute(query, parameters)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
