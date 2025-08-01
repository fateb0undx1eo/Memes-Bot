import discord
from discord.ext import commands
import re
import asyncio
import random

class SenpaiUwU(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}

    def owoify(self, text: str) -> str:
        """Basic OwOify text transformation."""
        # Replace common letters
        text = re.sub(r'[rl]', 'w', text)
        text = re.sub(r'[RL]', 'W', text)

        # Add random faces occasionally
        faces = ['OwO', 'UwU', '>w<', '^w^', '(* ^ ω ^)', '(◕‿◕✿)']
        if random.random() < 0.3:
            text += " " + random.choice(faces)

        # Replace n+vowels with ny+vowel
        text = re.sub(r'n([aeiou])', r'ny\1', text)
        text = re.sub(r'N([aeiouAEIOU])', r'Ny\1', text)
        return text

    @commands.command(
        name="uwu",
        aliases=["owoify", "ify", "uwuify", "owo"]
    )
    async def uwuify_command(self, ctx, *, text: str = None):
        user_id = ctx.author.id

        # --- 7 sec cooldown per user ---
        now = asyncio.get_event_loop().time()
        last_used = self.cooldowns.get(user_id, 0)
        if now - last_used < 7:
            retry_after = 7 - int(now - last_used)
            await ctx.send(f"⏳ Wait {retry_after}s before uwuifying again!")
            return
        self.cooldowns[user_id] = now

        # If no text, fetch the previous message in channel
        if text is None:
            async for msg in ctx.channel.history(limit=2):
                if msg.id != ctx.message.id and not msg.author.bot:
                    text = msg.content
                    break
            if text is None or text.strip() == "":
                await ctx.send("❌ Nothing to uwuify, baka!")
                return

        uwu_text = self.owoify(text)
        # Avoid pinging people
        uwu_text = re.sub(r"<@!?\d+>", "@someone", uwu_text)

        # Send in an embed with random color
        embed = discord.Embed(
            description=uwu_text,
            color=random.randint(0, 0xFFFFFF)
        )
        embed.set_author(name=f"{ctx.author.display_name} says:")
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(SenpaiUwU(bot))
