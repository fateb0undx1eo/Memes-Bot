import discord
from discord.ext import commands
import aiohttp
import asyncio
import random
import logging

logger = logging.getLogger('MemeBot.SelfEmotes')

class SelfEmotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Primary command name -> aliases (include primary for simplicity)
        self.emote_types = {
            "blush": ["blush", "shy", "embarrassed"],
            "smile": ["smile", "grin", "happy"],
            "happy": ["happy", "joy", "excited"],
            "dance": ["dance", "dancing", "party"],
            "cry": ["cry", "crying", "sad", "tears"],
            "wink": ["wink", "flirt", "tease"]
        }

        self.api_url = "https://api.waifu.pics"

        # Automatically register all commands
        self.register_emote_commands()

    def register_emote_commands(self):
        """Automatically create commands for all emote types, avoiding duplicates."""
        registered_names = set()

        for primary, aliases in self.emote_types.items():
            # Remove duplicate aliases to avoid registration errors
            unique_aliases = [a for a in aliases if a not in registered_names]
            if not unique_aliases:
                continue  # Skip if nothing unique left

            command_name = unique_aliases[0]
            command_aliases = unique_aliases[1:]

            async def dynamic_emote(ctx, emote=primary):
                await self.handle_emote(ctx, emote)

            # Avoid capturing late-binding variable in loop
            dynamic_emote.__name__ = f"cmd_{primary}"

            # Create the command dynamically
            cmd = commands.Command(
                func=dynamic_emote,
                name=command_name,
                aliases=command_aliases
            )

            # Register the command to the bot
            try:
                self.bot.add_command(cmd)
                registered_names.update(unique_aliases)
                logger.info(f"✅ Registered self-emote command: {command_name} (aliases: {command_aliases})")
            except commands.errors.CommandRegistrationError as e:
                logger.warning(f"⚠️ Skipped duplicate command: {command_name} ({str(e)})")

    async def fetch_waifu_gif(self, action: str, nsfw: bool = False):
        """Fetch a waifu GIF URL from waifu.pics with proper error handling"""
        try:
            category = "nsfw" if nsfw else "sfw"
            url = f"{self.api_url}/{category}/{action}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("url")
                    logger.warning(f"Waifu API error: Status {resp.status}")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching GIF: {str(e)}")
        except asyncio.TimeoutError:
            logger.warning("Waifu API request timed out")
        return None

    async def handle_emote(self, ctx, emote_type):
        """Handle all emote commands with GIF fetching and error handling"""
        try:
            gif_url = await self.fetch_waifu_gif(
                emote_type,
                nsfw=ctx.channel.is_nsfw() if hasattr(ctx.channel, 'is_nsfw') else False
            )

            if gif_url:
                embed = discord.Embed(
                    description=f"{ctx.author.mention} is **{emote_type}**!",
                    color=random.randint(0, 0xFFFFFF)
                )
                embed.set_image(url=gif_url)
                await ctx.send(embed=embed)
            else:
                await ctx.send("😢 Couldn't fetch a GIF right now. Try again later!")
        except Exception as e:
            logger.error(f"Error in {emote_type} command: {str(e)}")
            await ctx.send("⚠️ Something went wrong with that command!")

async def setup(bot):
    await bot.add_cog(SelfEmotes(bot))
