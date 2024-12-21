import discord
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncio
from models import Session, User, Message, ActivityPattern, Badge, UserBadge
from config import NIGHT_OWL_HOURS, EARLY_BIRD_HOURS
import logging
from functools import wraps
from collections import defaultdict

logger = logging.getLogger('LeaderboardBot')

def setup_logging():
    """Configure logging for the bot."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bot.log')
        ]
    )

def rate_limit(calls: int, period: float):
    """Rate limiting decorator for commands."""
    def decorator(func):
        last_reset = datetime.now()
        calls_made = defaultdict(int)
        
        @wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            nonlocal last_reset
            current_time = datetime.now()
            user_id = ctx.author.id
            
            # Reset counter if period has passed
            if (current_time - last_reset).total_seconds() > period:
                calls_made.clear()
                last_reset = current_time
            
            # Check rate limit
            if calls_made[user_id] >= calls:
                remaining_time = period - (current_time - last_reset).total_seconds()
                await ctx.send(f"Rate limit exceeded. Please try again in {remaining_time:.1f} seconds.")
                return
            
            calls_made[user_id] += 1
            return await func(ctx, *args, **kwargs)
        return wrapper
    return decorator

async def create_backup():
    """Create a backup of the database."""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_command = f'sqlite3 leaderboard.db ".backup \'backups/leaderboard_{timestamp}.db\'"'
        process = await asyncio.create_subprocess_shell(
            backup_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        logger.info(f"Database backup created: leaderboard_{timestamp}.db")
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")

def update_user_stats(session: Session, user_id: str, message_timestamp: datetime) -> User:
    """Update user statistics when a new message is processed."""
    user = session.query(User).filter_by(discord_id=user_id).first()
    if not user:
        user = User(
            discord_id=user_id,
            total_messages=0,
            streak=0,
            best_streak=0,
            night_owl_messages=0,
            early_bird_messages=0,
            weekend_messages=0,
            weekday_messages=0
        )
        session.add(user)
        session.flush()  # This will assign an ID to the user
    
    # Update basic stats
    if user.total_messages is None:
        user.total_messages = 0
    user.total_messages += 1
    
    current_date = message_timestamp.date()
    
    # Update streak
    if user.last_active_date:
        last_date = user.last_active_date.date()
        days_diff = (current_date - last_date).days
        
        if days_diff == 1:
            if user.streak is None:
                user.streak = 0
            user.streak += 1
            if user.best_streak is None:
                user.best_streak = 0
            user.best_streak = max(user.streak, user.best_streak)
        elif days_diff > 1:
            user.streak = 1
    else:
        user.streak = 1
    
    user.last_active_date = message_timestamp
    
    # Initialize counters if they're None
    if user.night_owl_messages is None:
        user.night_owl_messages = 0
    if user.early_bird_messages is None:
        user.early_bird_messages = 0
    if user.weekend_messages is None:
        user.weekend_messages = 0
    if user.weekday_messages is None:
        user.weekday_messages = 0
    
    # Update time-based stats
    hour = message_timestamp.hour
    if hour in NIGHT_OWL_HOURS:
        user.night_owl_messages += 1
    elif hour in EARLY_BIRD_HOURS:
        user.early_bird_messages += 1
    
    # Update day-based stats
    if message_timestamp.weekday() >= 5:  # Weekend (5=Saturday, 6=Sunday)
        user.weekend_messages += 1
    else:
        user.weekday_messages += 1
    
    return user

def check_and_award_badges(session: Session, user: User):
    """Check if user qualifies for any new badges and award them."""
    all_badges = session.query(Badge).all()
    
    for badge in all_badges:
        # Skip if user already has this badge
        if session.query(UserBadge).filter_by(user_id=user.id, badge_id=badge.id).first():
            continue
        
        awarded = False
        if badge.requirement_type == 'percentage':
            if badge.name == 'Night Owl':
                percentage = (user.night_owl_messages / user.total_messages * 100
                            if user.total_messages > 0 else 0)
                awarded = percentage >= badge.requirement_value
            elif badge.name == 'Early Bird':
                percentage = (user.early_bird_messages / user.total_messages * 100
                            if user.total_messages > 0 else 0)
                awarded = percentage >= badge.requirement_value
            elif badge.name == 'Weekend Warrior':
                percentage = (user.weekend_messages / user.total_messages * 100
                            if user.total_messages > 0 else 0)
                awarded = percentage >= badge.requirement_value
        elif badge.requirement_type == 'streak':
            awarded = user.streak >= badge.requirement_value
        
        if awarded:
            user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
            session.add(user_badge)

def create_leaderboard_embed(guild: discord.Guild, users: List[User], page: int = 0, 
                           users_per_page: int = 10) -> discord.Embed:
    """Create a formatted embed for the leaderboard."""
    start_idx = page * users_per_page
    page_users = users[start_idx:start_idx + users_per_page]
    total_pages = (len(users) + users_per_page - 1) // users_per_page
    
    embed = discord.Embed(
        title="🏆 Activity Leaderboard 🏆",
        description="Most active members in the server!",
        color=0xFF9300
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    for idx, user in enumerate(page_users, start=start_idx + 1):
        member = guild.get_member(int(user.discord_id))
        
        # Handle users who have left the server
        if member:
            display_name = member.display_name
            left_indicator = ""
        else:
            display_name = f"User left server (ID: {user.discord_id})"
            left_indicator = "👋 "  # Add waving hand emoji for users who left
        
        trophy = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else ""
        badges = [ub.badge.emoji for ub in user.badges]
        badge_str = " ".join(badges) if badges else ""
        
        # Get user's roles and check for special roles (only if user is still in server)
        special_emoji = ""
        if member:
            roles = [role.name for role in member.roles]
            if "Night Owl 🦉" in roles:
                special_emoji = "🦉"
            elif "Early Bird 🐦" in roles:
                special_emoji = "🐦"
        
        name = f"{left_indicator}{trophy}#{idx} {display_name} {special_emoji} {badge_str}"
        value = (
            f"Total Messages: **{user.total_messages}**\n"
            f"Last 24 hours: **{getattr(user, 'recent_messages', 0)}**\n"
            f"Current Streak: **{user.streak}** days\n"
            f"Best Streak: **{user.best_streak}** days"
        )
        
        embed.add_field(name=name.strip(), value=value, inline=False)
    
    embed.set_footer(text=f"Page {page + 1}/{total_pages} • "
                         f"Updated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return embed

def create_user_stats_embed(member: discord.Member, user: User) -> discord.Embed:
    """Create a formatted embed for user statistics."""
    embed = discord.Embed(
        title=f"📊 Activity Stats for {member.display_name}",
        color=0x00FF00
    )
    
    # Activity Overview
    overview = (f"Total Messages: **{user.total_messages}**\n"
               f"Current Streak: **{user.streak}** days\n"
               f"Best Streak: **{user.best_streak}** days")
    embed.add_field(name="📈 Overview", value=overview, inline=False)
    
    # Activity Patterns
    weekday_avg = user.weekday_messages / 5 if user.weekday_messages > 0 else 0
    weekend_avg = user.weekend_messages / 2 if user.weekend_messages > 0 else 0
    patterns = (f"Weekday Average: **{weekday_avg:.1f}** messages/day\n"
               f"Weekend Average: **{weekend_avg:.1f}** messages/day\n"
               f"Night Owl Activity: **{user.night_owl_messages}** messages\n"
               f"Early Bird Activity: **{user.early_bird_messages}** messages")
    embed.add_field(name="⏰ Activity Patterns", value=patterns, inline=False)
    
    # Badges
    if user.badges:
        badges = "\n".join([f"{ub.badge.emoji} {ub.badge.name} - {ub.badge.description}"
                           for ub in user.badges])
        embed.add_field(name="🏆 Badges Earned", value=badges, inline=False)
    
    return embed 