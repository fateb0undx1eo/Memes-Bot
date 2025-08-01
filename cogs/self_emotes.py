import discord
from discord.ext import commands
import aiohttp
import random
import logging

logger = logging.getLogger('MemeBot.SelfEmotes')

class SelfEmotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Supported self-emotes with aliases
        self.emote_types = {
            "blush": ["blush", "shy", "embarrassed"],
            "smile": ["smile", "grin", "happy"],
            "dance": ["dance", "dancing", "party"],
            "happy": ["happy", "joy", "excited"],
            "cry": ["cry", "crying", "sad", "tears"],
            "wink": ["wink", "flirt", "tease"]
        }
        self.api_url = "https://api.waifu.pics"

    async def fetch_waifu_gif(self, action: str, nsfw: bool = False):
        """Fetch a waifu GIF URL from waifu.pics with proper error handling"""
        try:
            category = "nsfw" if nsfw else "sfw"
            url = f"{self.api_url}/{category}/{action}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("url")
                    logger.warning(f"Waifu API error: Status {resp.status}")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching GIF: {str(e)}")
        except asyncio.TimeoutError:
            logger.warning("Waifu API request timed out")
        return None

    def get_primary_command(self, command_name):
        """Find the primary command from aliases"""
        for primary, aliases in self.emote_types.items():
            if command_name in aliases:
                return primary
        return command_name

    @commands.command(name="blush", aliases=["shy", "embarrassed"])
    async def blush(self, ctx):
        await self.handle_emote(ctx, "blush")
    
    @commands.command(name="smile", aliases=["grin", "happy"])
    async def smile(self, ctx):
        await self.handle_emote(ctx, "smile")
    
    @commands.command(name="dance", aliases=["dancing", "party"])
    async def dance(self, ctx):
        await self.handle_emote(ctx, "dance")
    
    @commands.command(name="happy", aliases=["joy", "excited"])
    async def happy(self, ctx):
        await self.handle_emote(ctx, "happy")
    
    @commands.command(name="cry", aliases=["crying", "sad", "tears"])
    async def cry(self, ctx):
        await self.handle_emote(ctx, "cry")
    
    @commands.command(name="wink", aliases=["flirt", "tease"])
    async def wink(self, ctx):
        await self.handle_emote(ctx, "wink")

    async def handle_emote(self, ctx, emote_type):
        """Handle all emote commands with cooldown and error handling"""
        try:
            # Get the primary command name for display
            primary_name = self.get_primary_command(ctx.command.name)
            
            gif_url = await self.fetch_waifu_gif(
                emote_type, 
                nsfw=ctx.channel.is_nsfw() if hasattr(ctx.channel, 'is_nsfw') else False
            )
            
            if gif_url:
                embed = discord.Embed(
                    description=f"{ctx.author.mention} is **{primary_name}**!",
                    color=random.randint(0, 0xFFFFFF)
                )
                embed.set_image(url=gif_url)
                await ctx.send(embed=embed)
            else:
                await ctx.send("😢 Couldn't fetch a GIF right now. Try again later!")
                
        except Exception as e:
            logger.error(f"Error in {emote_type} command: {str(e)}")
            await ctx.send("⚠️ Something went wrong with that command!")

async def setup(bot):
    await bot.add_cog(SelfEmotes(bot))
