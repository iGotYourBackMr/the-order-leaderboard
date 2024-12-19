import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
import logging
from datetime import datetime, timedelta, UTC
import asyncio
from models import Session, User, Message, ActivityPattern, Badge, UserBadge, Base, engine
from utils import (
    setup_logging, rate_limit, create_backup, update_user_stats,
    check_and_award_badges, create_leaderboard_embed, create_user_stats_embed
)
from config import (
    TOKEN, LEADERBOARD_CHANNEL_ID, COMMAND_CHANNELS, TRACKED_CHANNEL_IDS,
    ADMIN_IDS, COMMAND_RATE_LIMIT, LEADERBOARD_UPDATE_INTERVAL,
    MESSAGE_FETCH_INTERVAL, BACKUP_INTERVAL
)

# Initialize logging
setup_logging()
logger = logging.getLogger('LeaderboardBot')
logger.setLevel(logging.DEBUG)  # Set to debug level for more detailed logs

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Global variables
message_pages = {}  # Track pages per message ID
last_leaderboard_message = None

async def fetch_message_history():
    """Fetch message history from all tracked channels."""
    logger.info("Starting message history fetch...")
    total_messages = 0
    new_messages = 0
    
    for guild in bot.guilds:
        for channel_id in TRACKED_CHANNEL_IDS:
            channel = bot.get_channel(channel_id)
            if not channel:
                logger.warning(f"Could not find channel with ID: {channel_id}")
                continue
                
            try:
                logger.info(f"Fetching messages from {channel.name} ({channel.id})")
                async for message in channel.history(limit=None):
                    if message.author.bot:
                        continue
                        
                    try:
                        session = Session()
                        
                        # Check if message already exists
                        existing_message = session.query(Message).filter_by(
                            discord_message_id=str(message.id)
                        ).first()
                        
                        if existing_message:
                            session.close()
                            total_messages += 1
                            continue
                        
                        # Update user stats
                        user = update_user_stats(session, str(message.author.id), message.created_at)
                        
                        # Store message
                        db_message = Message(
                            discord_message_id=str(message.id),
                            user_id=user.id,
                            channel_id=str(message.channel.id),
                            timestamp=message.created_at
                        )
                        session.add(db_message)
                        
                        # Check and award badges
                        check_and_award_badges(session, user)
                        
                        session.commit()
                        session.close()
                        
                        total_messages += 1
                        new_messages += 1
                        if total_messages % 100 == 0:
                            logger.info(f"Processed {total_messages} messages ({new_messages} new)...")
                            
                    except Exception as e:
                        logger.error(f"Error processing message {message.id}: {str(e)}")
                        if session:
                            session.rollback()
                            session.close()
                            
                logger.info(f"Completed fetching from {channel.name}")
                
            except discord.Forbidden:
                logger.warning(f"No access to channel: {channel.name}")
            except Exception as e:
                logger.error(f"Error fetching from {channel.name}: {str(e)}")
    
    logger.info(f"Message history fetch completed! Total messages processed: {total_messages} ({new_messages} new)")
    return total_messages, new_messages

async def post_initial_leaderboard():
    """Post the initial leaderboard message in the designated channel."""
    global last_leaderboard_message
    
    print("A. Starting post_initial_leaderboard function")
    session = None
    try:
        print(f"B. Getting channel {LEADERBOARD_CHANNEL_ID}")
        channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
        if not channel:
            print(f"Error: Could not find channel {LEADERBOARD_CHANNEL_ID}")
            logger.error(f"Could not find leaderboard channel with ID: {LEADERBOARD_CHANNEL_ID}")
            return
            
        print(f"C. Found channel: {channel.name}")
        
        print("D. Creating database session")
        session = Session()
        
        print("E. Creating database tables")
        Base.metadata.create_all(engine)
        
        print("F. Querying users")
        users = session.query(User).order_by(User.total_messages.desc()).all()
        print(f"G. Found {len(users)} users")
        
        if not users:
            print("H. No users found, sending message")
            await channel.send("No activity recorded yet! The leaderboard will update as users send messages.")
            return
            
        print("I. Getting recent messages for users")
        for user in users:
            user.recent_messages = get_recent_messages(session, user.id)
            
        print("J. Creating embed")
        embed = create_leaderboard_embed(channel.guild, users, 0)
        
        try:
            if last_leaderboard_message:
                print("K. Deleting old message")
                await last_leaderboard_message.delete()
        except Exception as e:
            print(f"Warning: Could not delete old message: {e}")
        
        print("L. Sending new message")
        last_leaderboard_message = await channel.send(embed=embed)
        print("M. Message sent")
        
        if len(users) > 10:
            print("N. Adding reactions")
            await last_leaderboard_message.add_reaction('⬅️')
            await last_leaderboard_message.add_reaction('➡️')
            print("O. Reactions added")
            
        print("P. Leaderboard posted successfully")
    except Exception as e:
        print(f"Error in post_initial_leaderboard: {str(e)}")
        logger.error(f"Error posting initial leaderboard: {str(e)}", exc_info=True)
    finally:
        if session:
            print("Q. Closing session")
            session.close()

@bot.event
async def on_ready():
    """Handle bot startup."""
    print("1. Bot ready event triggered")
    logger.info(f'Bot is ready! Logged in as {bot.user.name} ({bot.user.id})')
    
    # Check bot permissions
    channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
    if channel:
        permissions = channel.permissions_for(channel.guild.me)
        required_permissions = {
            'send_messages': 'Send Messages',
            'manage_messages': 'Manage Messages',
            'embed_links': 'Embed Links',
            'add_reactions': 'Add Reactions',
            'read_message_history': 'Read Message History'
        }
        
        missing_permissions = [
            perm_name for perm, perm_name in required_permissions.items()
            if not getattr(permissions, perm, False)
        ]
        
        if missing_permissions:
            logger.error(f"Missing required permissions in channel {channel.name}: {', '.join(missing_permissions)}")
            print(f"⚠️ Bot is missing required permissions: {', '.join(missing_permissions)}")
            return
    
    # Log the guilds the bot is in
    for guild in bot.guilds:
        print(f"2. Found guild: {guild.name}")
        logger.info(f'Bot is in guild: {guild.name} (ID: {guild.id})')
        logger.info(f'Command channels configured: {COMMAND_CHANNELS}')
        logger.info(f'Tracked channels configured: {TRACKED_CHANNEL_IDS}')
    
    print("3. About to fetch message history")
    # Fetch initial message history first
    try:
        total_messages, new_messages = await fetch_message_history()
        print(f"4. Message history fetched: {total_messages} messages")
        logger.info(f"Initial message fetch completed: {total_messages} messages processed ({new_messages} new)")
    except Exception as e:
        print(f"Error in message fetch: {str(e)}")
        logger.error(f"Error during initial message fetch: {str(e)}", exc_info=True)

    print("5. About to wait 2 seconds")
    # Wait a short moment to ensure everything is initialized
    await asyncio.sleep(2)
    
    print("6. About to post initial leaderboard")
    # Post initial leaderboard
    try:
        await post_initial_leaderboard()
        print("7. Initial leaderboard posted")
    except Exception as e:
        print(f"Error posting leaderboard: {str(e)}")
        logger.error(f"Error in on_ready while posting leaderboard: {str(e)}", exc_info=True)
    
    print("8. Starting background tasks")
    # Start background tasks
    update_leaderboard.start()
    backup_database.start()
    print("9. Bot startup complete")

@bot.command(name='fetch')
async def fetch_messages(ctx: Context):
    """Manually fetch message history."""
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You don't have permission to use this command.")
        return
        
    try:
        status_message = await ctx.send("📥 Starting message fetch...")
        total_messages, new_messages = await fetch_message_history()
        await status_message.edit(
            content=f"✅ Message fetch completed!\n"
                   f"• Total messages processed: {total_messages}\n"
                   f"• New messages added: {new_messages}"
        )
    except Exception as e:
        logger.error(f"Error during manual message fetch: {str(e)}")
        await ctx.send(f"❌ Error during message fetch: {str(e)}")

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    logger.info(f"Command error triggered: {type(error).__name__} - {str(error)}")
    
    if isinstance(error, commands.errors.CommandNotFound):
        await ctx.send(f"Command not found. Available commands: `!leaderboard` (or `!lb`), `!stats [user]`, `!reset` (admin only), `!fetch` (admin only)")
    elif isinstance(error, commands.errors.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.errors.NoPrivateMessage):
        await ctx.send("This command can only be used in a server.")
    else:
        logger.error(f"Unhandled command error in {ctx.command}: {str(error)}")

class DatabaseSession:
    """Context manager for database sessions."""
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = Session()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type is not None:
                self.session.rollback()
            self.session.close()

@tasks.loop(hours=1)
async def update_leaderboard():
    """Update the leaderboard message hourly at minute 00."""
    # Wait until the next hour
    now = datetime.now()
    minutes_to_wait = 60 - now.minute
    if minutes_to_wait > 0:
        await asyncio.sleep(minutes_to_wait * 60)
    
    channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
    if not channel:
        logger.error(f"Could not find leaderboard channel with ID: {LEADERBOARD_CHANNEL_ID}")
        return
        
    async with DatabaseSession() as session:
        try:
            # Delete previous hourly leaderboard messages
            async for message in channel.history(limit=100):
                if message.author == bot.user and not hasattr(message, 'manual_leaderboard'):
                    try:
                        await message.delete()
                    except discord.NotFound:
                        pass
                    except Exception as e:
                        logger.error(f"Error deleting message: {str(e)}")
            
            users = session.query(User).order_by(User.total_messages.desc()).all()
            
            if not users:
                return
                
            for user in users:
                user.recent_messages = get_recent_messages(session, user.id)
                
            guild = channel.guild
            embed = create_leaderboard_embed(guild, users, 0)
            
            # Send new leaderboard message
            new_message = await channel.send(embed=embed)
            
            # Add pagination reactions if there are more than 10 users
            if len(users) > 10:
                await new_message.add_reaction('⬅️')
                await new_message.add_reaction('➡️')
                
        except Exception as e:
            logger.error(f"Error updating leaderboard: {str(e)}")

@update_leaderboard.before_loop
async def before_update_leaderboard():
    """Wait until the next hour before starting the update loop."""
    await bot.wait_until_ready()
    now = datetime.now()
    next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    await asyncio.sleep((next_hour - now).total_seconds())

@tasks.loop(seconds=BACKUP_INTERVAL)
async def backup_database():
    """Periodically backup the database."""
    try:
        await create_backup()
    except Exception as e:
        logger.error(f"Error during database backup: {str(e)}")

@bot.event
async def on_message(message):
    """Handle new messages."""
    if message.author.bot:
        return
        
    # Process commands regardless of channel
    await bot.process_commands(message)
    
    # Only track messages in tracked channels
    if message.channel.id not in TRACKED_CHANNEL_IDS:
        return
        
    try:
        session = Session()
        
        # Update user stats
        user = update_user_stats(session, str(message.author.id), message.created_at)
        
        # Store message
        db_message = Message(
            discord_message_id=str(message.id),
            user_id=user.id,
            channel_id=str(message.channel.id),
            timestamp=message.created_at
        )
        session.add(db_message)
        
        # Check and award badges
        check_and_award_badges(session, user)
        
        session.commit()
        session.close()
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        if session:
            session.rollback()
            session.close()

def get_recent_messages(session: Session, user_id: int) -> int:
    """Get the number of messages sent by a user in the last 24 hours."""
    yesterday = datetime.utcnow() - timedelta(days=1)
    return session.query(Message).filter(
        Message.user_id == user_id,
        Message.timestamp >= yesterday
    ).count()

@bot.command(name='leaderboard', aliases=['lb'])
async def show_leaderboard(ctx: Context):
    """Display the server leaderboard."""
    global current_page
    
    logger.info(f"Starting leaderboard command from {ctx.author} in channel {ctx.channel.id}")
    current_page = 0  # Reset to first page
    
    session = None
    try:
        logger.info("Creating database session")
        session = Session()
        
        logger.info("Querying users from database")
        users = session.query(User).order_by(User.total_messages.desc()).all()
        logger.info(f"Found {len(users)} users")
        
        if not users:
            await ctx.send("No activity recorded yet!")
            return
            
        logger.info("Getting recent messages for users")
        for user in users:
            user.recent_messages = get_recent_messages(session, user.id)
            
        logger.info("Creating leaderboard embed")
        embed = create_leaderboard_embed(ctx.guild, users, current_page)
        
        logger.info("Sending new leaderboard message")
        message = await ctx.send(embed=embed)
        # Mark the message as manually called
        setattr(message, 'manual_leaderboard', True)
        
        if len(users) > 10:
            logger.info("Adding pagination reactions")
            await message.add_reaction('⬅️')
            await message.add_reaction('➡️')
            
        logger.info("Leaderboard command completed successfully")
    except Exception as e:
        logger.error(f"Error showing leaderboard: {type(e).__name__} - {str(e)}", exc_info=True)
    finally:
        if session:
            logger.info("Closing database session")
            session.close()

@bot.command(name='stats')
async def show_stats(ctx: Context, member: discord.Member = None):
    """Display statistics for a user."""
    logger.info(f"Stats command used by {ctx.author} in channel {ctx.channel.id}")
    
    member = member or ctx.author
    
    try:
        session = Session()
        user = session.query(User).filter_by(discord_id=str(member.id)).first()
        
        if not user:
            await ctx.send(f"{member.display_name} has no recorded activity yet!")
            return
            
        embed = create_user_stats_embed(member, user)
        await ctx.send(embed=embed)
        
        session.close()
    except Exception as e:
        logger.error(f"Error showing user stats: {str(e)}")
        await ctx.send("An error occurred while fetching user statistics.")
        if session:
            session.close()

@bot.command(name='reset')
async def reset_stats(ctx: Context):
    """Reset all leaderboard statistics."""
    logger.info(f"Reset command used by {ctx.author} in channel {ctx.channel.id}")
    
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ You don't have permission to use this command.")
        return
        
    try:
        # Create backup before reset
        await create_backup()
        
        session = Session()
        
        # Clear all data
        session.query(UserBadge).delete()
        session.query(Message).delete()
        session.query(ActivityPattern).delete()
        session.query(User).delete()
        
        session.commit()
        session.close()
        
        await ctx.send("✅ All statistics have been reset and a backup has been created.")
    except Exception as e:
        logger.error(f"Error resetting stats: {str(e)}")
        await ctx.send("An error occurred while resetting statistics.")
        if session:
            session.rollback()
            session.close()

@bot.event
async def on_reaction_add(reaction, user):
    """Handle reaction additions."""
    if user.bot:
        return
        
    # Handle pagination reactions
    if reaction.message.author == bot.user and len(reaction.message.embeds) > 0:
        message_id = str(reaction.message.id)
        current_page = message_pages.get(message_id, 0)
        
        try:
            async with DatabaseSession() as session:
                users = session.query(User).order_by(User.total_messages.desc()).all()
                max_pages = (len(users) - 1) // 10
                
                # Get recent messages for each user
                for user in users:
                    user.recent_messages = get_recent_messages(session, user.id)
                
                if str(reaction.emoji) == '➡️' and current_page < max_pages:
                    current_page += 1
                    message_pages[message_id] = current_page
                    embed = create_leaderboard_embed(reaction.message.guild, users, current_page)
                    await reaction.message.edit(embed=embed)
                elif str(reaction.emoji) == '⬅️' and current_page > 0:
                    current_page -= 1
                    message_pages[message_id] = current_page
                    embed = create_leaderboard_embed(reaction.message.guild, users, current_page)
                    await reaction.message.edit(embed=embed)
                    
                # Try to remove the user's reaction with better error handling
                try:
                    await reaction.remove(user)
                except discord.Forbidden:
                    logger.warning(f"Bot lacks permission to remove reactions in channel {reaction.message.channel.id}")
                except Exception as e:
                    logger.error(f"Error removing reaction: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error handling pagination: {str(e)}")
            return

    # Handle message reactions
    try:
        async with DatabaseSession() as session:
            message = session.query(Message).filter_by(
                discord_message_id=str(reaction.message.id)
            ).first()
            
            if message:
                message.reaction_count += 1
                session.commit()
                
    except Exception as e:
        logger.error(f"Error processing reaction: {str(e)}")

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")