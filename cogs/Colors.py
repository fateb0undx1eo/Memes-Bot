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

    @commands.command(aliases=["color", "colour"])
    async def colorcmd(self, ctx, *, input: str = None):
        """Get color info - supports HEX, RGB, @user, or @role"""
        try:
            if not input:
                return await self._send_random_color(ctx)
            
            if ctx.message.mentions:
                return await self._handle_user(ctx, ctx.message.mentions[0])
                
            if ctx.message.role_mentions:
                return await self._handle_role(ctx, ctx.message.role_mentions[0])
                
            return await self._parse_color_input(ctx, input)
            
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}\n{self._get_help(ctx)}")

    async def _send_random_color(self, ctx):
        """Generate random color"""
        r, g, b = random.choices(range(256), k=3)
        embed = self._create_embed(r, g, b)
        await ctx.send(f"🎨 Random color for {ctx.author.mention}:", embed=embed)

    async def _handle_user(self, ctx, user):
        """Extract colors from avatar"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(user.display_avatar.url) as resp:
                    if resp.status != 200:
                        return await ctx.send("❌ Couldn't download avatar")
                    img_data = await resp.read()
            
            cf = ColorThief(BytesIO(img_data))
            palette = cf.get_palette(color_count=5, quality=5)
            
            embeds = []
            for color in palette:
                r, g, b = color
                embeds.append(self._create_embed(r, g, b))
                
            await self._send_paginated(ctx, embeds, f"Colors from {user.display_name}'s avatar")
            
        except Exception as e:
            await ctx.send(f"❌ Failed to process avatar: {str(e)}")

    async def _handle_role(self, ctx, role):
        """Show role color"""
        if role.color == discord.Color.default():
            return await ctx.send("⚠️ This role has no color set")
            
        r, g, b = role.color.to_rgb()
        embed = self._create_embed(r, g, b)
        await ctx.send(f"🎨 Color for role {role.mention}:", embed=embed)

    async def _parse_color_input(self, ctx, input):
        """Process HEX/RGB input"""
        input = input.strip().lower()
        
        # HEX format (#RRGGBB or RRGGBB)
        if re.match(r'^#?([a-f0-9]{6})$', input):
            hex_code = input.lstrip('#')
            r = int(hex_code[0:2], 16)
            g = int(hex_code[2:4], 16)
            b = int(hex_code[4:6], 16)
            embed = self._create_embed(r, g, b)
            return await ctx.send(f"🎨 HEX Color `#{hex_code}`:", embed=embed)
            
        # RGB format (255,255,255)
        elif match := re.match(r'^\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*$', input):
            r, g, b = map(int, match.groups())
            if any(n > 255 for n in (r, g, b)):
                return await ctx.send("❌ RGB values must be 0-255")
            embed = self._create_embed(r, g, b)
            return await ctx.send(f"🎨 RGB Color `{r},{g},{b}`:", embed=embed)
            
        await ctx.send(f"❌ Invalid format!\n{self._get_help(ctx)}")

    def _create_embed(self, r, g, b):
        """Generate color embed"""
        hex_code = f"{r:02x}{g:02x}{b:02x}"
        h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
        return discord.Embed(
            title=f"Color #{hex_code}",
            color=discord.Color.from_rgb(r, g, b),
            description=(
                f"**RGB:** `{r}, {g}, {b}`\n"
                f"**HEX:** `#{hex_code}`\n"
                f"**HSL:** `{int(h*360)}°, {int(s*100)}%, {int(l*100)}%`"
            )
        ).set_thumbnail(url=f"https://singlecolorimage.com/get/{hex_code}/150x150")

    async def _send_paginated(self, ctx, embeds, title):
        """Send paginated embeds"""
        if not embeds:
            return await ctx.send("❌ No colors found")
            
        class Paginator(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.page = 0
                self.embeds = embeds
                self.title = title
                
            @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.blurple)
            async def prev(self, interaction, button):
                self.page = max(0, self.page - 1)
                await self.update(interaction)
                
            @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.blurple)
            async def next(self, interaction, button):
                self.page = min(len(self.embeds) - 1, self.page + 1)
                await self.update(interaction)
                
            async def update(self, interaction):
                embed = self.embeds[self.page]
                embed.set_footer(text=f"Page {self.page+1}/{len(self.embeds)} • {self.title}")
                await interaction.response.edit_message(embed=embed, view=self)
                
            async def on_timeout(self):
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
                
        view = Paginator()
        view.message = await ctx.send(embed=view.embeds[0], view=view)

    def _get_help(self, ctx):
        """Generate help message"""
        return (
            f"**Usage:** `{ctx.prefix}color [value|@user|@role]`\n"
            "• `#RRGGBB` - HEX color\n"
            "• `255,255,255` - RGB values\n"
            "• `@User` - Extract from avatar\n"
            "• `@Role` - Show role color"
        )

async def setup(bot):
    await bot.add_cog(ColorCog(bot))
