import json, random, discord
from discord.ext import commands

class UserEmotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_emotes = [
            "kick","bully","cuddle","hug","kiss","lick","pat",
            "bonk","yeet","glomp","slap","kill","poke","highfive",
            "wave","handhold","nom","bite"
        ]
        # Load responses for roast, compliment, flirt
        with open("data/responses.json", "r", encoding="utf-8") as f:
            self.responses = json.load(f)

    # --- Roast / Compliment / Flirt ---
    @commands.command(name="roast")
    async def roast(self, ctx, member: discord.Member = None):
        if member is None:
            msg = await ctx.send("❌ Tag someone to roast, baka!")
            await msg.delete(delay=10)
            await ctx.message.delete(delay=10)
            return
        line = random.choice(self.responses["roast"])
        await ctx.send(f"🔥 {member.mention}, {line}")

    @commands.command(name="compliment")
    async def compliment(self, ctx, member: discord.Member = None):
        if member is None:
            msg = await ctx.send("❌ Tag someone to compliment!")
            await msg.delete(delay=10)
            await ctx.message.delete(delay=10)
            return
        line = random.choice(self.responses["compliment"])
        await ctx.send(f"💖 {member.mention}, {line}")

    @commands.command(name="flirt")
    async def flirt(self, ctx, member: discord.Member = None):
        if member is None:
            msg = await ctx.send("❌ Tag someone to flirt with!")
            await msg.delete(delay=10)
            await ctx.message.delete(delay=10)
            return
        line = random.choice(self.responses["flirt"])
        await ctx.send(f"😍 {member.mention}, {line}")
