import discord
from discord.ext import commands
import random
from colorthief import ColorThief
import aiohttp
import io

class Colors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_dominant_color(self, image_url: str):
        """Fetches image from URL and returns its dominant color."""
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        img_bytes = await resp.read()
                        color_thief = ColorThief(io.BytesIO(img_bytes))
                        return color_thief.get_color(quality=1)  # (R, G, B)
        except Exception as e:
            print(f"[Colors] Failed to fetch image: {e}")
        return (255, 255, 255)  # fallback white

    @commands.command(name="color", aliases=["colour", "dominant"])
    async def color(self, ctx: commands.Context, url: str = None):
        """Get the dominant color from an attached image or URL."""
        # Determine image source
        if url:
            image_url = url
        elif ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        else:
            await ctx.send("❌ Please provide an image URL or attach an image.")
            return

        # Fetch dominant color
        rgb = await self.get_dominant_color(image_url)
        hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

        # Build embed preview
        embed = discord.Embed(
            title="🎨 Dominant Color",
            description=f"**RGB:** {rgb}\n**HEX:** {hex_color}",
            color=discord.Color.from_rgb(*rgb)
        )
        embed.set_thumbnail(url=image_url)
        await ctx.send(embed=embed)

# Required setup function
async def setup(bot: commands.Bot):
    await bot.add_cog(Colors(bot))
