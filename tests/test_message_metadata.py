from datetime import datetime

from aiogram.types import Chat, Message, PhotoSize, Sticker, User

from relay_bot.services.message_metadata import (
    compact_message_text,
    extract_file_id,
    message_type,
    raw_message_json,
)

CHAT = Chat(id=1, type="private")
SENDER = User(id=1, is_bot=False, first_name="Guest")


def make(**kwargs) -> Message:
    return Message(message_id=1, date=datetime(2026, 1, 1), chat=CHAT, from_user=SENDER, **kwargs)


def test_text_message():
    message = make(text="hello")
    assert message_type(message) == "text"
    assert compact_message_text(message) == "hello"
    assert extract_file_id(message) is None


def test_photo_uses_largest_size():
    message = make(
        photo=[
            PhotoSize(file_id="small", file_unique_id="a", width=10, height=10),
            PhotoSize(file_id="large", file_unique_id="b", width=100, height=100),
        ],
        caption="a photo",
    )
    assert extract_file_id(message) == "large"
    assert compact_message_text(message) == "a photo"


def test_sticker_without_text_gets_type_placeholder():
    message = make(
        sticker=Sticker(
            file_id="stk",
            file_unique_id="s",
            type="regular",
            width=512,
            height=512,
            is_animated=False,
            is_video=False,
        )
    )
    assert extract_file_id(message) == "stk"
    assert compact_message_text(message) == "[sticker]"


def test_raw_json_drops_empty_fields():
    raw = raw_message_json(make(text="hi"))
    assert raw["text"] == "hi"
    assert "photo" not in raw
