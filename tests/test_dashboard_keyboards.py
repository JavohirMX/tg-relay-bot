from relay_bot.keyboards.admin import chat_button_text, dashboard_keyboard


def test_dashboard_keyboard_switches_pause_action():
    active_keyboard = dashboard_keyboard(paused=False)
    paused_keyboard = dashboard_keyboard(paused=True)

    assert active_keyboard.inline_keyboard[1][0].text == "⏸ Pause"
    assert active_keyboard.inline_keyboard[1][0].callback_data == "dashboard:pause"
    assert paused_keyboard.inline_keyboard[1][0].text == "▶️ Resume"
    assert paused_keyboard.inline_keyboard[1][0].callback_data == "dashboard:resume"


def test_chat_button_text_includes_status():
    assert chat_button_text({"display_name": "Alex", "is_blocked": 0, "is_muted": 0}) == "👤 Alex"
    assert (
        chat_button_text({"display_name": "Alex", "is_blocked": 1, "is_muted": 0})
        == "👤 Alex 🚫"
    )
    assert (
        chat_button_text({"display_name": "Alex", "is_blocked": 0, "is_muted": 1})
        == "👤 Alex 🔕"
    )
