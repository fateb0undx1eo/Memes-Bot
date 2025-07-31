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
from discord.ext.commands import has_permissions
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
    global reddit
    reddit = asyncpraw.Reddit(
        client_id=os.environ['REDDIT_CLIENT_ID'],
        client_secret=os.environ['REDDIT_CLIENT_SECRET'],
        user_agent=os.environ['REDDIT_USER_AGENT'],
        timeout=15
    )
    await reddit.read_only()
    logger.info("✅ Reddit client initialized")

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

def save_subreddits():
    temp_file = SUB_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(ALL_MEMES, f, indent=2)
    shutil.move(temp_file, SUB_FILE)

# ==== Core Functions ====
async def fetch_random_meme(target):
    try:
        max_attempts = 5
        for attempt in range(max_attempts):
            subreddit_name = random.choice(ALL_MEMES)
            logger.info(f"Attempt {attempt+1}: Fetching from r/{subreddit_name}")
            subreddit = await reddit.subreddit(subreddit_name)
            posts = []
            
            try:
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
            
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching r/{subreddit_name}")
                continue
            
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
    if post.url.endswith(".gifv"):
        embed.set_image(url=post.url.replace(".gifv", ".gif"))
    else:
        embed.set_image(url=post.url)
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
        logger.warning("Post failed: No suitable memes found")
        return False
    except Exception as e:
        logger.error(f"Posting failed: {e}", exc_info=True)
        return False

# ==== Scheduler Tasks ====
@tasks.loop(minutes=1.0)
async def meme_scheduler():
    """Check every minute if it's time to post a meme."""
    if not hasattr(bot, "last_post_time"):
        bot.last_post_time = datetime.utcnow() - timedelta(minutes=POST_INTERVAL_MAX)
    if not hasattr(bot, "next_post_minutes"):
        bot.next_post_minutes = random.uniform(POST_INTERVAL_MIN, POST_INTERVAL_MAX)

    elapsed = (datetime.utcnow() - bot.last_post_time).total_seconds() / 60

    if elapsed >= bot.next_post_minutes and not getattr(bot, "paused", False):
        success = await post_meme()
        bot.last_post_time = datetime.utcnow()

        if success:
            bot.next_post_minutes = random.uniform(POST_INTERVAL_MIN, POST_INTERVAL_MAX)
            logger.info(f"✅ Meme posted! Next in {bot.next_post_minutes:.1f} minutes")
        else:
            bot.next_post_minutes = 1
            logger.warning("⚠ No meme found. Will retry in 1 minute.")

@tasks.loop(hours=24)
async def reset_meme_of_the_day():
    global meme_of_the_day
    meme_of_the_day = {"score": 0, "post_id": None, "embed": None}
    meme_scores.clear()
    logger.info("Meme of the Day has been reset!")

# ==== Reaction Events ====
score_lock = asyncio.Lock()

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    async with score_lock:
        msg = reaction.message
        if msg.id in meme_scores:
            if str(reaction.emoji) == UPVOTE:
                meme_scores[msg.id]["score"] += 1
            elif str(reaction.emoji) == DOWNVOTE:
                meme_scores[msg.id]["score"] -= 1

            if meme_scores[msg.id]["score"] > meme_of_the_day["score"]:
                meme_of_the_day.update({
                    "score": meme_scores[msg.id]["score"],
                    "post_id": msg.id,
                    "embed": meme_scores[msg.id]["embed"]
                })

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return
    async with score_lock:
        msg = reaction.message
        if msg.id in meme_scores:
            if str(reaction.emoji) == UPVOTE:
                meme_scores[msg.id]["score"] -= 1
            elif str(reaction.emoji) == DOWNVOTE:
                meme_scores[msg.id]["score"] += 1

# ==== Commands ====
@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def meme(ctx):
    async with ctx.typing():
        post = await fetch_random_meme(ctx.channel)
        if post:
            embed = make_embed(post)
            msg = await ctx.send(embed=embed)
            await msg.add_reaction(UPVOTE)
            await msg.add_reaction(DOWNVOTE)
            meme_scores[msg.id] = {"score": 0, "embed": embed, "url": post.url}
        else:
            await ctx.send("🚫 Couldn't find a fresh meme! Try again later.")

@bot.command()
async def bestmeme(ctx):
    if meme_of_the_day["embed"]:
        await ctx.send(f"🏆 Meme of the Day (Score: {meme_of_the_day['score']})", embed=meme_of_the_day["embed"])
    else:
        await ctx.send("😔 No meme of the day yet.")

@bot.command()
async def stats(ctx):
    if not hasattr(bot, "last_post_time"):
        bot.last_post_time = datetime.utcnow()
    if not hasattr(bot, "next_post_minutes"):
        bot.next_post_minutes = POST_INTERVAL_MIN

    embed = discord.Embed(
        title="🤖 Meme Bot Stats",
        color=0x00FFAA,
        description=f"Tracking {len(posted_ids)} posts across {len(ALL_MEMES)} subreddits"
    )

    next_post = bot.last_post_time + timedelta(minutes=bot.next_post_minutes)
    mins_left = max(0, int((next_post - datetime.utcnow()).total_seconds() / 60))
    embed.add_field(name="Next Auto Post", value=f"In {mins_left} minutes", inline=False)

    embed.add_field(name="Subreddits", value="\n".join([f"• r/{sub}" for sub in ALL_MEMES]), inline=False)

    if hasattr(bot, "start_time"):
        uptime = datetime.utcnow() - bot.start_time
        embed.add_field(name="Uptime", value=str(uptime).split(".")[0], inline=False)

    await ctx.send(embed=embed)

# ==== Admin Commands ====
@bot.command()
@has_permissions(administrator=True)
async def addsub(ctx, subreddit):
    subreddit = subreddit.strip().lower()
    if subreddit not in ALL_MEMES:
        ALL_MEMES.append(subreddit)
        save_subreddits()
        await ctx.send(f"✅ Added r/{subreddit}")
    else:
        await ctx.send("⚠ Already in the list!")

@bot.command()
@has_permissions(administrator=True)
async def removesub(ctx, subreddit):
    subreddit = subreddit.strip().lower()
    if subreddit in ALL_MEMES:
        ALL_MEMES.remove(subreddit)
        save_subreddits()
        await ctx.send(f"✅ Removed r/{subreddit}")
    else:
        await ctx.send("⚠ Not found!")

@bot.command()
@has_permissions(administrator=True)
async def pause(ctx):
    bot.paused = True
    await ctx.send("⏸ Auto-posting paused.")

@bot.command()
@has_permissions(administrator=True)
async def resume(ctx):
    bot.paused = False
    await ctx.send("▶ Auto-posting resumed.")

@bot.command()
async def invite(ctx):
    perms = discord.Permissions(
        send_messages=True,
        embed_links=True,
        read_message_history=True,
        add_reactions=True,
        manage_messages=True
    )
    await ctx.send(f"🔗 Invite me:\n{discord.utils.oauth_url(bot.user.id, permissions=perms)}")

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
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"for memes in {len(ALL_MEMES)} subs"
        )
    )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Cooldown active! Try again in {error.retry_after:.0f} seconds.")
    else:
        logger.error(f"Command error: {error}", exc_info=True)

# ==== Start Bot ====
if _name_ == "_main_":
    keep_alive()
    logger.info("Webserver started for keep-alive")

    try:
        token = os.environ['discordkey']
        bot.run(token)
    except KeyError:
        logger.error("Missing 'discordkey' environment variable")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
