# Telegram Relay Bot

A local-first Telegram relay bot that lets strangers message a public bot while your personal account stays private. The bot relays incoming messages to your admin chat, lets you reply by replying to the relayed message, and stores conversation history in SQLite.

## Features

- Public `/start` flow with a professional welcome and rules message.
- Rich admin relay cards with sender profile, quick actions, and reply routing.
- Tap-first admin dashboard for status, recent chats, moderation, backup, and help.
- SQLite history for users, conversations, messages, relay mappings, rate limits, notes, and pause state.
- Broad Telegram message support through message copying and metadata/file ID storage.
- Admin commands for help, recent chats, history, moderation, backup, cleanup, and exports.
- Balanced per-user rate limiting with a warning before cooldown.
- Per-user mute/snooze for noisy conversations without blocking the stranger.

## Setup

1. Create a bot with [BotFather](https://t.me/BotFather) and copy the token.
2. Send a message to [userinfobot](https://t.me/userinfobot) or similar to get your numeric Telegram user ID.
3. Create a virtual environment and install the project:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

4. Create `.env` from the template:

```bash
cp .env.example .env
```

5. Fill in `BOT_TOKEN` and `ADMIN_TELEGRAM_ID`.
6. Run the bot:

```bash
relay-bot
```

## Admin Workflow

When a stranger messages the bot, you receive a rich relay card and a copy of their message. Reply to the copied message in your admin chat to send a response back to that stranger.

Send `/start` or `/dashboard` as the admin to open the button dashboard. From there you can view status, browse recent chats, open chat detail pages, pause/resume relays, export conversations, back up the database, and confirm destructive actions like forgetting history.

Useful commands:

- `/dashboard` opens the button dashboard.
- `/help` shows the full command list with examples.
- `/status` shows bot health, pause state, active chats, blocked count, muted count, and stored messages.
- `/chats` shows recent conversations with last-message previews.
- `/history` shows a replied conversation, or `/history USER_ID [full|N]`.
- `/block` blocks a user when used as a reply to a relayed message, or with a Telegram user ID.
- `/unblock` unblocks by reply or user ID.
- `/mute` mutes a user by reply or user ID; `/mute USER_ID 60` snoozes for 60 minutes.
- `/unmute` unmutes by reply or user ID.
- `/note` adds a note/tag to the current user when used as a reply, or with `USER_ID note text`.
- `/search` searches message history.
- `/export` exports a conversation by reply or user ID.
- `/backup` sends the SQLite database file.
- `/forget` deletes a conversation and its stored history by reply or user ID.
- `/pause` stops new incoming relays globally.
- `/resume` allows incoming relays again.

## Tests

```bash
pytest
ruff check .
```

## Privacy Notes

The bot stores full message history and Telegram file IDs in SQLite. It does not download media files locally by default. Keep the SQLite database and exports private, and avoid committing `.env`, `data/`, or `exports/`.
