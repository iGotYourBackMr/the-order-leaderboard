import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN')
LEADERBOARD_CHANNEL_ID = int(os.getenv('LEADERBOARD_CHANNEL_ID', '1313777896996732960'))
COMMAND_CHANNELS = [int(os.getenv('COMMAND_CHANNEL_ID', '1313777896996732960'))]
TRACKED_CATEGORY_ID = int(os.getenv('TRACKED_CATEGORY_ID', '1311716522858778736'))
EXCLUDED_CHANNEL_ID = int(os.getenv('EXCLUDED_CHANNEL_ID', '1313777896996732960'))
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '1015740711020281906').split(',')]

# Tracked channels
TRACKED_CHANNEL_IDS = {
    int(id.strip())
    for id in os.getenv('TRACKED_CHANNEL_IDS', '1312211055405170758,1312211208190824519,'
                       '1312323497334276096,1312323584613679129,1312323996255260702,'
                       '1313655509521403954,1314115629460095037').split(',')
}

# Activity settings
NIGHT_OWL_HOURS = set(range(22, 24)).union(set(range(0, 4)))  # 10 PM to 4 AM
EARLY_BIRD_HOURS = set(range(5, 9))  # 5 AM to 9 AM

# Database settings
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///leaderboard.db')

# Cache settings
CACHE_DURATION = int(os.getenv('CACHE_DURATION', '300'))  # 5 minutes in seconds
MAX_CACHE_ITEMS = int(os.getenv('MAX_CACHE_ITEMS', '1000'))

# Update intervals
LEADERBOARD_UPDATE_INTERVAL = int(os.getenv('LEADERBOARD_UPDATE_INTERVAL', '3600'))  # 1 hour in seconds
MESSAGE_FETCH_INTERVAL = int(os.getenv('MESSAGE_FETCH_INTERVAL', '900'))  # 15 minutes in seconds

# Rate limiting
COMMAND_RATE_LIMIT = int(os.getenv('COMMAND_RATE_LIMIT', '5'))  # Commands per minute
BACKUP_INTERVAL = int(os.getenv('BACKUP_INTERVAL', '86400'))  # 24 hours in seconds 