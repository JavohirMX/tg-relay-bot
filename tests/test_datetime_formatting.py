from relay_bot.utils.datetime import format_datetime


def test_format_datetime_is_human_readable():
    formatted = format_datetime("2026-05-11T07:25:00+00:00")

    assert formatted.startswith("May 11, 2026 ")
    assert "2026" in formatted
    assert "+00:00" not in formatted


def test_format_datetime_handles_missing_or_unknown_values():
    assert format_datetime(None) == "unknown"
    assert format_datetime("not-a-date") == "not-a-date"
