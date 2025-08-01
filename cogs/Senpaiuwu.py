import discord
from discord.ext import commands
import re
import asyncio
import random
import logging
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

class SenpaiUwU(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = commands.CooldownMapping.from_cooldown(
            1, 7, commands.BucketType.user
        )
        self.max_length = 1800  # Max characters to process
        self.uwu_faces = [
            "OwO", "UwU", ">w<", "^w^", "(* ^ ω ^)", "(◕‿◕✿)", ";;w;;", "(⁄ ⁄>⁄ ▽ ⁄<⁄ ⁄)",
            "(╯✧▽✧)╯", "✧･ﾟ: *✧･ﾟ♡", "♡(˃͈ દ ˂͈ ༶ )", "(˶ᵔ ᵕ ᵔ˶)", "ヾ(≧▽≦*)o", "(⁄˃⁄ ▽ ⁄˂⁄)"
        ]
        self.stutter_chance = 0.25  # Chance to add stutter
        self.face_chance = 0.4      # Chance to add uwu face

    def owoify(self, text: str) -> str:
        """Advanced OwOify text transformation with multiple rules"""
        # Preserve code blocks
        code_blocks = []
        def code_replacer(match):
            code_blocks.append(match.group(0))
            return f"__CODE_BLOCK_{len(code_blocks)-1}__"
        
        # Temporarily remove code blocks
        text = re.sub(r'```[^`]*```|`[^`]*`', code_replacer, text, flags=re.DOTALL)
        
        # Define transformation rules
        replacements = [
            (r'(?:r|l)', 'w'),                          # r/l -> w
            (r'(?:R|L)', 'W'),                          # R/L -> W
            (r'n([aeiou])', r'ny\1'),                   # n+vowel -> ny+vowel
            (r'N([aeiou])', r'Ny\1'),                   # N+vowel -> Ny+vowel
            (r'N([AEIOU])', r'NY\1'),                   # N+uppercase vowel
            (r'th\b', 'f'),                             # word-ending th -> f
            (r'th', 'd'),                               # th -> d
            (r'Th\b', 'F'),                             # word-ending Th -> F
            (r'Th', 'D'),                               # Th -> D
            (r'ove', 'uv'),                             # ove -> uv
            (r'\b(you|u)\b', 'yu'),                    # you/u -> yu
            (r'\b(You|U)\b', 'Yu'),                    # You/U -> Yu
            (r'!+', lambda m: '! ' + random.choice(['>w<', '^^', '♡'])),
            (r'\?+', lambda m: '? ' + random.choice(['OwO?', 'UwU?', '>w>?'])),
            (r'\.+', lambda m: '. ' + random.choice(self.uwu_faces) if random.random() < self.face_chance else m.group(0))
        ]
        
        # Apply transformations
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)
        
        # Add random stutters
        words = text.split()
        for i in range(len(words)):
            if (random.random() < self.stutter_chance and 
                len(words[i]) > 2 and 
                words[i][0].isalpha() and 
                not words[i].startswith('__CODE_BLOCK_')):
                words[i] = f"{words[i][0]}-{words[i]}"
        text = " ".join(words)
        
        # Add final uwu face with chance
        if random.random() < self.face_chance:
            text += " " + random.choice(self.uwu_faces)
        
        # Restore code blocks
        for i, code_block in enumerate(code_blocks):
            text = text.replace(f"__CODE_BLOCK_{i}__", code_block)
        
        return text

    @commands.command(
        name="uwu",
        aliases=["owoify", "ify", "uwuify", "owo"],
        description="Transform text into uwu-speak! (◕‿◕✿)"
    )
    @commands.cooldown(1, 7, commands.BucketType.user)
    async def uwuify_command(self, ctx, *, text: Optional[str] = None):
        """Transform text or the previous message into cute uwu speak"""
        # Get original message if none provided
        if text is None:
            async for msg in ctx.channel.history(limit=5, before=ctx.message):
                if not msg.author.bot and msg.content.strip():
                    text = msg.content
                    break
            if not text:
                await ctx.send("❌ No text to uwuify! Pwease pwovide some text OwO", delete_after=10)
                return

        # Truncate long messages
        if len(text) > self.max_length:
            text = text[:self.max_length] + "..."
            await ctx.send("⚠️ Text was too wong, twuncated for uwuification! >w<", delete_after=5)

        # Create uwu version
        try:
            uwu_text = self.owoify(text)
            
            # Prevent mention pings
            uwu_text = discord.utils.escape_mentions(uwu_text)
            
            # Create embed
            embed = discord.Embed(
                description=uwu_text,
                color=random.randint(0, 0xFFFFFF)
            )
            embed.set_author(
                name=f"{ctx.author.display_name} says:",
                icon_url=ctx.author.display_avatar.url
            )
            embed.set_footer(text="Powered by SenpaiUwU magic! ✨")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Uwuification failed: {e}", exc_info=True)
            await ctx.send("❌ Something went wrong with uwuification! ;w;", delete_after=10)

    @uwuify_command.error
    async def uwuify_error(self, ctx, error):
        """Handle cooldown errors"""
        if isinstance(error, commands.CommandOnCooldown):
            retry_after = int(error.retry_after)
            cute_time = random.choice(["soon", "in a bit", "later", "after a nap"])
            await ctx.send(
                f"⏳ Too fast! Pwease twy again {cute_time}~ "
                f"({retry_after} seconds cooldown) >w<",
                delete_after=retry_after
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(SenpaiUwU(bot))
