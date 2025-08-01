import json, random, discord, aiohttp, asyncio
from discord.ext import commands

class UserEmotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Actions that require tagging a user
        self.user_emotes = [
            "kick", "bully", "cuddle", "hug", "kiss", "lick", "pat",
            "bonk", "yeet", "glomp", "slap", "kill", "poke", "highfive",
            "wave", "handhold", "nom", "bite"
        ]
        # Load responses for roast, compliment, flirt
        with open("data/responses.json", "r", encoding="utf-8") as f:
            self.responses = json.load(f)

    async def _handle_no_mention(self, ctx, action: str):
        """Send a temporary error message and delete the user command."""
        msg = await ctx.send(f"❌ You need to tag someone to **{action}**, baka!")
        await msg.delete(delay=10)
        await ctx.message.delete(delay=10)

    async def fetch_waifu_gif(self, action: str, nsfw: bool = False):
        """Fetch GIF from waifu.pics with retries and timeout."""
        base = "https://api.waifu.pics"
        category = "nsfw" if nsfw else "sfw"
        url = f"{base}/{category}/{action}"

        for attempt in range(3):
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            gif_url = data.get("url")
                            if gif_url:
                                return gif_url
            except Exception as e:
                print(f"[UserEmotes] Attempt {attempt+1} failed for {url}: {e}")
            await asyncio.sleep(1)

        # Optional fallback GIFs
        fallback_gifs = [
            "https://media.tenor.com/3n01nOqK9MkAAAAC/anime-hug.gif",
            "https://media.tenor.com/-G9z8w8Q3-wAAAAC/anime-slap.gif"
        ]
        return random.choice(fallback_gifs)

    # --- User Emote Commands (hug/slap/etc.) ---
    @commands.command(name="hug", aliases=[
        "kick","bully","cuddle","kiss","lick","pat","bonk","yeet",
        "glomp","slap","kill","poke","highfive","wave","handhold","nom","bite"
    ])
    async def user_emote(self, ctx, member: discord.Member = None):
        cmd = ctx.command.name
        if member is None:
            await self._handle_no_mention(ctx, cmd)
            return

        gif_url = await self.fetch_waifu_gif(cmd, nsfw=ctx.channel.is_nsfw())
        if gif_url:
            embed = discord.Embed(
                description=f"{ctx.author.mention} **{cmd}s** {member.mention}!",
                color=random.randint(0, 0xFFFFFF)
            )
            embed.set_image(url=gif_url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("⚠️ Could not fetch a GIF, try again later.")

    # --- Roast / Compliment / Flirt ---
    @commands.command(name="roast")
    async def roast(self, ctx, member: discord.Member = None):
        if member is None:
            await self._handle_no_mention(ctx, "roast")
            return
        line = random.choice(self.responses["roast"])
        await ctx.send(f"🔥 {member.mention}, {line}")

    @commands.command(name="compliment")
    async def compliment(self, ctx, member: discord.Member = None):
        if member is None:
            await self._handle_no_mention(ctx, "compliment")
            return
        line = random.choice(self.responses["compliment"])
        await ctx.send(f"💖 {member.mention}, {line}")

    @commands.command(name="flirt")
    async def flirt(self, ctx, member: discord.Member = None):
        if member is None:
            await self._handle_no_mention(ctx, "flirt")
            return
        line = random.choice(self.responses["flirt"])
        await ctx.send(f"😍 {member.mention}, {line}")

# Required setup function for discord.py 2.x
async def setup(bot: commands.Bot):
    await bot.add_cog(UserEmotes(bot))
