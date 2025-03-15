import discord
import sqlite3
import os
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LTC_WALLET_ADDRESS = "LLwEzeJYdSA2X3hAZqNy77jN2N2SuPfCNkS"  # Replace with your LTC wallet address
OWNER_ID = 1101467683083530331  # Replace with your Discord ID

# Intents
intents = discord.Intents.default()
intents.message_content = True  # For reading message content

# Bot
bot = commands.Bot(command_prefix=".", intents=intents)  # Prefix is $

# Connect to SQLite database
conn = sqlite3.connect("points.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS balances (user_id TEXT PRIMARY KEY, points INTEGER)")
conn.commit()


# ✅ When bot is online
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")


# ✅ Error handler
@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"❌ Error: {error}")


# ✅ Get user balance
def get_balance(user_id):
    cursor.execute("SELECT points FROM balances WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0


# ✅ Update user balance
def update_balance(user_id, amount):
    if get_balance(user_id) == 0:
        cursor.execute("INSERT INTO balances (user_id, points) VALUES (?, ?)", (user_id, amount))
    else:
        cursor.execute("UPDATE balances SET points = points + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()


# ✅ Remove balance
def remove_balance(user_id, amount):
    current_balance = get_balance(user_id)
    new_balance = max(0, current_balance - amount)  # Prevent negative balances
    cursor.execute("UPDATE balances SET points = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    return new_balance


# 🎯 Command to check balance
@bot.command()
async def balance(ctx):
    points = get_balance(str(ctx.author.id))
    await ctx.send(f"{ctx.author.mention}, you have **{points} points**.")


# 🎯 Command to deposit (manual confirmation)
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


# 🎯 Admin command to manually add points
@bot.command()
async def addpoints(ctx, user: discord.Member, amount: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("Only the owner can add points.")

    update_balance(str(user.id), amount)
    new_balance = get_balance(str(user.id))
    await ctx.send(f"Added **{amount} points** to {user.mention}. They now have **{new_balance} points**.")


# 🎯 Admin command to manually remove points
@bot.command()
async def removepoints(ctx, user: discord.Member, amount: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("Only the owner can remove points.")

    new_balance = remove_balance(str(user.id), amount)
    await ctx.send(f"Removed **{amount} points** from {user.mention}. They now have **{new_balance} points**.")


# 🎯 Show leaderboard
@bot.command()
async def leaderboard(ctx):
    cursor.execute("SELECT user_id, points FROM balances ORDER BY points DESC LIMIT 10")
    top_users = cursor.fetchall()

    if not top_users:
        return await ctx.send("No leaderboard data available.")

    leaderboard_text = "**🏆 Leaderboard 🏆**\n"
    for rank, (user_id, points) in enumerate(top_users, start=1):
        user = await bot.fetch_user(int(user_id))
        leaderboard_text += f"**{rank}.** {user.mention} → **{points} points**\n"

    await ctx.send(leaderboard_text)


# ✅ Run the bot
bot.run(TOKEN)

