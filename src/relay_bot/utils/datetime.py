from datetime import UTC, datetime


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone()


def format_datetime(value: str | None) -> str:
    local = parse_datetime(value)
    if local is None:
        return value or "unknown"
    return (
        f"{local:%b} {local.day}, {local.year} "
        f"{_hour_12(local)}:{local.minute:02d} {local:%p} {local:%Z}"
    )


def format_date(value: datetime) -> str:
    return f"{value:%b} {value.day}, {value.year}"


def format_time(value: datetime) -> str:
    return f"{_hour_12(value)}:{value.minute:02d} {value:%p}"


def _hour_12(value: datetime) -> int:
    hour = value.hour % 12
    return 12 if hour == 0 else hour
