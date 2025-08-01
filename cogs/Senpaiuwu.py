import discord
from discord.ext import commands
import random
import re

class OwOCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def owoify(self, text: str) -> str:
        """Convert normal text to OwOified text"""
        text = re.sub(r"[rl]", "w", text)
        text = re.sub(r"[RL]", "W", text)
        text = re.sub(r"n([aeiou])", r"ny\1", text, flags=re.IGNORECASE)
        text = re.sub(r"N([aeiouAEIOU])", r"Ny\1", text)
        faces = ["UwU", "OwO", ">w<", "^w^", "(✿◕‿◕)"]
        if random.random() < 0.3:
            text += " " + random.choice(faces)
        return text

    @commands.command(name="uwu", aliases=["owo", "owoify", "ify"])
    @commands.cooldown(1, 7, commands.BucketType.user)  # 1 use every 7 seconds per user
    async def uwu(self, ctx, *, text: str = None):
        """OwOify the given text or the last message in the channel"""
        # If no text given, take the last non-bot message
        if not text:
            async for msg in ctx.channel.history(limit=2):
                if msg.id != ctx.message.id and not msg.author.bot:
                    text = f"**{msg.author.display_name}:** {msg.content}"
                    break
            if not text:
                await ctx.send(f"{ctx.author.mention}, there is no message before yours! UwU")
                return

        owofied = self.owoify(text)
        await ctx.send(owofied)

async def setup(bot):
    await bot.add_cog(OwOCog(bot))
