# Don Pablo Menu Bot

Telegram-бот для заказа рационов здорового питания (meal-prep delivery).

## Features

- 🍽 **Menu browsing** — browse daily menu with calories & macros
- 📅 **Flexible ordering** — order for multiple days with delivery schedule
- 🔄 **Dish swaps** — swap dishes within your ration
- 💳 **Multiple payment options** — cash, card terminal, bank transfer
- 🔔 **Manager notifications** — automatic order alerts to managers
- 🌍 **Multi-language** — Russian, English, Spanish support
- 🤖 **Manager bot** — separate bot for order management

## Tech Stack

- **Python 3.10+**
- **aiogram 3.x** — async Telegram Bot API framework
- **SQLite** — local database for orders & menu
- **gspread + oauth2client** — Google Sheets integration (optional)

## Project Structure

```
.
├── main.py                     # Entry point: runs client + manager bots
├── requirements.txt            # Python dependencies
├── bot/
│   ├── config.py               # Bot tokens, prices, delivery schedule
│   ├── config.example.py       # Example configuration
│   ├── data.py                 # Menu data (dishes, schedules)
│   ├── database.py             # SQLite database layer
│   ├── handlers.py             # Main bot handlers (client flow)
│   ├── handlers_extended.py    # Extended handlers (orders, payments)
│   ├── handlers_new_features.py # Additional features
│   ├── keyboards.py            # Telegram inline/reply keyboards
│   ├── manager_bot.py          # Manager notification sender
│   ├── manager_handlers.py     # Manager bot handlers
│   ├── manager_notifications.py # Notification formatting
│   ├── states.py               # FSM states
│   ├── translations.py         # Multi-language strings
│   ├── utils.py                # Helpers (date formatting, validation)
│   ├── gsheets.py              # Google Sheets integration
│   └── init_db.py              # Initial database seeding
```

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd "BOT 24"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or
   .venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the bot**
   ```bash
   cp bot/config.example.py bot/config.py
   # Edit bot/config.py and add your tokens
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

## Configuration

Get your bot token from [@BotFather](https://t.me/BotFather).

Get your numeric chat ID from [@userinfobot](https://t.me/userinfobot).

Edit `bot/config.py`:

```python
BOT_TOKEN = "your-main-bot-token"
MANAGER_BOT_TOKEN = "your-manager-bot-token"  # optional
MANAGER_CHAT_ID = 123456789                    # your chat ID
```

## Database

The bot uses SQLite (`orders.db`) which is created automatically on first run.

To seed initial menu data:
```bash
python -m bot.init_db
```

## Environment Variables (optional)

Instead of editing `config.py`, you can use `.env` file (not tracked by git):

```env
BOT_TOKEN=your-main-bot-token
MANAGER_BOT_TOKEN=your-manager-bot-token
MANAGER_CHAT_ID=123456789
```

## License

MIT
