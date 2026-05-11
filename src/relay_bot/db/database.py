from pathlib import Path
from types import TracebackType

import aiosqlite


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = await self.connection()
        schema_path = Path(__file__).with_name("schema.sql")
        await connection.executescript(schema_path.read_text(encoding="utf-8"))
        await self._migrate(connection)
        await connection.commit()

    async def _migrate(self, connection: aiosqlite.Connection) -> None:
        user_columns = await self._columns(connection, "users")
        if "is_muted" not in user_columns:
            await connection.execute(
                "ALTER TABLE users ADD COLUMN is_muted INTEGER NOT NULL DEFAULT 0"
            )
        if "muted_until" not in user_columns:
            await connection.execute("ALTER TABLE users ADD COLUMN muted_until TEXT")

    async def _columns(self, connection: aiosqlite.Connection, table: str) -> set[str]:
        cursor = await connection.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
        return {str(row["name"]) for row in rows}

    async def connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.path)
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def __aenter__(self) -> "Database":
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()
