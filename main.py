import discord
import asyncpraw
import asyncio
import os
import json
import random
import logging
import sys
import traceback
from datetime import datetime, timedelta, timezone
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
os.makedirs("data", exist_ok=True)
os.makedirs("cogs", exist_ok=True)

# Create __init__.py in cogs directory if missing
COGS_DIR = "cogs"
if not os.path.exists(os.path.join(COGS_DIR, "__init__.py")):
    open(os.path.join(COGS_DIR, "__init__.py"), 'a').close()

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

RESPONSES_FILE = "data/responses.json"
if not os.path.exists(RESPONSES_FILE):
    with open(RESPONSES_FILE, "w") as f:
        json.dump({}, f)

MEME_CHANNEL_ID = int(os.environ.get('MEMES_CHANNEL_ID', 0))
POST_INTERVAL_MIN = 5
POST_INTERVAL_MAX = 10
CACHE_SIZE = 1000

UPVOTE = "<:49noice:1390641356397088919>"
DOWNVOTE = "<a:55emoji_76:1390673781743423540>"

meme_scores = {}
meme_of_the_day = {"score": 0, "post_id": None, "embed": None}

reddit = None

async def init_reddit():
    global reddit
    reddit = asyncpraw.Reddit(
        client_id=os.environ['REDDIT_CLIENT_ID'],
        client_secret=os.environ['REDDIT_CLIENT_SECRET'],
        user_agent=os.environ['REDDIT_USER_AGENT'],
        timeout=15
    )
    reddit.read_only = True
    logger.info("✅ Reddit client initialized")

# ==== Bot Setup ====
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix=["s!", "senpai "],
    intents=intents,
    help_command=None
)

# ==== Cache ====
CACHE_FILE = "cache.json"
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

# ==== Meme Functions ====
async def fetch_random_meme(target):
    try:
        for _ in range(5):
            subreddit_name = random.choice(ALL_MEMES)
            subreddit = await reddit.subreddit(subreddit_name)
            posts = []

            async for post in subreddit.hot(limit=100):
                if post.stickied or not post.url or post.id in posted_ids:
                    continue
                if hasattr(target, 'is_nsfw') and not target.is_nsfw() and post.over_18:
                    continue

                clean_url = post.url.split('?')[0]
                if clean_url.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
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

        logger.warning("No suitable memes found.")
        return None

    except Exception as e:
        logger.error(f"Fetch error: {e}", exc_info=True)
        return None

def make_embed(post):
    embed = discord.Embed(
        title=post.title[:250],
        color=random.randint(0, 0xFFFFFF)
    )
    embed.set_image(url=post.url.replace(".gifv", ".gif") if post.url.endswith(".gifv") else post.url)
    embed.set_footer(text=f"From r/{post.subreddit} | React to vote ⬆⬇")
    return embed

async def post_meme(interaction=None, ctx=None):
    target_channel = (
        interaction.channel if interaction else
        ctx.channel if ctx else
        bot.get_channel(MEME_CHANNEL_ID)
    )
    if not target_channel:
        logger.error("No target channel for meme post.")
        return False

    post = await fetch_random_meme(target_channel)
    if not post:
        return False

    embed = make_embed(post)
    msg = None

    if interaction:
        if interaction.response.is_done():
            msg = await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)
            msg = await interaction.original_response()
    elif ctx:
        msg = await ctx.send(embed=embed)
    else:
        msg = await target_channel.send(embed=embed)

    await msg.add_reaction(UPVOTE)
    await msg.add_reaction(DOWNVOTE)

    meme_scores[msg.id] = {"score": 0, "embed": embed, "url": post.url}
    return True

# ==== Scheduler Tasks ====
@tasks.loop(minutes=1.0)
async def meme_scheduler():
    if not hasattr(bot, "next_post_minutes"):
        bot.next_post_minutes = random.uniform(POST_INTERVAL_MIN, POST_INTERVAL_MAX)
        bot.last_post_time = datetime.now(timezone.utc)

    elapsed = (datetime.now(timezone.utc) - bot.last_post_time).total_seconds() / 60
    if elapsed >= bot.next_post_minutes and not getattr(bot, "paused", False):
        success = await post_meme()
        bot.last_post_time = datetime.now(timezone.utc)
        bot.next_post_minutes = random.uniform(POST_INTERVAL_MIN, POST_INTERVAL_MAX if success else 3)

@tasks.loop(hours=24)
async def reset_meme_of_the_day():
    global meme_of_the_day
    meme_of_the_day = {"score": 0, "post_id": None, "embed": None}
    meme_scores.clear()

# ==== Slash Commands ====
@bot.tree.command(name="meme", description="Get a random meme")
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
    await interaction.response.defer()
    embed = discord.Embed(title="🤖 Meme Bot Stats", color=0x00FFAA)
    uptime = datetime.now(timezone.utc) - bot.start_time
    embed.add_field(name="Uptime", value=str(uptime).split(".")[0], inline=False)
    embed.add_field(name="Status", value="Paused ⏸️" if getattr(bot, "paused", False) else "Running ▶️", inline=False)
    embed.add_field(name="Loaded Cogs", value=f"{len(bot.cogs)}: {', '.join(bot.cogs)}", inline=False)
    await interaction.followup.send(embed=embed)

# ==== Cog Loader ====
async def load_all_cogs():
    for filename in os.listdir(COGS_DIR):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog_name = filename[:-3]
            full_path = f"{COGS_DIR}.{cog_name}"
            try:
                await bot.load_extension(full_path)
                logger.info(f"✅ Loaded cog: {cog_name}")
            except Exception as e:
                logger.error(f"❌ Failed to load cog {cog_name}: {e}", exc_info=True)

# ==== Events ====
@bot.event
async def on_ready():
    bot.start_time = datetime.now(timezone.utc)
    bot.paused = False
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

    if reddit is None:
        await init_reddit()
    load_cache()

    # Sync commands only once
    if not hasattr(bot, "synced_commands"):
        try:
            synced = await bot.tree.sync()
            logger.info(f"✅ Synced {len(synced)} slash commands")
            bot.synced_commands = True
        except Exception as e:
            logger.error(f"❌ Command sync error: {e}")

    # Start tasks only once
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
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

# ==== Main ====
async def main():
    # Load cogs before starting bot
    await load_all_cogs()
    async with bot:
        await bot.start(os.environ['DISCORD_TOKEN'])

if __name__ == "__main__":
    keep_alive()
    logger.info("Webserver started for keep-alive")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
