import discord
from discord.ext import commands
from discord import app_commands
import random
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

class Capture(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def create_text_screenshot(self, text: str, author: str) -> BytesIO:
        """Creates a basic text screenshot for text-only messages."""
        width, height = 800, 200
        background_color = (30, 30, 30)
        text_color = (255, 255, 255)

        img = Image.new("RGB", (width, height), background_color)
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except:
            font = ImageFont.load_default()

        draw.text((20, 50), f"{author}:\n{text}", font=font, fill=text_color)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    async def repost_message(self, ctx, message: discord.Message):
        """Handles reposting media or text screenshot."""
        attachments = message.attachments
        embed = discord.Embed(
            description=f"Captured from {message.author.mention}",
            color=random.randint(0, 0xFFFFFF),
            timestamp=datetime.now()
        )

        if attachments:
            # If media found, repost first image/video
            attachment = attachments[0]
            embed.set_image(url=attachment.url)
            msg = await ctx.send(embed=embed)
        else:
            # If no media, screenshot the text content
            if not message.content.strip():
                await ctx.send("❌ No content to capture!")
                return

            buffer = await self.create_text_screenshot(message.content, message.author.display_name)
            file = discord.File(buffer, filename="capture.png")
            embed.set_image(url="attachment://capture.png")
            msg = await ctx.send(embed=embed, file=file)

        # Add meme voting reactions
        await msg.add_reaction("<:49noice:1390641356397088919>")
        await msg.add_reaction("<a:55emoji_76:1390673781743423540>")

    # === Prefix command capture ===
    @commands.command(name="capture", aliases=["scapture"])
    async def capture_command(self, ctx):
        """Capture a replied message or the previous message."""
        message = None

        # Prefer replied message
        if ctx.message.reference:
            message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        else:
            # Otherwise get the last non-bot message
            async for msg in ctx.channel.history(limit=5):
                if msg.id != ctx.message.id and not msg.author.bot:
                    message = msg
                    break

        if not message:
            await ctx.send("❌ No message to capture!")
            return

        await self.repost_message(ctx, message)

    # === Slash command capture ===
    @app_commands.command(name="scapture", description="Capture a replied message as media or screenshot")
    async def slash_capture(self, interaction: discord.Interaction):
        message = None

        # Fetch the referenced message if the command is used as a reply
        if interaction.message and interaction.message.reference:
            try:
                message = await interaction.channel.fetch_message(interaction.message.reference.message_id)
            except:
                pass

        if not message:
            # fallback to previous non-bot message
            async for msg in interaction.channel.history(limit=5):
                if not msg.author.bot:
                    message = msg
                    break

        if not message:
            await interaction.response.send_message("❌ No message to capture!", ephemeral=True)
            return

        await interaction.response.defer()
        # Create a fake ctx object to reuse repost logic
        class FakeCtx:
            def __init__(self, interaction):
                self.channel = interaction.channel
                self.send = interaction.followup.send
        fake_ctx = FakeCtx(interaction)

        await self.repost_message(fake_ctx, message)


async def setup(bot: commands.Bot):
    await bot.add_cog(Capture(bot))
