import discord
import asyncpraw
import asyncio
import os
import json
import random
import logging
import sys
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
ALL_MEMES = ["memes", "dankmemes", "funny", "me_irl", "animememes", "goodanimemes", "wholesomememes"]
MEME_CHANNEL_ID = int(os.environ.get('MEMES_CHANNEL_ID', 0))
POST_INTERVAL_MIN = 5
POST_INTERVAL_MAX = 10
CACHE_SIZE = 1000

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

# ==== Core Functions ====
async def fetch_random_meme():
    try:
        subreddit_name = random.choice(ALL_MEMES)
        logger.info(f"Fetching from r/{subreddit_name}")
        subreddit = await reddit.subreddit(subreddit_name)
        posts = []
        
        try:
            async for post in subreddit.hot(limit=150):
                if (post.stickied or 
                    post.over_18 or 
                    not post.url or 
                    post.id in posted_ids or
                    post.url.endswith(".mp4")):
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

async def post_meme():
    try:
        channel = bot.get_channel(MEME_CHANNEL_ID)
        if not channel:
            logger.error("Meme channel not found!")
            return False

        post = await fetch_random_meme()
        if post:
            await channel.send(embed=make_embed(post))
            logger.info(f"Posted: r/{post.subreddit} - {post.title[:50]}...")
            return True
        logger.warning("Post failed: No suitable memes found")
        return False
    except Exception as e:
        logger.error(f"Posting failed: {e}", exc_info=True)
        return False

# ==== Scheduler Task ====
@tasks.loop(minutes=1.0)
async def meme_scheduler():
    if not hasattr(bot, "next_post_minutes"):
        bot.next_post_minutes = random.uniform(POST_INTERVAL_MIN, POST_INTERVAL_MAX)
        bot.last_post_time = datetime.utcnow()
        logger.info(f"Initialized scheduler. First post in {bot.next_post_minutes:.1f} minutes")

    elapsed = (datetime.utcnow() - bot.last_post_time).total_seconds() / 60
    
    if elapsed >= bot.next_post_minutes:
        success = await post_meme()
        
        if success:
            bot.last_post_time = datetime.utcnow()
            bot.next_post_minutes = random.uniform(POST_INTERVAL_MIN, POST_INTERVAL_MAX)
            logger.info(f"Next post scheduled in {bot.next_post_minutes:.1f} minutes")
        else:
            bot.next_post_minutes = random.uniform(1, 3)
            logger.warning(f"Post failed. Retrying in {bot.next_post_minutes:.1f} minutes")

# ==== Commands ====
@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def meme(ctx):
    async with ctx.typing():
        post = await fetch_random_meme()
        if post:
            await ctx.send(embed=make_embed(post))
        else:
            await ctx.send("🚫 Couldn't find a fresh meme! Try again later.")

@bot.command()
async def invite(ctx):
    perms = discord.Permissions(
        send_messages=True,
        embed_links=True,
        read_message_history=True,
        add_reactions=True
    )
    await ctx.send(f"🔗 Invite me to your server:\n{discord.utils.oauth_url(bot.user.id, permissions=perms)}")

@bot.command()
async def stats(ctx):
    embed = discord.Embed(
        title="🤖 Meme Bot Stats",
        color=0x00FFAA,
        description=f"Tracking *{len(posted_ids)}* posts across *{len(ALL_MEMES)}* subreddits"
    )
    
    if hasattr(bot, "last_post_time") and hasattr(bot, "next_post_minutes"):
        next_post = bot.last_post_time + timedelta(minutes=bot.next_post_minutes)
        time_left = next_post - datetime.utcnow()
        mins_left = max(0, int(time_left.total_seconds() / 60))
        embed.add_field(name="Next Auto Post", value=f"In {mins_left} minutes", inline=False)
    
    embed.add_field(name="Subreddits", value="\n".join([f"• r/{sub}" for sub in ALL_MEMES]), inline=False)
    
    if hasattr(bot, "start_time"):
        uptime = datetime.utcnow() - bot.start_time
        embed.add_field(name="Uptime", value=str(uptime).split(".")[0], inline=False)
        
    await ctx.send(embed=embed)

@bot.command()
@commands.is_owner()
async def subreddits(ctx):
    await ctx.send(f"📋 Monitored subreddits:\n{', '.join([f'r/{s}' for s in ALL_MEMES])}")

@bot.command()
@commands.is_owner()
async def reschedule(ctx):
    if hasattr(bot, "next_post_minutes"):
        bot.next_post_minutes = 0
        await ctx.send("⏩ Next post will be attempted within 1 minute")
    else:
        await ctx.send("⚠ Scheduler not initialized yet")

# ==== Events ====
@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    bot.start_time = datetime.utcnow()
    load_cache()
    
    if not meme_scheduler.is_running():
        meme_scheduler.start()
        logger.info("Started meme scheduler")
    
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
if __name__ == "__main__":
    try:
        # Start keep-alive webserver
        keep_alive()
        logger.info("Webserver started for keep-alive")
        
        # Get Discord token
        token = os.environ['discordkey']
        
        # Start the bot
        bot.run(token)
    except KeyError:
        logger.error("Missing 'discordkey' environment variable")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # Properly close resources
        loop = asyncio.get_event_loop()
        loop.run_until_complete(reddit.close())
        logger.info("Reddit client closed")
        loop.close()
