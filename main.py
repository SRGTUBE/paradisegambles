import discord
from discord.ext import commands
import os

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LTC_WALLET_ADDRESS = "YOUR_LTC_WALLET_ADDRESS"  # Replace with your LTC wallet address
OWNER_ID = 123456789012345678  # Replace with your Discord ID

bot = commands.Bot(command_prefix=".", intents=discord.Intents.default())

# Store user balances
balances = {}

# Command to check balance
@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    points = balances.get(user_id, 0)
    await ctx.send(f"{ctx.author.mention}, you have **{points} points**.")

# Command to deposit (manual confirmation)
@bot.command()
async def deposit(ctx, amount: float):
    amount_usd = amount / 100  # Convert points to USD
    ltc_price = 80  # Replace with real-time LTC price if needed
    ltc_amount = amount_usd / ltc_price  # Convert USD to LTC

    await ctx.send(
        f"{ctx.author.mention}, send **{ltc_amount:.6f} LTC** to this address:\n"
        f"```{LTC_WALLET_ADDRESS}```\n"
        "After sending, notify the owner for confirmation."
    )

# Admin command to manually add points
@bot.command()
async def addpoints(ctx, user: discord.Member, amount: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("Only the owner can add points.")
    
    user_id = str(user.id)
    balances[user_id] = balances.get(user_id, 0) + amount
    await ctx.send(f"Added **{amount} points** to {user.mention}. They now have **{balances[user_id]} points**.")

# Run bot
bot.run(TOKEN)
