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

# ==== Reddit Client ====
reddit = asyncpraw.Reddit(
    client_id=os.environ['REDDIT_CLIENT_ID'],
    client_secret=os.environ['REDDIT_CLIENT_SECRET'],
    user_agent=os.environ['REDDIT_USER_AGENT'],
    timeout=15
)

# ==== Bot Setup ====
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

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
    """Atomically save subreddit list to prevent corruption."""
    temp_file = SUB_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(ALL_MEMES, f, indent=2)
    shutil.move(temp_file, SUB_FILE)

# ==== Core Functions ====
async def fetch_random_meme(ctx=None):
    try:
        subreddit_name = random.choice(ALL_MEMES)
        logger.info(f"Fetching from r/{subreddit_name}")
        subreddit = await reddit.subreddit(subreddit_name)
        posts = []
        
        try:
            async for post in subreddit.hot(limit=150):
                if (post.stickied or 
                    not post.url or 
                    post.id in posted_ids or
                    post.url.endswith(".mp4")):
                    continue
                
                # Skip NSFW in non-NSFW channels
                if ctx and not ctx.channel.is_nsfw() and post.over_18:
                    continue
                
                if any(post.url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".gifv")):
                    posts.append(post)
                    if len(posts) >= 25:
                        break
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching from r/{subreddit_name}")
        
        if not posts:
            logger.warning(f"No new memes in r/{subreddit_name}")
            return None
            
        post = random.choice(posts)
        
        # Update cache
        if len(posted_queue) == CACHE_SIZE:
            oldest_id = posted_queue.popleft()
            posted_ids.remove(oldest_id)
            
        posted_queue.append(post.id)
        posted_ids.add(post.id)
        save_cache()
        
        return post
        
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
        channel = bot.get_channel(MEME_CHANNEL_ID)
        if not channel:
            logger.error("Meme channel not found!")
            return False

        class DummyContext:
            channel = channel
        
        post = await fetch_random_meme(DummyContext())
        if post:
            embed = make_embed(post)
            msg = await channel.send(embed=embed)
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
    if not hasattr(bot, "next_post_minutes"):
        bot.next_post_minutes = random.uniform(POST_INTERVAL_MIN, POST_INTERVAL_MAX)
        bot.last_post_time = datetime.utcnow()
        logger.info(f"Initialized scheduler. First post in {bot.next_post_minutes:.1f} minutes")

    elapsed = (datetime.utcnow() - bot.last_post_time).total_seconds() / 60
    
    if elapsed >= bot.next_post_minutes and not getattr(bot, "paused", False):
        success = await post_meme()
        
        if success:
            bot.last_post_time = datetime.utcnow()
            bot.next_post_minutes = random.uniform(POST_INTERVAL_MIN, POST_INTERVAL_MAX)
            logger.info(f"Next post scheduled in {bot.next_post_minutes:.1f} minutes")
        else:
            bot.next_post_minutes = random.uniform(1, 3)
            logger.warning(f"Post failed. Retrying in {bot.next_post_minutes:.1f} minutes")

@tasks.loop(hours=24)
async def reset_meme_of_the_day():
    global meme_of_the_day
    meme_of_the_day = {"score": 0, "post_id": None, "embed": None}
    meme_scores.clear()
    logger.info("Meme of the Day has been reset!")

# ==== Reaction Events with Lock ====
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

            logger.info(f"Vote added. MsgID: {msg.id}, Score: {meme_scores[msg.id]['score']}")

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

            logger.info(f"Vote removed. MsgID: {msg.id}, Score: {meme_scores[msg.id]['score']}")

# ==== Commands ====
@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def meme(ctx):
    async with ctx.typing():
        post = await fetch_random_meme(ctx)
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
async def invite(ctx):
    perms = discord.Permissions(
        send_messages=True,
        embed_links=True,
        read_message_history=True,
        add_reactions=True,
        manage_messages=True
    )
    await ctx.send(f"🔗 Invite me:\n{discord.utils.oauth_url(bot.user.id, permissions=perms)}")

@bot.command()
async def stats(ctx):
    embed = discord.Embed(
        title="🤖 Meme Bot Stats",
        color=0x00FFAA,
        description=f"Tracking {len(posted_ids)} posts across {len(ALL_MEMES)} subreddits"
    )
    
    if hasattr(bot, "last_post_time") and hasattr(bot, "next_post_minutes"):
        next_post = bot.last_post_time + timedelta(minutes=bot.next_post_minutes)
        mins_left = max(0, int((next_post - datetime.utcnow()).total_seconds() / 60))
        embed.add_field(name="Next Auto Post", value=f"In {mins_left} minutes", inline=False)
    
    embed.add_field(name="Subreddits", value="\n".join([f"• r/{sub}" for sub in ALL_MEMES]), inline=False)
    
    if hasattr(bot, "start_time"):
        uptime = datetime.utcnow() - bot.start_time
        embed.add_field(name="Uptime", value=str(uptime).split(".")[0], inline=False)
        
    await ctx.send(embed=embed)

# Owner-only admin commands
@bot.command()
@commands.is_owner()
async def subreddits(ctx):
    await ctx.send(f"📋 Monitored subreddits:\n{', '.join([f'r/{s}' for s in ALL_MEMES])}")

@bot.command()
@commands.is_owner()
async def addsub(ctx, subreddit):
    subreddit = subreddit.strip().lower()
    if subreddit not in ALL_MEMES:
        ALL_MEMES.append(subreddit)
        save_subreddits()
        await ctx.send(f"✅ Added r/{subreddit}")
    else:
        await ctx.send("⚠ Already in the list!")

@bot.command()
@commands.is_owner()
async def removesub(ctx, subreddit):
    subreddit = subreddit.strip().lower()
    if subreddit in ALL_MEMES:
        ALL_MEMES.remove(subreddit)
        save_subreddits()
        await ctx.send(f"✅ Removed r/{subreddit}")
    else:
        await ctx.send("⚠ Not found!")

@bot.command()
@commands.is_owner()
async def reschedule(ctx):
    if hasattr(bot, "next_post_minutes"):
        bot.next_post_minutes = 0
        await ctx.send("⏩ Next post will be attempted within 1 minute")
    else:
        await ctx.send("⚠ Scheduler not initialized yet")

@bot.command()
@commands.is_owner()
async def pause(ctx):
    bot.paused = True
    await ctx.send("⏸ Auto-posting paused.")

@bot.command()
@commands.is_owner()
async def resume(ctx):
    bot.paused = False
    await ctx.send("▶ Auto-posting resumed.")

# ==== Events ====
@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    bot.start_time = datetime.utcnow()
    load_cache()
    
    if not meme_scheduler.is_running():
        meme_scheduler.start()
        logger.info("Started meme scheduler")
    
    if not reset_meme_of_the_day.is_running():
        reset_meme_of_the_day.start()
        logger.info("Started Meme of the Day reset scheduler")
    
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
    elif isinstance(error, commands.NotOwner):
        await ctx.send("🔒 This command is for bot owners only!")
    else:
        logger.error(f"Command error: {error}", exc_info=True)

# ==== Start Bot ====
if _name_ == "_main_":
    try:
        keep_alive()  # webserver keep-alive
        logger.info("Webserver started for keep-alive")
        
        token = os.environ['discordkey']
        bot.run(token)
    except KeyError:
        logger.error("Missing 'discordkey' environment variable")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(reddit.close())
        logger.info("Reddit client closed")
        loop.close()
