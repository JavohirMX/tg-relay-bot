import pytest
from aiogram.types import User

from relay_bot.db.database import Database
from relay_bot.repositories.store import Store
from relay_bot.services.export import ExportService


async def make_store(tmp_path):
    database = Database(tmp_path / "relay.sqlite3")
    await database.initialize()
    return Store(database)


async def test_export_writes_header_and_messages(tmp_path):
    store = await make_store(tmp_path)
    await store.upsert_user(User(id=7, is_bot=False, first_name="Guest", username="guest7"))
    conversation_id = await store.ensure_conversation(7)
    await store.record_message(
        conversation_id=conversation_id,
        user_id=7,
        direction="inbound",
        message_type="text",
        text="hello there",
    )
    await store.record_message(
        conversation_id=conversation_id,
        user_id=7,
        direction="outbound",
        message_type="text",
        text="hi back",
    )

    path = await ExportService(store, tmp_path / "out").export_conversation_text(7)

    assert path.name == "conversation-7.txt"
    content = path.read_text(encoding="utf-8")
    assert "Username: @guest7" in content
    assert "Blocked: no" in content
    assert "hello there" in content
    assert "hi back" in content


async def test_export_unknown_user_raises(tmp_path):
    store = await make_store(tmp_path)
    with pytest.raises(ValueError, match="unknown user 99"):
        await ExportService(store, tmp_path / "out").export_conversation_text(99)
