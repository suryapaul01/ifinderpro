# Telegram ID Finder Bot

we are now making A Telegram bot that helps users find Telegram IDs for users, channels, groups, and bots.

## Features

- Get Telegram IDs by forwarding messages
- Get Telegram IDs from usernames or t.me links
- Browse and select from your joined channels, groups, and contacts
- Support the developer with donations (Telegram Stars or TON crypto)
- Inline mode support for quick ID lookups

## Setup

1. Clone this repository
2. Create a `.env` file with the following content:
   ```
   BOT_TOKEN=your_telegram_bot_token
   ADMIN_IDS=your_telegram_id,another_admin_id
   TON_WALLET=your_ton_wallet_address  # Optional, for donation feature
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the bot:
   ```
   python bot.py
   ```

## Usage

### Basic Commands

- `/start` - Start the bot and see the main menu
- `/donate` - Support the developer with a donation

### Getting IDs

1. **Forward a message** from a user, channel, group, or bot to get its ID
2. **Send a username** (e.g., @username) to get its ID
3. **Send a t.me link** to get the ID of the linked entity
4. Use the **menu buttons** to browse and select from your contacts, channels, groups, or bots

### Inline Mode

You can use the bot in inline mode by typing `@your_bot_username` followed by a username or t.me link in any chat.

## Donation Options

### Telegram Stars
- Available denominations: 5, 10, 20, 50, 100, 500, 1000 stars

### TON Crypto
- Available denominations: 0.1, 0.2, 0.5, 1, 2, 5, 10 TON

## Notes

- The bot requires access to message metadata to extract IDs
- For privacy reasons, the bot does not store or log message content
- Some features require the bot to be added to groups or channels

## License

MIT License 
