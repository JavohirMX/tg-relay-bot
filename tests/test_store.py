from aiogram.types import User

from relay_bot.db.database import Database
from relay_bot.repositories.store import Store


async def test_store_creates_user_conversation_message_and_mapping(tmp_path):
    database = Database(tmp_path / "relay.sqlite3")
    await database.initialize()
    store = Store(database)

    user = await store.upsert_user(
        User(id=1001, is_bot=False, first_name="Guest", username="guest1001")
    )
    conversation_id = await store.ensure_conversation(1001)
    message_id = await store.record_message(
        conversation_id=conversation_id,
        user_id=1001,
        direction="inbound",
        message_type="text",
        telegram_chat_id=1001,
        telegram_message_id=10,
        admin_chat_id=42,
        admin_message_id=20,
        text="hello",
        raw={"ok": True},
    )
    await store.add_relay_mapping(
        admin_chat_id=42,
        admin_message_id=20,
        user_id=1001,
        conversation_id=conversation_id,
        message_id=message_id,
    )

    mapping = await store.get_relay_mapping(admin_chat_id=42, admin_message_id=20)
    results = await store.search_messages("hell")

    assert user["display_name"] == "Guest"
    assert mapping is not None
    assert mapping["user_id"] == 1001
    assert results[0]["text"] == "hello"

    await database.close()


async def test_store_blocks_notes_and_pause_state(tmp_path):
    database = Database(tmp_path / "relay.sqlite3")
    await database.initialize()
    store = Store(database)
    await store.upsert_user(User(id=1001, is_bot=False, first_name="Guest"))

    await store.set_user_blocked(1001, True)
    await store.append_note(1001, "spammy first contact")
    await store.set_paused(True)

    user = await store.get_user(1001)

    assert user is not None
    assert user["is_blocked"] == 1
    assert "spammy first contact" in user["notes"]
    assert await store.is_paused() is True

    await database.close()


async def test_conversation_messages_can_fetch_without_limit(tmp_path):
    database = Database(tmp_path / "relay.sqlite3")
    await database.initialize()
    store = Store(database)
    await store.upsert_user(User(id=1001, is_bot=False, first_name="Guest"))
    conversation_id = await store.ensure_conversation(1001)

    for index in range(3):
        await store.record_message(
            conversation_id=conversation_id,
            user_id=1001,
            direction="inbound",
            message_type="text",
            text=f"message {index}",
        )

    messages = await store.conversation_messages(1001, limit=None)

    assert [message["text"] for message in messages] == ["message 0", "message 1", "message 2"]

    await database.close()


async def test_store_mutes_recent_chats_and_forgets_user(tmp_path):
    database = Database(tmp_path / "relay.sqlite3")
    await database.initialize()
    store = Store(database)
    await store.upsert_user(User(id=1001, is_bot=False, first_name="Guest"))
    conversation_id = await store.ensure_conversation(1001)
    await store.record_message(
        conversation_id=conversation_id,
        user_id=1001,
        direction="inbound",
        message_type="text",
        text="hello",
    )

    await store.set_user_muted(1001, True, minutes=15)
    chats = await store.recent_chats()

    assert await store.is_user_muted(1001) is True
    assert chats[0]["telegram_id"] == 1001
    assert chats[0]["last_text"] == "hello"
    assert await store.forget_user(1001) is True
    assert await store.get_user(1001) is None

    await database.close()
