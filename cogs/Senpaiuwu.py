import discord
from discord.ext import commands
import random
import re

class SenpaiUwU(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def owoify(self, text: str) -> str:
        """Basic OwO/UwU text transformation."""
        # Replace 'r' and 'l' with 'w'
        text = re.sub(r'[rl]', 'w', text)
        text = re.sub(r'[RL]', 'W', text)
        
        # Add some faces randomly
        faces = ["UwU", "OwO", ">w<", "^w^", "(* ^ ω ^)", "(o´∀`o)", "(✿oωo)"]
        text += " " + random.choice(faces)
        
        return text

    @commands.command(
        name="uwu",
        aliases=["owo", "owoify", "ify"],
        help="OwOify your text or the previous message. Example: s!uwu Hello"
    )
    @commands.cooldown(1, 7, commands.BucketType.user)  # 7 sec cooldown per user
    async def uwu_command(self, ctx: commands.Context, *, text: str = None):
        # If no text, try previous message
        if not text:
            # Fetch the last non-bot message before this one
            async for msg in ctx.channel.history(limit=2):
                if msg.id != ctx.message.id and not msg.author.bot:
                    text = msg.content
                    break

        if not text:
            await ctx.send("❌ No message to UwUify! Please provide text or send after a message.")
            return

        # UwUify the text
        uwu_text = self.owoify(text)
        
        # Create an embed with random color
        embed = discord.Embed(
            title="✨ Senpai UwU ✨",
            description=uwu_text,
            color=random.randint(0, 0xFFFFFF)
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")

        await ctx.send(embed=embed)

    # Handle cooldown error
    @uwu_command.error
    async def uwu_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Wait {error.retry_after:.1f}s before UwUifying again!", delete_after=5)

# Required setup function for discord.py 2.x
async def setup(bot: commands.Bot):
    await bot.add_cog(SenpaiUwU(bot))
