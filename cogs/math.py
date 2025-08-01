import discord
from discord.ext import commands
import sympy
import random

class MathCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="math",
        aliases=["calc", "calculate"],
        help="Solve a math expression using sympy. Example: s!math 2+2"
    )
    @commands.cooldown(1, 7, commands.BucketType.user)  # 7 sec cooldown per user
    async def math_command(self, ctx: commands.Context, *, expression: str = None):
        if not expression:
            await ctx.send("❌ Please provide an expression to calculate, e.g., `s!math 2+2`")
            return

        try:
            # Parse & evaluate safely
            expr = sympy.sympify(expression)
            result = expr.evalf()

            # Random color embed for fun
            embed = discord.Embed(
                title="🧮 Math Result",
                description=f"**Expression:** `{expression}`\n**Answer:** `{result}`",
                color=random.randint(0, 0xFFFFFF)
            )
            await ctx.send(embed=embed)

        except sympy.SympifyError:
            await ctx.send("⚠️ Invalid math expression! Please try again.")

    # Error handler for cooldown
    @math_command.error
    async def math_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Wait {error.retry_after:.1f}s before using this command again!", delete_after=5)

# Required setup function for discord.py 2.x
async def setup(bot: commands.Bot):
    await bot.add_cog(MathCog(bot))

