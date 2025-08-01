import discord
from discord.ext import commands
from discord import app_commands
import random
import io
from PIL import Image, ImageDraw, ImageFont
import logging

logger = logging.getLogger(__name__)

class Capture(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.font_cache = {}
        self.max_lines = 50
        self.max_line_length = 80
        self.line_height = 20
        self.padding = 15

    # --- Improved text image creation ---
    async def create_text_image(self, author_name: str, text: str) -> discord.File:
        """Create an image with formatted text content"""
        # Load/create font with better error handling
        if not self.font_cache:
            font_names = [
                "DejaVuSansMono.ttf", 
                "consola.ttf", 
                "cour.ttf", 
                "Courier_New.ttf"
            ]
            for name in font_names:
                try:
                    self.font_cache['mono'] = ImageFont.truetype(name, 14)
                    break
                except IOError:
                    continue
            if 'mono' not in self.font_cache:
                self.font_cache['mono'] = ImageFont.load_default()
                logger.warning("Using fallback font for text rendering")

        font = self.font_cache['mono']
        
        # Process and wrap text
        lines = []
        for line in text.replace('\t', '    ').splitlines():
            while line:
                # Preserve leading spaces for code blocks
                if len(line) > self.max_line_length:
                    # Find last space within max length
                    split_index = line.rfind(' ', 0, self.max_line_length)
                    if split_index <= 0:
                        split_index = self.max_line_length
                    lines.append(line[:split_index])
                    line = line[split_index:].lstrip()
                else:
                    lines.append(line)
                    break
                if len(lines) >= self.max_lines:
                    break
            if len(lines) >= self.max_lines:
                break

        # Truncate if too many lines
        if len(lines) >= self.max_lines:
            lines = lines[:self.max_lines]
            lines[-1] = lines[-1][:77] + "..." if len(lines[-1]) > 77 else lines[-1] + "..."

        # Calculate image dimensions
        header = f"{author_name} said:"
        width = 800
        height = (self.padding * 2) + self.line_height + (len(lines) * self.line_height)

        # Create image
        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        y = self.padding
        
        # Draw header
        draw.text((self.padding, y), header, font=font, fill=(0, 0, 0))
        y += self.line_height
        
        # Draw content lines
        for line in lines:
            draw.text((self.padding, y), line, font=font, fill=(0, 0, 0))
            y += self.line_height

        # Save to byte stream
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return discord.File(buf, filename="capture.png")

    # --- Unified message reposting ---
    async def repost_message(self, ctx_or_interaction, target_message: discord.Message):
        """Handle message reposting for both command types"""
        # Create embed with consistent styling
        embed = discord.Embed(
            description=f"📸 Captured from {target_message.author.mention}",
            color=random.randint(0, 0xFFFFFF),
            timestamp=target_message.created_at
        )
        embed.set_footer(text=f"In #{target_message.channel.name}")

        file = None
        should_upload = False

        # Handle different content types
        if target_message.attachments:
            # Use first image if available
            for att in target_message.attachments:
                if att.content_type and att.content_type.startswith('image/'):
                    embed.set_image(url=att.url)
                    break
            # Fallback to text if no images
            if not embed.image and target_message.content:
                should_upload = True
        elif target_message.content:
            should_upload = True

        # Create text image if needed
        if should_upload:
            try:
                file = await self.create_text_image(
                    target_message.author.display_name,
                    target_message.content
                )
                embed.set_image(url="attachment://capture.png")
            except Exception as e:
                logger.error(f"Image creation failed: {e}")

        # Handle no content case
        if not embed.image and not file:
            error_msg = "❌ Nothing to capture (no text/images)"
            if isinstance(ctx_or_interaction, commands.Context):
                await ctx_or_interaction.send(error_msg, delete_after=10)
            else:
                await ctx_or_interaction.response.send_message(error_msg, ephemeral=True)
            return

        # Send response
        try:
            if isinstance(ctx_or_interaction, commands.Context):
                await ctx_or_interaction.send(embed=embed, file=file)
            else:
                await ctx_or_interaction.response.send_message(embed=embed, file=file)
        except discord.HTTPException as e:
            logger.error(f"Failed to send message: {e}")

    # --- Prefix Command ---
    @commands.command(name="capture", aliases=["cap", "snap"])
    async def capture_prefix(self, ctx: commands.Context):
        """Capture replied message or recent message"""
        # Check message reference first
        if ctx.message.reference and ctx.message.reference.resolved:
            if isinstance(ctx.message.reference.resolved, discord.Message):
                target_message = ctx.message.reference.resolved
            else:
                target_message = None
        else:
            # Search recent messages
            target_message = None
            async for msg in ctx.channel.history(limit=10):
                if not msg.author.bot and msg.id != ctx.message.id:
                    target_message = msg
                    break

        if not target_message:
            await ctx.send("❌ No recent message found", delete_after=10)
            try:
                await ctx.message.delete(delay=3)
            except:
                pass
            return

        await self.repost_message(ctx, target_message)
        try:
            await ctx.message.delete(delay=3)
        except discord.Forbidden:
            pass

    # --- Slash Command ---
    @app_commands.command(name="capture", description="Capture a message/media and repost as the bot")
    @app_commands.describe(message="Message to capture (leave blank for most recent)")
    async def capture_slash(
        self, 
        interaction: discord.Interaction,
        message: discord.Message = None
    ):
        """Slash command version with message option"""
        await interaction.response.defer()
        
        if not message:
            # Find recent non-bot message
            async for msg in interaction.channel.history(limit=10):
                if not msg.author.bot:
                    message = msg
                    break

        if not message:
            await interaction.followup.send("❌ No message found to capture", ephemeral=True)
            return

        await self.repost_message(interaction, message)

async def setup(bot: commands.Bot):
    await bot.add_cog(Capture(bot))
