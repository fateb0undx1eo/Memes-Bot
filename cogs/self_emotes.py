import discord
from discord.ext import commands
import aiohttp, random, asyncio

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

        for attempt in range(3):  # Retry up to 3 times
            try:
                timeout = aiohttp.ClientTimeout(total=10)  # 10 sec timeout
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            gif_url = data.get("url")
                            if gif_url:
                                return gif_url
            except Exception as e:
                print(f"Attempt {attempt+1} failed for {url}: {e}")
            await asyncio.sleep(1)  # wait 1 sec before retry

        # Optional fallback GIFs
        fallback_gifs = [
            "https://media.tenor.com/q4M8p0QQUCkAAAAC/anime-blush.gif",
            "https://media.tenor.com/G1i1ny-H9HIAAAAC/anime-smile.gif"
        ]
        return random.choice(fallback_gifs)

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
