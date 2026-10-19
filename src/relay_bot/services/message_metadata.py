from typing import Any

from aiogram.types import Message


def message_type(message: Message) -> str:
    # ContentType is a str enum; str() gives "ContentType.TEXT" on Python 3.11+.
    content_type = message.content_type
    return str(getattr(content_type, "value", content_type))


def extract_file_id(message: Message) -> str | None:
    if message.photo:
        return message.photo[-1].file_id
    for attribute in (
        "animation",
        "audio",
        "document",
        "sticker",
        "video",
        "video_note",
        "voice",
    ):
        value = getattr(message, attribute, None)
        if value is not None:
            return getattr(value, "file_id", None)
    return None


def compact_message_text(message: Message) -> str:
    if message.text:
        return message.text
    if message.caption:
        return message.caption
    return f"[{message_type(message)}]"


def raw_message_json(message: Message) -> dict[str, Any]:
    return message.model_dump(mode="json", exclude_none=True)
