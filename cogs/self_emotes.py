import discord
from discord.ext import commands
import aiohttp, random

class SelfEmotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.self_emotes = [
            "happy","awoo","smug","blush","smile","dance","wink","cringe","cry",
            "waifu","neko","shinobu","megumin"
        ]

    async def fetch_waifu_gif(self, action: str, nsfw: bool = False):
        base = "https://api.waifu.pics"
        category = "nsfw" if nsfw else "sfw"
        url = f"{base}/{category}/{action}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("url")
        return None

    @commands.command(name="happy", aliases=[
        "awoo","smug","blush","smile","dance","wink","cringe","cry",
        "waifu","neko","shinobu","megumin"
    ])
    async def self_emote(self, ctx: commands.Context):
        cmd = ctx.command.name

        gif_url = await self.fetch_waifu_gif(cmd, nsfw=ctx.channel.is_nsfw())
        if gif_url:
            embed = discord.Embed(
                description=f"{ctx.author.mention} is feeling **{cmd}**!",
                color=random.randint(0, 0xFFFFFF)
            )
            embed.set_image(url=gif_url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚠️ Could not fetch a GIF, try again later.")

async def setup(bot):
    await bot.add_cog(SelfEmotes(bot))
