import json, random, discord
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
