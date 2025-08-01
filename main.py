import discord
import asyncpraw
import asyncio
import os
import json
import random
import logging
import sys
import shutil
from datetime import datetime, timedelta
from collections import deque
from discord.ext import commands, tasks
from dotenv import load_dotenv
from webserver import keep_alive
from discord import app_commands

# ==== Python 3.13 Fix ====
if sys.version_info >= (3, 13):
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

# ==== Setup ====
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('MemeBot')

# ==== CONFIG ====
SUB_FILE = "subreddits.json"
DEFAULT_SUBS = [
    "memes", "dankmemes", "funny", "me_irl",
    "animememes", "goodanimemes", "wholesomememes",
    "AdviceAnimals", "MemeEconomy", "terriblefacebookmemes",
    "nsfwmemes", "dankmemes_nsfw", "EdgyMemes", "darkmemers"
]

if os.path.exists(SUB_FILE):
    with open(SUB_FILE, "r") as f:
        ALL_MEMES = json.load(f)
else:
    ALL_MEMES = DEFAULT_SUBS
    with open(SUB_FILE, "w") as f:
        json.dump(ALL_MEMES, f, indent=2)

MEME_CHANNEL_ID = int(os.environ.get('MEMES_CHANNEL_ID', 0))
POST_INTERVAL_MIN = 5
POST_INTERVAL_MAX = 10
CACHE_SIZE = 1000
COGS_DIR = "cogs"  # Cog directory path

# Custom reaction emojis
UPVOTE = "<:49noice:1390641356397088919>"
DOWNVOTE = "<a:55emoji_76:1390673781743423540>"

# Meme of the day tracking
meme_scores = {}  # msg_id: {"score": int, "embed": Embed, "url": str}
meme_of_the_day = {"score": 0, "post_id": None, "embed": None}

# Reddit client (lazy init)
reddit = None

async def init_reddit():
    """Initialize asyncpraw after loop is alive"""
    global reddit
    reddit = asyncpraw.Reddit(
        client_id=os.environ['REDDIT_CLIENT_ID'],
        client_secret=os.environ['REDDIT_CLIENT_SECRET'],
        user_agent=os.environ['REDDIT_USER_AGENT'],
        timeout=15
    )
    reddit.read_only = True
    logger.info("✅ Reddit client initialized in read-only mode")

# ==== Bot Setup ====
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True  # Needed for user info in cogs
intents.guilds = True   # Needed for server info in cogs

bot = commands.Bot(
    command_prefix=["s!", "senpai "], 
    intents=intents, 
    help_command=None
)

# ==== Shared Configuration ====
class BotConfig:
    """Central configuration accessible to all cogs"""
    def __init__(self):
        self.meme_channel_id = MEME_CHANNEL_ID
        self.post_intervals = (POST_INTERVAL_MIN, POST_INTERVAL_MAX)
        self.upvote_emoji = UPVOTE
        self.downvote_emoji = DOWNVOTE
        self.subreddits = ALL_MEMES
        self.cache_file = "cache.json"

# Attach to bot instance
bot.shared_config = BotConfig()

# ==== Data Management ====
CACHE_FILE = bot.shared_config.cache_file
posted_ids = set()
posted_queue = deque(maxlen=CACHE_SIZE)

def load_cache():
    global posted_ids, posted_queue
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                cache_data = json.load(f)
                if isinstance(cache_data, list):
                    posted_queue = deque(cache_data, maxlen=CACHE_SIZE)
                    posted_ids = set(cache_data)
                    logger.info(f"Loaded {len(posted_ids)} cached post IDs")
    except Exception as e:
        logger.error(f"Cache load error: {e}")

def save_cache():
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(list(posted_queue), f)
    except Exception as e:
        logger.error(f"Cache save error: {e}")

# ==== Core Functions ====
async def fetch_random_meme(target):
    try:
        max_attempts = 5
        for attempt in range(max_attempts):
            subreddit_name = random.choice(ALL_MEMES)
            logger.info(f"Attempt {attempt+1}: Fetching from r/{subreddit_name}")
            subreddit = await reddit.subreddit(subreddit_name)
            posts = []
            
            async for post in subreddit.hot(limit=100):
                if (post.stickied or not post.url or post.id in posted_ids):
                    continue
                if hasattr(target, 'is_nsfw') and not target.is_nsfw() and post.over_18:
                    continue
                
                clean_url = post.url.split('?')[0]
                if any(clean_url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif")):
                    posts.append(post)
                    if len(posts) >= 15:
                        break
            
            if posts:
                post = random.choice(posts)
                if len(posted_queue) == CACHE_SIZE:
                    oldest_id = posted_queue.popleft()
                    posted_ids.remove(oldest_id)
                    
                posted_queue.append(post.id)
                posted_ids.add(post.id)
                save_cache()
                
                return post
        
        logger.warning("No suitable memes found after multiple attempts")
        return None
        
    except Exception as e:
        logger.error(f"Fetch error: {e}", exc_info=True)
        return None

def make_embed(post):
    embed = discord.Embed(
        title=post.title[:250],
        color=random.randint(0, 0xFFFFFF)
    )

    if post.url.endswith(".gifv"):
        embed.set_image(url=post.url.replace(".gifv", ".gif"))
    else:
        embed.set_image(url=post.url)

    embed.set_footer(
        text=f"From r/{post.subreddit} | React below to vote ⬆⬇"
    )
    return embed

async def post_meme(interaction: discord.Interaction = None, ctx: commands.Context = None):
    try:
        # Determine target channel
        if interaction:
            target_channel = interaction.channel
        elif ctx:
            target_channel = ctx.channel
        else:
            target_channel = bot.get_channel(MEME_CHANNEL_ID)
        
        if not target_channel:
            logger.error("Meme channel not found!")
            return False

        post = await fetch_random_meme(target_channel)
        if post:
            embed = make_embed(post)
            
            # Send to appropriate context
            if interaction:
                await interaction.response.send_message(embed=embed)
                msg = await interaction.original_response()
            elif ctx:
                msg = await ctx.send(embed=embed)
            else:
                msg = await target_channel.send(embed=embed)
                
            # Add reactions
            await msg.add_reaction(UPVOTE)
            await msg.add_reaction(DOWNVOTE)
            
            # Track meme
            meme_scores[msg.id] = {"score": 0, "embed": embed, "url": post.url}
            logger.info(f"Posted: r/{post.subreddit} - {post.title[:50]}...")
            return True
        return False
    except Exception as e:
        logger.error(f"Posting failed: {e}", exc_info=True)
        return False

# ==== Scheduler Tasks ====
@tasks.loop(minutes=1.0)
async def meme_scheduler():
    if not hasattr(bot, "next_post_minutes"):
        bot.next_post_minutes = random.uniform(POST_INTERVAL_MIN, POST_INTERVAL_MAX)
        bot.last_post_time = datetime.utcnow()

    elapsed = (datetime.utcnow() - bot.last_post_time).total_seconds() / 60
    if elapsed >= bot.next_post_minutes and not getattr(bot, "paused", False):
        success = await post_meme()  # No context for scheduler
        if success:
            bot.last_post_time = datetime.utcnow()
            bot.next_post_minutes = random.uniform(POST_INTERVAL_MIN, POST_INTERVAL_MAX)
        else:
            bot.next_post_minutes = random.uniform(1, 3)

@tasks.loop(hours=24)
async def reset_meme_of_the_day():
    global meme_of_the_day
    meme_of_the_day = {"score": 0, "post_id": None, "embed": None}
    meme_scores.clear()

# ==== Slash Commands ====
@bot.tree.command(name="meme", description="Get a random meme")
@app_commands.checks.cooldown(1, 30.0)
async def slash_meme(interaction: discord.Interaction):
    await post_meme(interaction=interaction)

@bot.tree.command(name="bestmeme", description="Show today's highest-rated meme")
async def slash_bestmeme(interaction: discord.Interaction):
    if meme_of_the_day["embed"]:
        await interaction.response.send_message(
            f"🏆 Meme of the Day (Score: {meme_of_the_day['score']})",
            embed=meme_of_the_day["embed"]
        )
    else:
        await interaction.response.send_message("😔 No meme of the day yet.")

@bot.tree.command(name="stats", description="Show bot statistics")
async def slash_stats(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Meme Bot Stats", color=0x00FFAA)
    if hasattr(bot, "last_post_time") and hasattr(bot, "next_post_minutes"):
        next_post = bot.last_post_time + timedelta(minutes=bot.next_post_minutes)
        mins_left = max(0, int((next_post - datetime.utcnow()).total_seconds() / 60))
        embed.add_field(name="Next Auto Post", value=f"In {mins_left} minutes", inline=False)
    embed.add_field(name="Uptime", value=str(datetime.utcnow() - bot.start_time).split(".")[0], inline=False)
    embed.add_field(name="Status", value="Paused ⏸️" if getattr(bot, "paused", False) else "Running ▶️", inline=False)
    
    # Show cog stats
    cog_count = len(bot.cogs)
    cog_names = ", ".join(bot.cogs.keys()) if cog_count > 0 else "None"
    embed.add_field(name="Loaded Cogs", value=f"{cog_count} cogs: {cog_names}", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="pause", description="Pause auto-posting (Admin only)")
@app_commands.checks.has_permissions(manage_guild=True)
async def slash_pause(interaction: discord.Interaction):
    bot.paused = True
    await interaction.response.send_message("⏸ Auto-posting paused.")

@bot.tree.command(name="resume", description="Resume auto-posting (Admin only)")
@app_commands.checks.has_permissions(manage_guild=True)
async def slash_resume(interaction: discord.Interaction):
    bot.paused = False
    await interaction.response.send_message("▶ Auto-posting resumed.")

subreddits_group = app_commands.Group(name="subreddits", description="Manage subreddit list")

@subreddits_group.command(name="add", description="Add a subreddit to the list (Admin only)")
@app_commands.describe(subreddit="Subreddit name (without r/)")
@app_commands.checks.has_permissions(manage_guild=True)
async def addsub(interaction: discord.Interaction, subreddit: str):
    sub = subreddit.lower().strip()
    if sub in ALL_MEMES:
        await interaction.response.send_message(f"❌ r/{sub} is already in the list.", ephemeral=True)
        return
        
    ALL_MEMES.append(sub)
    with open(SUB_FILE, "w") as f:
        json.dump(ALL_MEMES, f, indent=2)
    await interaction.response.send_message(f"✅ Added r/{sub} to the list.", ephemeral=True)

@subreddits_group.command(name="remove", description="Remove a subreddit from the list (Admin only)")
@app_commands.describe(subreddit="Subreddit name (without r/)")
@app_commands.checks.has_permissions(manage_guild=True)
async def removesub(interaction: discord.Interaction, subreddit: str):
    sub = subreddit.lower().strip()
    if sub not in ALL_MEMES:
        await interaction.response.send_message(f"❌ r/{sub} not found in the list.", ephemeral=True)
        return
        
    ALL_MEMES.remove(sub)
    with open(SUB_FILE, "w") as f:
        json.dump(ALL_MEMES, f, indent=2)
    await interaction.response.send_message(f"✅ Removed r/{sub} from the list.", ephemeral=True)

@subreddits_group.command(name="list", description="Show current subreddit list")
async def listsubs(interaction: discord.Interaction):
    subs = "\n".join([f"• r/{sub}" for sub in ALL_MEMES])
    embed = discord.Embed(
        title=f"Subreddits ({len(ALL_MEMES)})",
        description=subs,
        color=0x3498DB
    )
    await interaction.response.send_message(embed=embed)

# Add group to command tree
bot.tree.add_command(subreddits_group)

# ==== Cog Management ====
def setup_cog_directory():
    """Ensure cog directory exists with necessary files"""
    os.makedirs(COGS_DIR, exist_ok=True)
    
    # Create __init__.py if missing
    init_file = os.path.join(COGS_DIR, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("# Cog package initializer\n")
    
    logger.info(f"Cog directory setup: {COGS_DIR}")

async def load_all_cogs():
    """Dynamically load all cogs in directory"""
    loaded_cogs = []
    for filename in os.listdir(COGS_DIR):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog_name = filename[:-3]  # Remove .py extension
            try:
                await bot.load_extension(f"{COGS_DIR}.{cog_name}")
                loaded_cogs.append(cog_name)
                logger.info(f"✅ Loaded cog: {cog_name}")
            except Exception as e:
                logger.error(f"❌ Failed to load cog '{cog_name}': {str(e)}")
    return loaded_cogs

# ==== Events ====
@bot.event
async def on_ready():
    global reddit
    bot.start_time = datetime.utcnow()
    bot.paused = False
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

    if reddit is None:
        await init_reddit()
    load_cache()
    
    # Setup and load cogs
    setup_cog_directory()
    loaded_cogs = await load_all_cogs()
    logger.info(f"Loaded {len(loaded_cogs)} cogs: {', '.join(loaded_cogs)}")
    
    # Sync slash commands globally
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands")
    except Exception as e:
        logger.error(f"Command sync error: {e}")

    # Start background tasks
    if not meme_scheduler.is_running():
        meme_scheduler.start()
    if not reset_meme_of_the_day.is_running():
        reset_meme_of_the_day.start()
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name=f"memes & {len(bot.cogs)} cogs"
        )
    )

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
        
    msg_id = reaction.message.id
    if msg_id not in meme_scores:
        return
        
    emoji = str(reaction.emoji)
    if emoji == UPVOTE:
        meme_scores[msg_id]["score"] += 1
    elif emoji == DOWNVOTE:
        meme_scores[msg_id]["score"] -= 1
        
    # Update meme of the day
    current_score = meme_scores[msg_id]["score"]
    if current_score > meme_of_the_day["score"]:
        meme_of_the_day["score"] = current_score
        meme_of_the_day["post_id"] = msg_id
        meme_of_the_day["embed"] = meme_scores[msg_id]["embed"]

@bot.event
async def on_reaction_remove(reaction, user):
    await on_reaction_add(reaction, user)  # Same logic

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Cooldown active! Try again in {error.retry_after:.0f} seconds.")
    elif isinstance(error, commands.ExtensionError):
        await ctx.send(f"⚠️ Cog error: {error.original}")
    else:
        logger.error(f"Command error: {error}", exc_info=True)

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author.bot:
        return

    # Only watch the memes channel
    if message.channel.id == MEME_CHANNEL_ID and message.attachments:
        # Only handle media files (images/videos)
        for attachment in message.attachments:
            if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mov", ".webm")):
                
                # Repost the media as the bot
                embed = discord.Embed(
                    description=f"Posted by {message.author.mention}",
                    color=random.randint(0, 0xFFFFFF),
                    timestamp=datetime.utcnow()
                )
                embed.set_image(url=attachment.url)
                repost = await message.channel.send(embed=embed)

                # React with upvote/downvote like auto memes
                await repost.add_reaction(UPVOTE)
                await repost.add_reaction(DOWNVOTE)

                # Track it in meme_scores
                meme_scores[repost.id] = {"score": 0, "embed": embed, "url": attachment.url}

                # Delete the original message
                await message.delete()
                break  # Only repost first media if multiple

    # Important: Process normal commands after our event
    await bot.process_commands(message)

# ==== Main Entry Point ====
async def main():
    """Async main function to start the bot"""
    async with bot:
        await bot.start(os.environ['discordkey'])

# ==== Start Bot ====
if __name__ == "__main__":
    keep_alive()
    logger.info("Webserver started for keep-alive")
    asyncio.run(main())
