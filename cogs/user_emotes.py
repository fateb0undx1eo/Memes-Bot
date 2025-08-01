import discord
from discord.ext import commands
import aiohttp, random

class SelfEmotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Original API actions for self emotes
        self.self_emotes = {
            "happy_self": "happy",
            "cry_self": "cry",
            "blush_self": "blush",
            "dance_self": "dance",
            "smile_self": "smile"
        }

    async def fetch_waifu_gif(self, action: str, nsfw: bool = False):
        """Fetch GIF URL from waifu.pics API"""
        base = "https://api.waifu.pics"
        category = "nsfw" if nsfw else "sfw"
        url = f"{base}/{category}/{action}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("url")
        return None

    async def send_self_emote(self, ctx: commands.Context, action: str, display: str):
        """Send self emote embed"""
        gif_url = await self.fetch_waifu_gif(action, nsfw=ctx.channel.is_nsfw())
        if gif_url:
            embed = discord.Embed(
                description=f"{ctx.author.mention} is feeling **{display}**!",
                color=random.randint(0, 0xFFFFFF)
            )
            embed.set_image(url=gif_url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚠️ Could not fetch a GIF, try again later.")

    # --- Commands ---
    @commands.command(name="happy_self")
    async def happy_self(self, ctx: commands.Context):
        await self.send_self_emote(ctx, "happy", "happy")

    @commands.command(name="cry_self")
    async def cry_self(self, ctx: commands.Context):
        await self.send_self_emote(ctx, "cry", "sad")

    @commands.command(name="blush_self")
    async def blush_self(self, ctx: commands.Context):
        await self.send_self_emote(ctx, "blush", "shy")

    @commands.command(name="dance_self")
    async def dance_self(self, ctx: commands.Context):
        await self.send_self_emote(ctx, "dance", "dancing")

    @commands.command(name="smile_self")
    async def smile_self(self, ctx: commands.Context):
        await self.send_self_emote(ctx, "smile", "smiling")

async def setup(bot):
    await bot.add_cog(SelfEmotes(bot))
