from relay_bot.utils.history import compact_media_groups, history_legend, sender_emoji, sender_label


def test_sender_label_distinguishes_inbound_and_outbound():
    assert sender_label("inbound") == "👤 them"
    assert sender_label("outbound") == "💎 you"
    assert sender_label("inbound", style="long") == "👤 stranger"
    assert sender_label("outbound", style="long") == "💎 admin"


def test_history_legend_and_emoji_markers():
    assert history_legend() == "👤 them · 💎 you"
    assert sender_emoji("inbound") == "👤"
    assert sender_emoji("outbound") == "💎"


def test_compact_media_groups_summarizes_adjacent_album_items():
    messages = [
        {
            "media_group_id": "album-1",
            "direction": "inbound",
            "message_type": "photo",
            "caption": "first",
            "text": None,
        },
        {
            "media_group_id": "album-1",
            "direction": "inbound",
            "message_type": "photo",
            "caption": None,
            "text": None,
        },
    ]

    compacted = compact_media_groups(messages)

    assert len(compacted) == 1
    assert compacted[0]["text"] == "[album: 2 items, photo] first"
