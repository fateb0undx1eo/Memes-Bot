import json, random, discord, aiohttp, asyncio
from discord.ext import commands

class UserEmotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Multi-user actions that need a target
        self.user_emotes = [
            "hug", "kiss", "cuddle", "slap", "pat", "poke",
            "highfive", "bite", "nom", "kick", "punch", "glomp",
            "holdhands", "yeet", "bonk", "tickle"
        ]

        self.api_base = "https://nekos.best/api/v2"

        # Fallback GIFs
        self.fallback_gifs = [
            "https://media.tenor.com/3n01nOqK9MkAAAAC/anime-hug.gif",
            "https://media.tenor.com/-G9z8w8Q3-wAAAAC/anime-slap.gif",
            "https://media.tenor.com/3N0Q5vKpZX0AAAAC/anime-kiss.gif"
        ]

        # Load responses for roast, compliment, flirt
        try:
            with open("data/responses.json", "r", encoding="utf-8") as f:
                self.responses = json.load(f)
        except FileNotFoundError:
            self.responses = {"roast": [], "compliment": [], "flirt": []}

    async def _handle_no_mention(self, ctx, action: str):
        """Send a temporary error message and delete the user command."""
        msg = await ctx.send(f"❌ You need to tag someone to **{action}**, baka!")
        await msg.delete(delay=10)
        await ctx.message.delete(delay=10)

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
                            results = data.get("results", [])
                            if results and "url" in results[0]:
                                return results[0]["url"]
            except Exception as e:
                print(f"[UserEmotes] Attempt {attempt+1} failed for {action}: {e}")
            await asyncio.sleep(1)
        return random.choice(self.fallback_gifs)

    # --- User Emote Commands ---
    @commands.command(name="hug", aliases=[
        "kiss","cuddle","slap","pat","poke","highfive","bite","nom",
        "kick","punch","glomp","holdhands","yeet","bonk","tickle"
    ])
    async def user_emote(self, ctx, member: discord.Member = None):
        cmd = ctx.command.name
        if member is None:
            await self._handle_no_mention(ctx, cmd)
            return

        gif_url = await self.fetch_emote_gif(cmd)
        embed = discord.Embed(
            description=f"{ctx.author.mention} **{cmd}s** {member.mention}!",
            color=random.randint(0, 0xFFFFFF)
        )
        embed.set_image(url=gif_url)
        await ctx.send(embed=embed)

    # --- Roast / Compliment / Flirt ---
    @commands.command(name="roast")
    async def roast(self, ctx, member: discord.Member = None):
        if member is None:
            await self._handle_no_mention(ctx, "roast")
            return
        line = random.choice(self.responses.get("roast", ["You're mid."]))
        embed = discord.Embed(
            description=f"🔥 {member.mention}, {line}",
            color=random.randint(0, 0xFFFFFF)
        )
        await ctx.send(embed=embed)

    @commands.command(name="compliment")
    async def compliment(self, ctx, member: discord.Member = None):
        if member is None:
            await self._handle_no_mention(ctx, "compliment")
            return
        line = random.choice(self.responses.get("compliment", ["You're awesome!"]))
        embed = discord.Embed(
            description=f"💖 {member.mention}, {line}",
            color=random.randint(0, 0xFFFFFF)
        )
        await ctx.send(embed=embed)

    @commands.command(name="flirt")
    async def flirt(self, ctx, member: discord.Member = None):
        if member is None:
            await self._handle_no_mention(ctx, "flirt")
            return
        line = random.choice(self.responses.get("flirt", ["Hey cutie 😉"]))
        embed = discord.Embed(
            description=f"😍 {member.mention}, {line}",
            color=random.randint(0, 0xFFFFFF)
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(UserEmotes(bot))
