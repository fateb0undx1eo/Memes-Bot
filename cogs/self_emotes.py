import discord
from discord.ext import commands
import aiohttp, random, asyncio

class SelfEmotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Single-user emotes
        self.self_emotes = [
            "smile", "dance", "wink", "blush", "cry", "happy", "thinking",
            "wave", "laugh", "shrug", "pout", "sleep"
        ]

        # API base for nekos.best
        self.api_base = "https://nekos.best/api/v2"

        # Fallback GIFs if API fails
        self.fallback_gifs = [
            "https://media.tenor.com/q4M8p0QQUCkAAAAC/anime-blush.gif",
            "https://media.tenor.com/G1i1ny-H9HIAAAAC/anime-smile.gif",
            "https://media.tenor.com/QvC0f3dGh2wAAAAd/anime-dance.gif"
        ]

    async def fetch_emote_gif(self, action: str):
        """Fetch GIF from nekos.best API with retries."""
        url = f"{self.api_base}/{action}?amount=1"
        for attempt in range(3):
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            # nekos.best returns: {"results":[{"url":"..."}, ...]}
                            results = data.get("results", [])
                            if results and "url" in results[0]:
                                return results[0]["url"]
            except Exception as e:
                print(f"[SelfEmotes] Attempt {attempt+1} failed for {action}: {e}")
            await asyncio.sleep(1)
        return random.choice(self.fallback_gifs)

    # Register a single command with aliases
    @commands.command(name="smile", aliases=[
        "dance","wink","blush","cry","happy","thinking",
        "wave","laugh","shrug","pout","sleep"
    ])
    async def self_emote(self, ctx: commands.Context):
        cmd = ctx.command.name
        gif_url = await self.fetch_emote_gif(cmd)
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
