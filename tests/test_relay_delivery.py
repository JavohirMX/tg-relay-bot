from datetime import UTC, datetime
from types import SimpleNamespace

from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message, User

from relay_bot.db.database import Database
from relay_bot.repositories.store import Store
from relay_bot.services.relay import RelayService


class FailingBot:
    async def send_message(self, **kwargs):
        raise TelegramForbiddenError(
            method=SendMessage(chat_id=1, text="x"), message="Forbidden: bot was blocked"
        )


def make_message(user_id: int = 1001, text: str = "hello") -> Message:
    return Message(
        message_id=7,
        date=datetime(2026, 1, 1, tzinfo=UTC),
        chat=Chat(id=user_id, type="private"),
        from_user=User(id=user_id, is_bot=False, first_name="Guest"),
        text=text,
    )


async def test_relay_from_user_keeps_message_when_admin_unreachable(tmp_path):
    database = Database(tmp_path / "relay.sqlite3")
    await database.initialize()
    store = Store(database)
    settings = SimpleNamespace(admin_telegram_id=42)
    service = RelayService(settings=settings, store=store)

    delivered = await service.relay_from_user(FailingBot(), make_message())

    assert delivered is False
    history = await store.conversation_messages(1001, limit=None)
    assert [item["text"] for item in history] == ["hello"]
    assert history[0]["direction"] == "inbound"
    await database.close()
