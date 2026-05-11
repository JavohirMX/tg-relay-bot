from types import SimpleNamespace

from relay_bot.handlers.admin_commands import (
    history_limit_from_args,
    mute_minutes_from_args,
    note_text_from_args,
    resolve_user_id,
)


async def test_resolve_user_id_from_args():
    message = SimpleNamespace(reply_to_message=None)

    assert await resolve_user_id(message, "123 hello", store=None) == 123
    assert await resolve_user_id(message, "not-a-number", store=None) is None


def test_note_text_from_reply_uses_entire_args():
    message = SimpleNamespace(reply_to_message=object())

    assert note_text_from_args(message, "follow up later", 123) == "follow up later"


def test_note_text_from_direct_command_skips_user_id():
    message = SimpleNamespace(reply_to_message=None)

    assert note_text_from_args(message, "123 follow up later", 123) == "follow up later"


def test_mute_minutes_from_args():
    direct_message = SimpleNamespace(reply_to_message=None)
    reply_message = SimpleNamespace(reply_to_message=object())

    assert mute_minutes_from_args(direct_message, "123 60") == 60
    assert mute_minutes_from_args(reply_message, "15") == 15
    assert mute_minutes_from_args(direct_message, "123") is None


def test_history_limit_from_args():
    direct_message = SimpleNamespace(reply_to_message=None)
    reply_message = SimpleNamespace(reply_to_message=object())

    assert history_limit_from_args(direct_message, "123 full") is None
    assert history_limit_from_args(direct_message, "123 50") == 50
    assert history_limit_from_args(reply_message, "full") is None
    assert history_limit_from_args(reply_message, "") == 20
