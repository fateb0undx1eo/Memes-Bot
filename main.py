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
    reddit.read_only = True  # ✅ FIXED
    logger.info("✅ Reddit client initialized in read-only mode")

# ==== Bot Setup ====
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ==== Data Management ====
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
        url=f"https://reddit.com{post.permalink}",
        color=random.randint(0, 0xFFFFFF),
        timestamp=datetime.utcnow()
    )
    embed.set_image(url=post.url if not post.url.endswith(".gifv") else post.url.replace(".gifv", ".gif"))
    embed.set_footer(
        text=f"👍 {post.score} | 💬 {post.num_comments} | r/{post.subreddit}",
        icon_url="https://www.redditstatic.com/desktop2x/img/favicon/favicon-32x32.png"
    )
    return embed

async def post_meme(ctx=None):
    try:
        target_channel = ctx.channel if ctx else bot.get_channel(MEME_CHANNEL_ID)
        if not target_channel:
            logger.error("Meme channel not found!")
            return False

        post = await fetch_random_meme(target_channel)
        if post:
            embed = make_embed(post)
            msg = await target_channel.send(embed=embed)
            await msg.add_reaction(UPVOTE)
            await msg.add_reaction(DOWNVOTE)
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
        success = await post_meme()
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

# ==== Commands ====
@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def meme(ctx):
    await post_meme(ctx)

@bot.command()
async def bestmeme(ctx):
    if meme_of_the_day["embed"]:
        await ctx.send(f"🏆 Meme of the Day (Score: {meme_of_the_day['score']})", embed=meme_of_the_day["embed"])
    else:
        await ctx.send("😔 No meme of the day yet.")

@bot.command()
async def stats(ctx):
    embed = discord.Embed(title="🤖 Meme Bot Stats", color=0x00FFAA)
    if hasattr(bot, "last_post_time") and hasattr(bot, "next_post_minutes"):
        next_post = bot.last_post_time + timedelta(minutes=bot.next_post_minutes)
        mins_left = max(0, int((next_post - datetime.utcnow()).total_seconds() / 60))
        embed.add_field(name="Next Auto Post", value=f"In {mins_left} minutes", inline=False)
    embed.add_field(name="Uptime", value=str(datetime.utcnow() - bot.start_time).split(".")[0], inline=False)
    await ctx.send(embed=embed)

# ==== Events ====
@bot.event
async def on_ready():
    global reddit
    bot.start_time = datetime.utcnow()
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

    if reddit is None:
        await init_reddit()
    load_cache()
    if not meme_scheduler.is_running():
        meme_scheduler.start()
    if not reset_meme_of_the_day.is_running():
        reset_meme_of_the_day.start()
    
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"for memes in {len(ALL_MEMES)} subs")
    )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Cooldown active! Try again in {error.retry_after:.0f} seconds.")
    else:
        logger.error(f"Command error: {error}", exc_info=True)

# ==== Start Bot ====
if __name__ == "__main__":
    keep_alive()
    logger.info("Webserver started for keep-alive")
    bot.run(os.environ['discordkey'])
