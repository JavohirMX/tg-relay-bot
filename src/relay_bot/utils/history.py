def history_legend() -> str:
    return "👤 them · 💎 you"


def sender_emoji(direction: str) -> str:
    if direction == "inbound":
        return "👤"
    if direction == "outbound":
        return "💎"
    return "⚙️"


def sender_label(direction: str, *, style: str = "short") -> str:
    if direction == "inbound":
        return "👤 them" if style == "short" else "👤 stranger"
    if direction == "outbound":
        return "💎 you" if style == "short" else "💎 admin"
    return "⚙️ system"


def compact_media_groups(messages: list[dict]) -> list[dict]:
    compacted: list[dict] = []
    index = 0
    while index < len(messages):
        item = messages[index]
        media_group_id = item.get("media_group_id")
        if not media_group_id:
            compacted.append(item)
            index += 1
            continue

        group = [item]
        index += 1
        while (
            index < len(messages)
            and messages[index].get("media_group_id") == media_group_id
            and messages[index].get("direction") == item.get("direction")
        ):
            group.append(messages[index])
            index += 1

        if len(group) == 1:
            compacted.append(item)
            continue

        types = ", ".join(sorted({entry["message_type"] for entry in group}))
        captions = [
            entry["caption"] or entry["text"]
            for entry in group
            if entry.get("caption") or entry.get("text")
        ]
        summary = f"[album: {len(group)} items, {types}]"
        if captions:
            summary = f"{summary} {' / '.join(captions)}"
        compacted.append({**item, "text": summary, "caption": None})
    return compacted
