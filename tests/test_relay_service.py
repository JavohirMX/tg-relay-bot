from datetime import datetime
from types import SimpleNamespace

import pytest
from aiogram.exceptions import TelegramAPIError
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message, User

from relay_bot.config import Settings
from relay_bot.db.database import Database
from relay_bot.repositories.store import Store
from relay_bot.services.relay import RelayService

ADMIN_ID = 42
GUEST = User(id=1001, is_bot=False, first_name="Guest", username="guest1001")


class FakeBot:
    def __init__(self, *, fail_copy: bool = False) -> None:
        self.fail_copy = fail_copy
        self.sent: list[dict] = []
        self.copied: list[dict] = []
        self._next_id = 500

    def _id(self) -> int:
        self._next_id += 1
        return self._next_id

    async def send_message(self, **kwargs):
        self.sent.append(kwargs)
        return SimpleNamespace(message_id=self._id())

    async def copy_message(self, **kwargs):
        if self.fail_copy:
            raise TelegramAPIError(method=SendMessage(chat_id=1, text="x"), message="boom")
        self.copied.append(kwargs)
        return SimpleNamespace(message_id=self._id())

    async def set_message_reaction(self, **kwargs):
        return True


def settings(tmp_path) -> Settings:
    return Settings(BOT_TOKEN="1:t", ADMIN_TELEGRAM_ID=ADMIN_ID, DATABASE_PATH=tmp_path / "r.db")


@pytest.fixture
async def service(tmp_path):
    database = Database(tmp_path / "relay.sqlite3")
    await database.initialize()
    yield RelayService(settings=settings(tmp_path), store=Store(database))
    await database.close()


def guest_message(text="hello") -> Message:
    return Message(
        message_id=7,
        date=datetime(2026, 1, 1),
        chat=Chat(id=GUEST.id, type="private"),
        from_user=GUEST,
        text=text,
    )


async def test_relay_from_user_sends_card_copies_and_stores(service):
    bot = FakeBot()

    await service.relay_from_user(bot, guest_message())

    assert bot.sent[0]["chat_id"] == ADMIN_ID
    assert "Guest" in bot.sent[0]["text"]
    assert bot.copied[0]["from_chat_id"] == GUEST.id
    stored = await service.store.conversation_messages(GUEST.id, limit=10)
    assert [m["direction"] for m in stored] == ["inbound"]
    assert stored[0]["text"] == "hello"


async def test_copy_failure_falls_back_to_notice_and_still_stores(service):
    bot = FakeBot(fail_copy=True)

    await service.relay_from_user(bot, guest_message("hi <b>"))

    fallback = bot.sent[1]["text"]
    assert "Could not copy" in fallback
    assert "hi &lt;b&gt;" in fallback
    assert len(await service.store.conversation_messages(GUEST.id, limit=10)) == 1


async def test_admin_reply_routes_to_user_and_unmapped_reply_is_ignored(service):
    bot = FakeBot()
    await service.relay_from_user(bot, guest_message())
    card_id = 501  # first id the fake bot hands out is the relay card

    admin_chat = Chat(id=ADMIN_ID, type="private")
    admin = User(id=ADMIN_ID, is_bot=False, first_name="Admin")

    def admin_reply(reply_to_id: int) -> Message:
        original = Message(message_id=reply_to_id, date=datetime(2026, 1, 1), chat=admin_chat)
        return Message(
            message_id=90,
            date=datetime(2026, 1, 1),
            chat=admin_chat,
            from_user=admin,
            text="answer",
            reply_to_message=original,
        )

    assert await service.relay_from_admin_reply(bot, admin_reply(card_id)) is True
    assert bot.copied[-1]["chat_id"] == GUEST.id
    stored = await service.store.conversation_messages(GUEST.id, limit=10)
    assert [m["direction"] for m in stored] == ["inbound", "outbound"]

    assert await service.relay_from_admin_reply(bot, admin_reply(99999)) is False


async def test_history_chunks_stay_under_telegram_limit_for_long_escaped_messages(service):
    await service.store.upsert_user(GUEST)
    conversation_id = await service.store.ensure_conversation(GUEST.id)
    await service.store.record_message(
        conversation_id=conversation_id,
        user_id=GUEST.id,
        direction="inbound",
        message_type="text",
        text="<" * 3000,  # escapes to 12000 characters
    )

    chunks = await service.history_chunks(GUEST.id)

    assert len(chunks) > 1
    assert all(len(chunk) <= 4096 for chunk in chunks)
    assert "".join(chunks).count("&lt;") == 3000  # no entity was cut in half
