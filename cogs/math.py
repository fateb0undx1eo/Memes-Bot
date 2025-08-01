import discord
from discord.ext import commands
import sympy
from sympy.parsing.sympy_parser import parse_expr
from sympy import simplify
import random

class MathCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="math", aliases=["calc", "calculate"])
    @commands.cooldown(1, 5, commands.BucketType.user)  # 5-second cooldown
    async def math(self, ctx, *, expression: str = None):
        """
        Safely evaluate a math expression using sympy.
        Example: s!math 2+2
        """
        if not expression:
            await ctx.send(f"{ctx.author.mention}, please provide an expression! Example: `s!math 2+2`")
            return

        # Prevent extremely long input
        if len(expression) > 100:
            await ctx.send("⚠️ Expression too long!")
            return

        try:
            # Parse and simplify the expression
            expr = parse_expr(expression, evaluate=True)
            result = simplify(expr)

            # Convert to string for display
            result_str = str(result)

            # Limit output length like original OwO bot
            if len(result_str) > 1000:
                result_str = result_str[:1000] + "..."

            await ctx.send(f"🧮 {ctx.author.mention}, the answer is: **{result_str}**")

        except Exception:
            await ctx.send(f"❌ {ctx.author.mention}, I don't think that's a valid math expression!")

async def setup(bot):
    await bot.add_cog(MathCog(bot))
