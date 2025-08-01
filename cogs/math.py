import discord
from discord import app_commands
from discord.ext import commands
import random
import math
import typing
import configparser
import os

# Load configuration from file
config = configparser.ConfigParser()
config.read('config.ini')

# Get allowed channels from config with fallback
try:
    ALLOWED_CHANNELS = {
        int(ch_id.strip()) 
        for ch_id in config.get('MATH', 'allowed_channels', fallback='').split(',')
        if ch_id.strip()
    }
except:
    ALLOWED_CHANNELS = set()

class MathCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.max_factorial = 1000  # Prevent excessive computation
        self.max_decimals = 6      # Max decimal places to display

    async def ensure_allowed_channel(self, interaction: discord.Interaction) -> bool:
        """Check if command is used in an allowed channel"""
        if not ALLOWED_CHANNELS:  # No restriction if not configured
            return True
            
        if interaction.channel_id in ALLOWED_CHANNELS:
            return True
            
        channels = ', '.join(f'<#{ch_id}>' for ch_id in ALLOWED_CHANNELS)
        await interaction.response.send_message(
            f"🔢 Math commands are only available in: {channels}",
            ephemeral=True
        )
        return False

    def format_number(self, num: typing.Union[int, float]) -> str:
        """Format numbers intelligently for display"""
        if isinstance(num, int) or num.is_integer():
            return str(int(num))
        return f"{num:.{self.max_decimals}f}".rstrip('0').rstrip('.')

    # --- Core Math Operations ---
    @app_commands.command(name="add", description="Add multiple numbers together")
    @app_commands.describe(numbers="Numbers to add (space separated)")
    async def add(self, interaction: discord.Interaction, numbers: str):
        if not await self.ensure_allowed_channel(interaction):
            return
            
        try:
            nums = [float(n) for n in numbers.split()]
            if not nums:
                raise ValueError("No numbers provided")
                
            result = sum(nums)
            equation = " + ".join(self.format_number(n) for n in nums)
            await interaction.response.send_message(
                f"**{equation} = {self.format_number(result)}**"
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid input. Please provide space-separated numbers.",
                ephemeral=True
            )

    @app_commands.command(name="multiply", description="Multiply multiple numbers")
    @app_commands.describe(numbers="Numbers to multiply (space separated)")
    async def multiply(self, interaction: discord.Interaction, numbers: str):
        if not await self.ensure_allowed_channel(interaction):
            return
            
        try:
            nums = [float(n) for n in numbers.split()]
            if not nums:
                raise ValueError("No numbers provided")
                
            result = 1
            for n in nums:
                result *= n
                
            equation = " × ".join(self.format_number(n) for n in nums)
            await interaction.response.send_message(
                f"**{equation} = {self.format_number(result)}**"
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid input. Please provide space-separated numbers.",
                ephemeral=True
            )

    # --- Advanced Operations ---
    @app_commands.command(name="power", description="Raise a number to a power")
    @app_commands.describe(base="Base number", exponent="Exponent")
    async def power(self, interaction: discord.Interaction, base: float, exponent: float):
        if not await self.ensure_allowed_channel(interaction):
            return
            
        try:
            result = base ** exponent
            await interaction.response.send_message(
                f"**{self.format_number(base)}<sup>{self.format_number(exponent)}</sup> = {self.format_number(result)}**"
            )
        except OverflowError:
            await interaction.response.send_message(
                "⚠️ Result is too large to calculate!",
                ephemeral=True
            )

    @app_commands.command(name="sqrt", description="Calculate square root of a number")
    @app_commands.describe(number="Number to find square root of")
    async def sqrt(self, interaction: discord.Interaction, number: float):
        if not await self.ensure_allowed_channel(interaction):
            return
            
        if number < 0:
            await interaction.response.send_message(
                "❌ Cannot calculate square root of negative numbers",
                ephemeral=True
            )
            return
            
        result = math.sqrt(number)
        await interaction.response.send_message(
            f"**√{self.format_number(number)} = {self.format_number(result)}**"
        )

    @app_commands.command(name="log", description="Calculate logarithm of a number")
    @app_commands.describe(
        number="Number to calculate logarithm of",
        base="Logarithm base (default: 10)"
    )
    async def log(self, interaction: discord.Interaction, number: float, base: float = 10):
        if not await self.ensure_allowed_channel(interaction):
            return
            
        if number <= 0:
            await interaction.response.send_message(
                "❌ Logarithm is only defined for positive numbers",
                ephemeral=True
            )
            return
        if base <= 0 or base == 1:
            await interaction.response.send_message(
                "❌ Logarithm base must be positive and not equal to 1",
                ephemeral=True
            )
            return
            
        result = math.log(number, base)
        await interaction.response.send_message(
            f"**log<sub>{self.format_number(base)}</sub>({self.format_number(number)}) = {self.format_number(result)}**"
        )

    @app_commands.command(name="factorial", description="Calculate factorial of a number")
    @app_commands.describe(number="Positive integer to calculate factorial of")
    async def factorial(self, interaction: discord.Interaction, number: int):
        if not await self.ensure_allowed_channel(interaction):
            return
            
        if number < 0:
            await interaction.response.send_message(
                "❌ Factorial is only defined for non-negative integers",
                ephemeral=True
            )
            return
        if number > self.max_factorial:
            await interaction.response.send_message(
                f"⚠️ Factorials are limited to {self.max_factorial} to prevent resource abuse",
                ephemeral=True
            )
            return
            
        result = math.factorial(number)
        await interaction.response.send_message(
            f"**{number}! = {result:,}**"  # Format with commas for large numbers
        )

    # --- Algebra ---
    @app_commands.command(name="quadratic", description="Solve quadratic equation: ax² + bx + c = 0")
    @app_commands.describe(a="Coefficient of x²", b="Coefficient of x", c="Constant term")
    async def quadratic(self, interaction: discord.Interaction, a: float, b: float, c: float):
        if not await self.ensure_allowed_channel(interaction):
            return
            
        if a == 0:
            await interaction.response.send_message(
                "❌ Coefficient 'a' cannot be zero (not quadratic)",
                ephemeral=True
            )
            return
            
        discriminant = b**2 - 4*a*c
        if discriminant > 0:
            root1 = (-b + math.sqrt(discriminant)) / (2*a)
            root2 = (-b - math.sqrt(discriminant)) / (2*a)
            response = (
                f"**Equation:** {a}x² + {b}x + {c} = 0\n"
                f"**Discriminant:** {discriminant} (positive, two real roots)\n"
                f"**Roots:** x₁ = {self.format_number(root1)}, x₂ = {self.format_number(root2)}"
            )
        elif discriminant == 0:
            root = -b / (2*a)
            response = (
                f"**Equation:** {a}x² + {b}x + {c} = 0\n"
                f"**Discriminant:** 0 (one real root)\n"
                f"**Root:** x = {self.format_number(root)}"
            )
        else:
            real = -b / (2*a)
            imag = math.sqrt(-discriminant) / (2*a)
            response = (
                f"**Equation:** {a}x² + {b}x + {c} = 0\n"
                f"**Discriminant:** {discriminant} (negative, complex roots)\n"
                f"**Roots:** x₁ = {self.format_number(real)} + {self.format_number(imag)}i, "
                f"x₂ = {self.format_number(real)} - {self.format_number(imag)}i"
            )
            
        await interaction.response.send_message(response)

    # --- Random Numbers ---
    @app_commands.command(name="random", description="Generate a random number in a range")
    @app_commands.describe(
        low="Lower bound",
        high="Upper bound",
        integer="Generate integer? (default: False)",
        count="How many numbers to generate (default: 1)"
    )
    async def random_num(
        self,
        interaction: discord.Interaction,
        low: float,
        high: float,
        integer: bool = False,
        count: app_commands.Range[int, 1, 25] = 1
    ):
        if not await self.ensure_allowed_channel(interaction):
            return
            
        if low >= high:
            await interaction.response.send_message(
                "❌ Lower bound must be less than upper bound",
                ephemeral=True
            )
            return
            
        results = []
        for _ in range(count):
            if integer:
                results.append(str(random.randint(int(low), int(high))))
            else:
                results.append(self.format_number(random.uniform(low, high)))
                
        result_str = ", ".join(results)
        range_type = "integer" if integer else "decimal"
        await interaction.response.send_message(
            f"🔢 Random {range_type} number(s) between {self.format_number(low)} and {self.format_number(high)}:\n"
            f"**{result_str}**"
        )

    # --- Unit Conversion ---
    @app_commands.command(name="convert", description="Convert between common units")
    @app_commands.describe(
        value="Value to convert",
        from_unit="Unit to convert from",
        to_unit="Unit to convert to"
    )
    @app_commands.choices(
        from_unit=[
            app_commands.Choice(name="Celsius", value="c"),
            app_commands.Choice(name="Fahrenheit", value="f"),
            app_commands.Choice(name="Miles", value="mi"),
            app_commands.Choice(name="Kilometers", value="km"),
            app_commands.Choice(name="Pounds", value="lb"),
            app_commands.Choice(name="Kilograms", value="kg")
        ],
        to_unit=[
            app_commands.Choice(name="Fahrenheit", value="f"),
            app_commands.Choice(name="Celsius", value="c"),
            app_commands.Choice(name="Kilometers", value="km"),
            app_commands.Choice(name="Miles", value="mi"),
            app_commands.Choice(name="Kilograms", value="kg"),
            app_commands.Choice(name="Pounds", value="lb")
        ]
    )
    async def convert(
        self,
        interaction: discord.Interaction,
        value: float,
        from_unit: app_commands.Choice[str],
        to_unit: app_commands.Choice[str]
    ):
        if not await self.ensure_allowed_channel(interaction):
            return
            
        unit_map = {
            # Temperature
            ("c", "f"): lambda c: c * 9/5 + 32,
            ("f", "c"): lambda f: (f - 32) * 5/9,
            
            # Distance
            ("mi", "km"): lambda mi: mi * 1.60934,
            ("km", "mi"): lambda km: km / 1.60934,
            
            # Weight
            ("lb", "kg"): lambda lb: lb * 0.453592,
            ("kg", "lb"): lambda kg: kg / 0.453592,
        }
        
        conversion_key = (from_unit.value, to_unit.value)
        if conversion_key in unit_map:
            result = unit_map[conversion_key](value)
            await interaction.response.send_message(
                f"**{self.format_number(value)} {from_unit.name} = "
                f"{self.format_number(result)} {to_unit.name}**"
            )
        else:
            await interaction.response.send_message(
                "❌ Unsupported conversion pair",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(MathCog(bot))
