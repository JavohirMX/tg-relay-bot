from relay_bot.config import Settings


def test_settings_read_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("BOT_TOKEN", "123:test")
    monkeypatch.setenv("ADMIN_TELEGRAM_ID", "42")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "bot.sqlite3"))
    monkeypatch.setenv("RATE_LIMIT_MAX_MESSAGES", "7")

    settings = Settings()

    assert settings.bot_token == "123:test"
    assert settings.admin_telegram_id == 42
    assert settings.database_path == tmp_path / "bot.sqlite3"
    assert settings.rate_limit_max_messages == 7
