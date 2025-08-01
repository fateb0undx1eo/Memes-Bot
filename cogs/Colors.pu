import discord
from discord.ext import commands
import random
import colorsys
from io import BytesIO
import aiohttp
from colorthief import ColorThief
import re

class ColorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_usage_examples(self, ctx):
        """Generate usage examples with the correct prefix"""
        prefix = ctx.prefix
        return (
            f"**Examples:**\n"
            f"`{prefix}color` - Random color\n"
            f"`{prefix}color #FF0000` - Red from HEX\n"
            f"`{prefix}color 255,0,0` - Red from RGB\n"
            f"`{prefix}color @User` - Colors from avatar\n"
            f"`{prefix}color @Role` - Role color"
        )

    @commands.command(aliases=["color", "randcolor", "colour", "randcolour"])
    async def colorcmd(self, ctx, *, arg: str = None):
        """Show colors - accepts HEX, RGB, @user, or @role"""
        try:
            if not arg:
                return await self.handle_random_color(ctx)
            
            if ctx.message.mentions:
                return await self.handle_user_avatar(ctx, ctx.message.mentions[0])
            
            if ctx.message.role_mentions:
                return await self.handle_role_color(ctx, ctx.message.role_mentions[0])
            
            return await self.handle_color_input(ctx, arg)
            
        except Exception as e:
            examples = self.get_usage_examples(ctx)
            await ctx.send(f"🚫 Error: {str(e)}\n{examples}")

    # ... [rest of your methods remain the same, but use ctx.prefix where needed] ...

    async def handle_color_input(self, ctx, arg):
        """Parse color from HEX/RGB input"""
        hex_match = re.match(r"^#?([0-9a-fA-F]{3,6})$", arg.strip())
        if hex_match:
            return await self.display_hex_color(ctx, hex_match.group(1), arg)
        
        rgb_match = re.match(r"(\d{1,3})\s*[,\s]\s*(\d{1,3})\s*[,\s]\s*(\d{1,3})", arg)
        if rgb_match:
            return await self.display_rgb_color(ctx, rgb_match.groups(), arg)
            
        examples = self.get_usage_examples(ctx)
        await ctx.send(f"❌ Invalid color format!\n{examples}")

async def setup(bot):
    await bot.add_cog(ColorCog(bot))
