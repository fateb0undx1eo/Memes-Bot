import discord
from discord import app_commands
from discord.ext import commands
import random
import re
import colorsys
from typing import Optional

class ColorsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color_services = [
            "https://singlecolorimage.com/get/{hex}/200x200",
            "https://dummyimage.com/200x200/{hex}/{hex}",
            "https://via.placeholder.com/200/{hex}?text=+"
        ]
        self.named_colors = {
            "red": 0xFF0000, "green": 0x00FF00, "blue": 0x0000FF,
            "yellow": 0xFFFF00, "purple": 0x800080, "orange": 0xFFA500,
            "pink": 0xFFC0CB, "cyan": 0x00FFFF, "brown": 0xA52A2A,
            "white": 0xFFFFFF, "black": 0x000000, "gray": 0x808080,
            "silver": 0xC0C0C0, "gold": 0xFFD700, "violet": 0xEE82EE
        }

    async def ensure_allowed_channel(self, interaction: discord.Interaction) -> bool:
        """No channel restrictions anymore"""
        return True

    def parse_color_input(self, input_str: str) -> Optional[int]:
        """Parse various color formats into an integer value"""
        input_str = input_str.strip().lower()
        
        # Named color
        if input_str in self.named_colors:
            return self.named_colors[input_str]
            
        # Hex code
        if re.match(r'^#?([a-f0-9]{6}|[a-f0-9]{3})$', input_str):
            hex_code = input_str.lstrip('#')
            if len(hex_code) == 3:
                hex_code = ''.join(c * 2 for c in hex_code)
            return int(hex_code, 16)
            
        # RGB tuple
        rgb_match = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', input_str)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                return (r << 16) | (g << 8) | b
        
        return None

    def get_color_embed(self, color_value: int, title: str = "Color") -> discord.Embed:
        """Create a rich embed for a color"""
        hex_code = f"{color_value:06X}"
        r, g, b = (color_value >> 16) & 0xFF, (color_value >> 8) & 0xFF, color_value & 0xFF
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        
        # Pick first image service
        image_url = self.color_services[0].format(hex=hex_code)
        
        embed = discord.Embed(title=f"🎨 {title}", color=color_value)
        embed.add_field(name="HEX", value=f"`#{hex_code}`", inline=True)
        embed.add_field(name="RGB", value=f"`rgb({r}, {g}, {b})`", inline=True)
        embed.add_field(name="HSV", value=f"`hsv({int(h*360)}°, {int(s*100)}%, {int(v*100)}%)`", inline=False)
        
        # Find closest named color
        closest_name, closest_diff = None, float('inf')
        for name, value in self.named_colors.items():
            diff = sum(abs((value >> i & 0xFF) - (color_value >> i & 0xFF)) for i in (16, 8, 0))
            if diff < closest_diff:
                closest_name, closest_diff = name, diff
        
        if closest_diff < 100:
            embed.add_field(name="Closest Named", value=f"**{closest_name.capitalize()}**", inline=True)
        
        embed.set_thumbnail(url=image_url)
        embed.set_footer(text=f"Color Value: {color_value}")
        return embed

    # --- Color Commands ---
    @app_commands.command(name="randomcolor", description="Generate a random color with preview")
    async def random_color(self, interaction: discord.Interaction):
        color_value = random.randint(0, 0xFFFFFF)
        embed = self.get_color_embed(color_value, "Random Color")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="color", description="Preview a color from hex, name, or RGB")
    @app_commands.describe(color="Hex code, color name, or RGB value (e.g. #FF5733, red, rgb(255,87,51))")
    async def color_preview(self, interaction: discord.Interaction, color: str):
        color_value = self.parse_color_input(color)
        if color_value is None:
            await interaction.response.send_message(
                "❌ Invalid color format. Use:\n"
                "- Hex code: `#FF5733` or `FF5733`\n"
                "- Color name: `red`, `blue`, etc.\n"
                "- RGB value: `rgb(255, 87, 51)`",
                ephemeral=True
            )
            return
            
        embed = self.get_color_embed(color_value)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="complementary", description="Get complementary color for a given color")
    @app_commands.describe(color="Base color in hex, name, or RGB")
    async def complementary_color(self, interaction: discord.Interaction, color: str):
        color_value = self.parse_color_input(color)
        if color_value is None:
            await interaction.response.send_message("❌ Invalid color format", ephemeral=True)
            return
            
        r, g, b = (color_value >> 16) & 0xFF, (color_value >> 8) & 0xFF, color_value & 0xFF
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        comp_h = (h + 0.5) % 1.0
        comp_r, comp_g, comp_b = colorsys.hsv_to_rgb(comp_h, s, v)
        comp_value = (int(comp_r*255) << 16) | (int(comp_g*255) << 8) | int(comp_b*255)
        
        base_embed = self.get_color_embed(color_value, "Base Color")
        comp_embed = self.get_color_embed(comp_value, "Complementary Color")
        
        await interaction.response.send_message(embeds=[base_embed, comp_embed])

    def adjust_hsv(self, h: float, s: float, v: float,
                   h_delta: float = 0, s_delta: float = 0, v_delta: float = 0) -> int:
        """Adjust HSV values and return as integer color"""
        new_h = (h + h_delta/360) % 1.0
        new_s = max(0, min(1, s + s_delta))
        new_v = max(0, min(1, v + v_delta))
        r, g, b = colorsys.hsv_to_rgb(new_h, new_s, new_v)
        return (int(r*255) << 16) | (int(g*255) << 8) | int(b*255)

async def setup(bot: commands.Bot):
    await bot.add_cog(ColorsCog(bot))
