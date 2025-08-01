import json
import random
import discord
import aiohttp
import asyncio
import logging
from discord.ext import commands
from typing import Optional, Literal

# Configure logging
logger = logging.getLogger(__name__)

class UserEmotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()  # Persistent session
        
        # Multi-user actions that need a target
        self.emote_actions = {
            "hug": "hug",
            "kiss": "kiss",
            "cuddle": "cuddle",
            "slap": "slap",
            "pat": "pat",
            "poke": "poke",
            "highfive": "highfive",
            "bite": "bite",
            "nom": "nom",
            "kick": "kick",
            "punch": "punch",
            "glomp": "glomp",
            "holdhands": "holdhands",
            "yeet": "yeet",
            "bonk": "bonk",
            "tickle": "tickle"
        }
        
        # Action-specific fallback GIFs
        self.fallback_gifs = {
            "hug": [
                "https://media.tenor.com/3n01nOqK9MkAAAAC/anime-hug.gif",
                "https://media.tenor.com/xGvzBnWbMG0AAAAC/anime-hug.gif"
            ],
            "kiss": [
                "https://media.tenor.com/3N0Q5vKpZX0AAAAC/anime-kiss.gif",
                "https://media.tenor.com/4Hk077jUclAAAAAC/anime-kiss.gif"
            ],
            "slap": [
                "https://media.tenor.com/-G9z8w8Q3-wAAAAC/anime-slap.gif",
                "https://media.tenor.com/UsFANZ7iVd0AAAAC/slap-anime.gif"
            ],
            "pat": [
                "https://media.tenor.com/1bYYC8m9R3YAAAAC/anime-head-pat.gif",
                "https://media.tenor.com/3FpMqJb2gFQAAAAC/pat-anime.gif"
            ],
            "poke": [
                "https://media.tenor.com/4T8xGtDmKdEAAAAC/anime-poke.gif",
                "https://media.tenor.com/4yJd6VlBp2AAAAAC/poke-anime.gif"
            ],
            "cuddle": [
                "https://media.tenor.com/1IYjE7mMh3sAAAAC/anime-cuddle.gif",
                "https://media.tenor.com/q1kqA2g5aGkAAAAC/anime-cuddle.gif"
            ],
            # Add more as needed
        }
        
        # Default fallback if action-specific not found
        self.default_fallback = "https://media.tenor.com/3n01nOqK9MkAAAAC/anime-hug.gif"
        
        # Load responses for roast, compliment, flirt
        self.responses = {
            "roast": ["You're so dense, light bends around you."],
            "compliment": ["You're amazing!"],
            "flirt": ["Are you a magician? Because whenever I look at you, everyone else disappears."]
        }
        self._load_responses()
    
    def _load_responses(self):
        """Load responses from file with error handling"""
        try:
            with open("data/responses.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                # Validate and merge with defaults
                for key in self.responses.keys():
                    if key in data and isinstance(data[key], list) and len(data[key]) > 0:
                        self.responses[key] = data[key]
        except FileNotFoundError:
            logger.warning("Responses file not found, using defaults")
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Error loading responses: {e}")
    
    async def cog_unload(self):
        """Clean up session when cog unloads"""
        await self.session.close()
    
    async def fetch_emote_gif(self, action: str) -> str:
        """Fetch GIF from nekos.best API with proper error handling"""
        url = f"https://nekos.best/api/v2/{action}?amount=1"
        
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                # Handle rate limits
                if resp.status == 429:
                    retry_after = int(resp.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited for {action}. Retrying after {retry_after}s")
                    await asyncio.sleep(retry_after)
                    return await self.fetch_emote_gif(action)
                
                if resp.status != 200:
                    logger.error(f"API returned {resp.status} for {action}")
                    return random.choice(self.fallback_gifs.get(action, [self.default_fallback]))
                
                data = await resp.json()
                return data["results"][0]["url"]
                
        except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, IndexError) as e:
            logger.error(f"Failed to fetch {action} GIF: {type(e).__name__} - {e}")
            return random.choice(self.fallback_gifs.get(action, [self.default_fallback]))
    
    async def _handle_no_mention(self, ctx, action: str):
        """Send a temporary error message"""
        responses = [
            f"❌ You need to tag someone to **{action}**, baka!",
            f"❓ Who should I {action}? Tag them next time!",
            f"⚠️ {action.capitalize()} who? Don't forget to mention someone!"
        ]
        msg = await ctx.send(random.choice(responses), delete_after=10)
        try:
            await ctx.message.delete(delay=5)
        except discord.Forbidden:
            pass

    # --- Unified Emote Command Handler ---
    @commands.command(
        name="emote",
        description="Interact with others using anime emotes!",
        aliases=list(emote_actions.keys())
    )
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def user_emote(self, ctx, member: Optional[discord.Member] = None):
        """Handle all user emote commands"""
        action = self.emote_actions.get(ctx.invoked_with, "hug")
        
        if member is None:
            await self._handle_no_mention(ctx, action)
            return
        
        # Prevent self-targeting for certain actions
        if member == ctx.author and action in ["slap", "kick", "punch", "bonk"]:
            responses = [
                "❌ Don't hurt yourself!",
                "🛑 Self-violence is not the answer!",
                "💔 Please be kind to yourself!"
            ]
            await ctx.send(random.choice(responses), delete_after=10)
            return
        
        try:
            gif_url = await self.fetch_emote_gif(action)
            
            # Action-specific messages
            action_messages = {
                "hug": f"{ctx.author.mention} gives {member.mention} a warm hug! 🤗",
                "kiss": f"{ctx.author.mention} kisses {member.mention}! 😘💕",
                "slap": f"{ctx.author.mention} slaps {member.mention}! 👋😠",
                "pat": f"{ctx.author.mention} pats {member.mention}! 👋💖",
                "poke": f"{ctx.author.mention} pokes {member.mention}! 👉😊",
                "cuddle": f"{ctx.author.mention} cuddles with {member.mention}! 💕🤗",
                "highfive": f"{ctx.author.mention} high-fives {member.mention}! ✋🎉",
                "yeet": f"{ctx.author.mention} YEETS {member.mention}! 💥🚀"
            }
            
            description = action_messages.get(
                action, 
                f"{ctx.author.mention} **{action}s** {member.mention}!"
            )
            
            embed = discord.Embed(
                description=description,
                color=random.randint(0, 0xFFFFFF)
            )
            embed.set_image(url=gif_url)
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in {action} command: {e}", exc_info=True)
            await ctx.send(f"⚠️ Something went wrong with {action}ing!", delete_after=10)

    # --- Text Interaction Commands ---
    @commands.command(name="roast", description="Roast another user")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def roast(self, ctx, member: Optional[discord.Member] = None):
        """Roast another user"""
        await self._text_interaction(ctx, member, "roast", "🔥", ["❌ Roast who?", "⚠️ Who should I roast?"])
    
    @commands.command(name="compliment", description="Compliment another user")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def compliment(self, ctx, member: Optional[discord.Member] = None):
        """Compliment another user"""
        await self._text_interaction(ctx, member, "compliment", "💖", ["❌ Compliment who?", "💝 Who deserves a compliment?"])
    
    @commands.command(name="flirt", description="Flirt with another user")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def flirt(self, ctx, member: Optional[discord.Member] = None):
        """Flirt with another user"""
        await self._text_interaction(ctx, member, "flirt", "😍", ["❌ Flirt with who?", "💘 Who caught your eye?"])
    
    async def _text_interaction(self, ctx, member, action, emoji, errors):
        """Handle text-based interactions"""
        if member is None:
            await ctx.send(random.choice(errors), delete_after=10)
            try:
                await ctx.message.delete(delay=5)
            except discord.Forbidden:
                pass
            return
        
        # Prevent self-interactions for certain actions
        if member == ctx.author and action in ["roast"]:
            responses = [
                "❌ Don't roast yourself!",
                "🛑 Be kind to yourself!",
                "💔 Self-roasting is not allowed!"
            ]
            await ctx.send(random.choice(responses), delete_after=10)
            return
        
        line = random.choice(self.responses.get(action, [f"You're awesome!"]))
        
        embed = discord.Embed(
            description=f"{emoji} {member.mention}, {line}",
            color=random.randint(0, 0xFFFFFF)
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(UserEmotes(bot))
