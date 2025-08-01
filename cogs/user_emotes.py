import discord
from discord.ext import commands
import aiohttp, json, random, os

class UserEmotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Supported user emotes
        self.user_emotes = ["hug", "pat", "kiss", "slap", "poke"]
        # Load responses JSON for roast/compliment/flirt
        self.responses_file = os.path.join("data", "responses.json")
        with open(self.responses_file, "r", encoding="utf-8") as f:
            self.responses = json.load(f)

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

    # --- User Emotes like hug/slap/kiss ---
    @commands.command(name="hug", aliases=["pat","kiss","slap","poke"])
    async def user_emote(self, ctx: commands.Context, member: discord.Member = None):
        cmd = ctx.command.name

        if member is None:
            await ctx.send(f"❌ You need to tag someone to **{cmd}**, baka!")
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
    async def roast(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            await ctx.send("❌ Tag someone to roast, baka!")
            return
        line = random.choice(self.responses["roast"])
        await ctx.send(f"🔥 {member.mention}, {line}")

    @commands.command(name="compliment")
    async def compliment(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            await ctx.send("❌ Tag someone to compliment!")
            return
        line = random.choice(self.responses["compliment"])
        await ctx.send(f"💖 {member.mention}, {line}")

    @commands.command(name="flirt")
    async def flirt(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            await ctx.send("❌ Tag someone to flirt with!")
            return
        line = random.choice(self.responses["flirt"])
        await ctx.send(f"😍 {member.mention}, {line}")

async def setup(bot):
    await bot.add_cog(UserEmotes(bot))
