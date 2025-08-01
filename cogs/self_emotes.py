import discord
from discord.ext import commands
import aiohttp
import random
import logging

logger = logging.getLogger('MemeBot.SelfEmotes')

class SelfEmotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://api.waifu.pics"

        # emote name -> aliases
        self.emote_types = {
            "blush": ["shy", "embarrassed"],
            "smile": ["grin", "happy"],
            "dance": ["dancing", "party"],
            "happy": ["joy", "excited"],
            "cry": ["crying", "sad", "tears"],
            "wink": ["flirt", "tease"]
        }

        # Dynamically add commands to the bot
        for emote, aliases in self.emote_types.items():
            async def emote_func(ctx, emote_type=emote):
                gif_url = await self.fetch_waifu_gif(
                    emote_type, 
                    nsfw=getattr(ctx.channel, 'is_nsfw', lambda: False)()
                )
                if gif_url:
                    embed = discord.Embed(
                        description=f"{ctx.author.mention} is **{emote_type}**!",
                        color=random.randint(0, 0xFFFFFF)
                    )
                    embed.set_image(url=gif_url)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("😢 Couldn't fetch a GIF right now. Try again later!")

            emote_func.__name__ = f"cmd_{emote}"  # give it a unique name

            self.bot.add_command(commands.Command(emote_func, name=emote, aliases=aliases))

    async def fetch_waifu_gif(self, action: str, nsfw: bool = False):
        """Fetch a waifu GIF URL from waifu.pics"""
        category = "nsfw" if nsfw else "sfw"
        url = f"{self.api_url}/{category}/{action}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("url")
                    logger.warning(f"Waifu API error: Status {resp.status}")
        except Exception as e:
            logger.error(f"GIF fetch error: {e}")
        return None

async def setup(bot):
    await bot.add_cog(SelfEmotes(bot))
