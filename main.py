import discord
import sqlite3
import os
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LTC_WALLET_ADDRESS = "YOUR_LTC_WALLET_ADDRESS"  # Replace with your LTC wallet address
OWNER_ID = 123456789012345678  # Replace with your Discord ID

bot = commands.Bot(command_prefix=".", intents=discord.Intents.default())

# Connect to SQLite database
conn = sqlite3.connect("points.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS balances (user_id TEXT PRIMARY KEY, points INTEGER)")
conn.commit()

# Function to get user balance
def get_balance(user_id):
    cursor.execute("SELECT points FROM balances WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

# Function to update user balance
def update_balance(user_id, amount):
    if get_balance(user_id) == 0:
        cursor.execute("INSERT INTO balances (user_id, points) VALUES (?, ?)", (user_id, amount))
    else:
        cursor.execute("UPDATE balances SET points = points + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

# Command to check balance
@bot.command()
async def balance(ctx):
    points = get_balance(str(ctx.author.id))
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

    update_balance(str(user.id), amount)
    new_balance = get_balance(str(user.id))
    await ctx.send(f"Added **{amount} points** to {user.mention}. They now have **{new_balance} points**.")

bot.run(TOKEN)
