# Discord Activity Leaderboard Bot

A Discord bot that tracks user activity and maintains a leaderboard with various statistics and badges.

## Features

- Real-time message tracking
- User activity statistics
- Achievement badges
- Activity patterns analysis
- Automatic database backups
- Rate limiting for commands
- Configurable settings

## Setup

1. Create a `.env` file in the root directory with the following variables:

```env
DISCORD_TOKEN=your_bot_token
LEADERBOARD_CHANNEL_ID=your_channel_id
COMMAND_CHANNEL_ID=your_channel_id
TRACKED_CATEGORY_ID=your_category_id
EXCLUDED_CHANNEL_ID=your_channel_id
ADMIN_IDS=comma_separated_admin_ids
TRACKED_CHANNEL_IDS=comma_separated_channel_ids
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `backups` directory:

```bash
mkdir backups
```

4. Run the bot:

```bash
python bot.py
```

## Commands

- `!leaderboard` or `!lb` - Show the activity leaderboard
- `!stats [user]` - Show detailed statistics for a user
- `!reset` (Admin only) - Reset all statistics

## Badges

- 🦉 Night Owl - 30% of messages during night hours (10 PM - 4 AM)
- 🌅 Early Bird - 30% of messages during early hours (5 AM - 9 AM)
- 🎮 Weekend Warrior - 40% of messages during weekends
- 🔥 Consistent Contributor - Maintained a 7-day streak

## Database

The bot uses SQLite for data storage. The database file is automatically created when the bot starts.
Backups are created periodically in the `backups` directory.

## Configuration

You can modify various settings in `config.py`:
- Update intervals
- Rate limits
- Cache settings
- Activity hours
- Database settings

## Contributing

Feel free to submit issues and pull requests for new features or improvements. 