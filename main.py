import discord
import sqlite3
import os
import random
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LTC_WALLET_ADDRESS = "LLwEzeJYdSA2X3hAZqNy77jN2N2SuPfCNkS"
OWNER_ID = 1101467683083530331

# LTC Price (Fixed for now, can be updated via API later)
LTC_PRICE = 80  

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# Database connection
conn = sqlite3.connect("points.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS balances (user_id TEXT PRIMARY KEY, points INTEGER)")
conn.commit()


def get_balance(user_id):
    cursor.execute("SELECT points FROM balances WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0


def update_balance(user_id, amount):
    if get_balance(user_id) == 0:
        cursor.execute("INSERT INTO balances (user_id, points) VALUES (?, ?)", (user_id, amount))
    else:
        cursor.execute("UPDATE balances SET points = points + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()


def remove_balance(user_id, amount):
    current_balance = get_balance(user_id)
    new_balance = max(0, current_balance - amount)
    cursor.execute("UPDATE balances SET points = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    return new_balance


@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")


@bot.command()
async def balance(ctx):
    points = get_balance(str(ctx.author.id))
    await ctx.send(f"{ctx.author.mention}, you have **{points} points**.")


@bot.command()
async def addpoints(ctx, user: discord.Member, amount: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("Only the owner can add points.")
    update_balance(str(user.id), amount)
    await ctx.send(f"Added **{amount} points** to {user.mention}.")


@bot.command()
async def removepoints(ctx, user: discord.Member, amount: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("Only the owner can remove points.")
    new_balance = remove_balance(str(user.id), amount)
    await ctx.send(f"Removed **{amount} points** from {user.mention}. New balance: **{new_balance} points**.")


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


# 🎲 Dice Game
@bot.command()
async def dice(ctx, bet: int):
    balance = get_balance(str(ctx.author.id))
    if bet > balance:
        return await ctx.send("You don't have enough points to bet.")
    
    roll = random.randint(1, 6)
    if roll >= 4:
        update_balance(str(ctx.author.id), bet)
        await ctx.send(f"🎲 You rolled a {roll}! You won **{bet} points**!")
    else:
        remove_balance(str(ctx.author.id), bet)
        await ctx.send(f"🎲 You rolled a {roll}. You lost **{bet} points**.")


# 🃏 Blackjack (Simple)
@bot.command()
async def bj(ctx, bet: int):
    balance = get_balance(str(ctx.author.id))
    if bet > balance:
        return await ctx.send("You don't have enough points to bet.")
    
    player = random.randint(15, 21)
    dealer = random.randint(17, 23)
    
    if player > 21:
        remove_balance(str(ctx.author.id), bet)
        await ctx.send(f"🃏 You busted with {player}. Dealer had {dealer}. You lost **{bet} points**.")
    elif dealer > 21 or player > dealer:
        update_balance(str(ctx.author.id), bet)
        await ctx.send(f"🃏 You had {player}. Dealer had {dealer}. You won **{bet} points**!")
    else:
        remove_balance(str(ctx.author.id), bet)
        await ctx.send(f"🃏 You had {player}. Dealer had {dealer}. You lost **{bet} points**.")


# 💣 Mines (Simple)
@bot.command()
async def mines(ctx, bet: int, mines: int):
    balance = get_balance(str(ctx.author.id))
    if bet > balance:
        return await ctx.send("You don't have enough points to bet.")
    if mines < 1 or mines > 24:
        return await ctx.send("Mines must be between 1 and 24.")

    safe_tiles = 25 - mines
    chance = random.randint(1, 25)

    if chance <= safe_tiles:
        winnings = int(bet * (25 / safe_tiles))
        update_balance(str(ctx.author.id), winnings)
        await ctx.send(f"💣 You avoided the mines and won **{winnings} points**!")
    else:
        remove_balance(str(ctx.author.id), bet)
        await ctx.send(f"💣 You hit a mine and lost **{bet} points**!")


# ✅ Deposit Command (Minimum 0.1$)
@bot.command()
async def deposit(ctx, amount: float):
    if amount < 0.1:
        return await ctx.send("Minimum deposit is **0.1$**.")
    
    ltc_amount = amount / LTC_PRICE
    await ctx.send(
        f"{ctx.author.mention}, send **{ltc_amount:.6f} LTC** to this address:\n"
        f"```{LTC_WALLET_ADDRESS}```\n"
        "After sending, notify the owner for confirmation."
    )


# ✅ Withdrawal Command (Minimum 1$)
@bot.command()
async def withdraw(ctx, amount: float, ltc_address: str):
    if amount < 1:
        return await ctx.send("Minimum withdrawal is **1$**.")
    
    points_required = int(amount * 100)
    balance = get_balance(str(ctx.author.id))

    if points_required > balance:
        return await ctx.send("You don't have enough points.")

    remove_balance(str(ctx.author.id), points_required)

    await ctx.send(
        f"{ctx.author.mention}, your **{amount}$ (in LTC)** will be sent to this address:\n"
        f"```{ltc_address}```\n"
        "The owner will manually process the withdrawal."
    )


# ✅ Custom .help command
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="💎 Gambling Bot Commands", color=discord.Color.blue())
    embed.add_field(name=".balance", value="Check your points balance.", inline=False)
    embed.add_field(name=".deposit <amount>", value="Deposit LTC to get points. (Min 0.1$)", inline=False)
    embed.add_field(name=".withdraw <amount> <LTC address>", value="Withdraw LTC. (Min 1$)", inline=False)
    embed.add_field(name=".dice <bet>", value="Play Dice game.", inline=False)
    embed.add_field(name=".bj <bet>", value="Play Blackjack.", inline=False)
    embed.add_field(name=".mines <bet> <mines>", value="Play Mines.", inline=False)
    embed.add_field(name=".leaderboard", value="Show top players.", inline=False)
    embed.set_footer(text="🔗 Made by SHREYANSH GAMETUBE") 
    await ctx.send(embed=embed)


bot.run(TOKEN)
