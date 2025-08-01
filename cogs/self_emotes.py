import discord
from discord.ext import commands
import aiohttp
import random
import asyncio
import logging
from typing import Literal, Optional

# Configure logging
logger = logging.getLogger(__name__)

class SelfEmotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()  # Persistent session for efficiency
        
        # Unified emote list with better API mapping
        self.emote_mapping = {
            "smile": "smile",
            "dance": "dance",
            "wink": "wink",
            "blush": "blush",
            "cry": "cry",
            "happy": "happy",
            "thinking": "thinking",
            "wave": "wave",
            "laugh": "laugh",
            "shrug": "shrug",
            "pout": "pout",
            "sleep": "sleep"
        }
        
        # API base for nekos.best
        self.api_base = "https://nekos.best/api/v2"
        
        # Improved fallback GIFs with more variety
        self.fallback_gifs = {
            "smile": "https://media.tenor.com/G1i1ny-H9HIAAAAC/anime-smile.gif",
            "dance": "https://media.tenor.com/QvC0f3dGh2wAAAAd/anime-dance.gif",
            "wink": "https://media.tenor.com/5B5x7wB4F5wAAAAC/anime-wink.gif",
            "blush": "https://media.tenor.com/q4M8p0QQUCkAAAAC/anime-blush.gif",
            "cry": "https://media.tenor.com/3iN2Q4e0dQkAAAAC/anime-cry-sad.gif",
            "happy": "https://media.tenor.com/xG5J7lVL3YAAAAAC/happy-anime.gif",
            "thinking": "https://media.tenor.com/6gCqKJwL0cUAAAAC/anime-thinking.gif",
            "wave": "https://media.tenor.com/8vVh2e8J0VkAAAAC/anime-wave.gif",
            "laugh": "https://media.tenor.com/9BdRgqR6d0wAAAAC/laugh-anime.gif",
            "shrug": "https://media.tenor.com/6ZRgF4VbD8cAAAAC/anime-shrug.gif",
            "pout": "https://media.tenor.com/9vUQ7q7D2r8AAAAC/pout-anime.gif",
            "sleep": "https://media.tenor.com/6JhxqRzwYjIAAAAC/anime-sleeping.gif"
        }

    async def cog_unload(self):
        """Clean up the aiohttp session when cog unloads"""
        await self.session.close()

    async def fetch_emote_gif(self, action: str) -> Optional[str]:
        """Fetch GIF from nekos.best API with proper error handling"""
        # Validate action
        if action not in self.emote_mapping:
            logger.warning(f"Invalid emote action requested: {action}")
            return None

        url = f"{self.api_base}/{self.emote_mapping[action]}?amount=1"
        
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                # Handle rate limits
                if resp.status == 429:
                    retry_after = int(resp.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited. Retrying after {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return await self.fetch_emote_gif(action)
                
                if resp.status != 200:
                    logger.error(f"API returned {resp.status} for {action}")
                    return self.fallback_gifs.get(action)
                
                data = await resp.json()
                return data["results"][0]["url"] if data.get("results") else None
                
        except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, IndexError) as e:
            logger.error(f"Failed to fetch {action} GIF: {type(e).__name__} - {e}")
            return self.fallback_gifs.get(action)

    @commands.command(
        name="emote",
        description="Express yourself with anime emotes!",
        aliases=list(emote_mapping.keys())
    )
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def self_emote(self, ctx: commands.Context):
        """Handle all emote commands through a single function"""
        cmd = ctx.invoked_with  # Get the specific alias used
        action = self.emote_mapping.get(cmd, "smile")  # Default to smile
        
        try:
            gif_url = await self.fetch_emote_gif(cmd)
            if not gif_url:
                gif_url = self.fallback_gifs.get(cmd, random.choice(list(self.fallback_gifs.values())))
            
            embed = discord.Embed(
                description=f"{ctx.author.mention} is **{cmd}ing**!",
                color=random.randint(0, 0xFFFFFF)
            )
            embed.set_image(url=gif_url)
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.exception(f"Unexpected error in {cmd} command")
            await ctx.send("⚠️ Something went wrong. Try again later!", delete_after=10)

async def setup(bot):
    await bot.add_cog(SelfEmotes(bot))
