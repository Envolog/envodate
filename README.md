# UniMatch Ethiopia - University Dating Bot

A Telegram bot dating service specifically designed for Ethiopian university students with advanced matching, secure in-bot messaging, personalized notifications, and an anonymous confession platform.

## Features

- **User Registration**: Create a profile with name, age, gender, interests, university, bio, and photo
- **Profile Management**: Edit or delete your profile at any time
- **Channel Membership**: Requires users to join official and confession channels
- **Smart Matching**: Find potential matches based on gender preference, university, and mutual interest
- **Match Notifications**: Receive real-time alerts when you get likes and matches
- **Private Messaging**: Chat securely within the bot with your matches
- **Anonymous Confessions**: Submit anonymous confessions to the UniMatchConfessions channel
- **Moderation System**: Admin controls to manage reports and ban users

## Bot Commands

- `/start` - Begin registration process
- `/profile` - View, edit or delete your profile
- `/find` - Start finding potential matches
- `/matches` - View your current matches
- `/chat` - Access your active chats
- `/confess` - Submit an anonymous confession
- `/help` - View available commands
- `/ping` - Check if the bot is online

### Admin Commands

- `/admin` - Access admin commands
- `/reports` - View user reports
- `/banned` - View banned users
- `/ban <user_id>` - Ban a user
- `/unban <user_id>` - Unban a user

## Environment Variables

The following environment variables are used:

- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token (required)
- `DATABASE_URL` - PostgreSQL database URL
- `ADMIN_IDS` - Comma-separated list of admin Telegram IDs
- `OFFICIAL_CHANNEL_ID` - Channel ID for the official UniMatch Ethiopia channel
- `OFFICIAL_CHANNEL_USERNAME` - Username of the official channel (without @)
- `CONFESSION_CHANNEL_ID` - Channel ID for posting confessions
- `CONFESSION_CHANNEL_USERNAME` - Username of the confession channel (without @)
- `REQUIRE_CONFESSION_APPROVAL` - Whether confessions need admin approval (default: True)
- `REQUIRE_CHANNEL_MEMBERSHIP` - Whether to require channel membership (default: True)
- `ENABLE_NOTIFICATIONS` - Whether to enable like and match notifications (default: True)

## Technical Details

- **Backend**: Python with Flask
- **Bot Library**: python-telegram-bot
- **Database**: PostgreSQL
- **Web Server**: Gunicorn

## Development Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables
4. Initialize the database: `python scripts/initialize_database.py`
5. Run the application: `gunicorn --bind 0.0.0.0:5000 main:app`

## License

This project is licensed under the MIT License - see the LICENSE file for details.