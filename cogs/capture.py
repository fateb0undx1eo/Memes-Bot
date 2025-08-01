import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageOps
import aiohttp
import io
import random

UPVOTE = "<:49noice:1390641356397088919>"
DOWNVOTE = "<a:55emoji_76:1390673781743423540>"

class Capture(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="capture", aliases=["scapture"])
    async def capture(self, ctx: commands.Context):
        """
        Capture a replied message as either media repost or screenshot.
        Works with /capture, /scapture, s!capture, senpai capture
        """
        msg_ref = ctx.message.reference

        if msg_ref is None:
            await ctx.reply("❌ Please reply to a message to capture!", delete_after=10)
            return

        target_msg = await ctx.channel.fetch_message(msg_ref.message_id)

        # If the target has attachments (image/video), repost it
        if target_msg.attachments:
            media_url = target_msg.attachments[0].url
            embed = discord.Embed(
                description=f"🎬 Captured from {target_msg.author.mention}",
                color=discord.Color.random()
            )
            embed.set_image(url=media_url)
            repost = await ctx.send(embed=embed)

        else:
            # Generate screenshot-like image for text messages
            text = target_msg.content or "[No Text]"
            avatar_url = target_msg.author.display_avatar.url

            # Fetch avatar
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as resp:
                    avatar_bytes = await resp.read()
            avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((64, 64))

            # Make avatar circular
            mask = Image.new("L", (64, 64), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, 64, 64), fill=255)
            avatar_img = ImageOps.fit(avatar_img, (64, 64))
            avatar_img.putalpha(mask)

            # Create canvas (Dark Discord-like background)
            img = Image.new("RGBA", (700, 140), (54, 57, 63, 255))
            img.paste(avatar_img, (20, 38), avatar_img)

            draw = ImageDraw.Draw(img)

            # Load a font
            try:
                font_name = ImageFont.truetype("arial.ttf", 24)
                font_text = ImageFont.truetype("arial.ttf", 22)
            except:
                font_name = ImageFont.load_default()
                font_text = ImageFont.load_default()

            # Author name in white
            draw.text((100, 40), target_msg.author.display_name, fill=(255, 255, 255), font=font_name)
            # Message content in light grey, wrapped
            wrapped = "\n".join([text[i:i+50] for i in range(0, len(text), 50)])
            draw.text((100, 70), wrapped, fill=(220, 220, 220), font=font_text)

            # Save to buffer
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            file = discord.File(buffer, filename="capture.png")
            repost = await ctx.send(content=f"🎬 Captured from {target_msg.author.mention}", file=file)

        # Add meme voting reactions
        await repost.add_reaction(UPVOTE)
        await repost.add_reaction(DOWNVOTE)


async def setup(bot):
    await bot.add_cog(Capture(bot))
