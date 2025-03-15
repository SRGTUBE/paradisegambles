import discord
import sqlite3
import random
import os
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Intents
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# Database Setup
conn = sqlite3.connect("points.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS balances (user_id TEXT PRIMARY KEY, points INTEGER)")
conn.commit()


# 📥 Database Functions
def get_balance(user_id):
    cursor.execute("SELECT points FROM balances WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def add_points(user_id, amount):
    if get_balance(user_id) == 0:
        cursor.execute("INSERT INTO balances (user_id, points) VALUES (?, ?)", (user_id, amount))
    else:
        cursor.execute("UPDATE balances SET points = points + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def remove_points(user_id, amount):
    current_balance = get_balance(user_id)
    new_balance = max(0, current_balance - amount)
    cursor.execute("UPDATE balances SET points = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()


# 💎 Help Command
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="💎 Shulker Gambling Bot Commands", color=discord.Color.purple())
    embed.add_field(name=".bj <bet>", value="🎰 Play Blackjack", inline=False)
    embed.add_field(name=".cf <bet> <heads/tails>", value="🪙 Coinflip", inline=False)
    embed.add_field(name=".dice <bet>", value="🎲 Roll Dice", inline=False)
    embed.add_field(name=".mines <bet> <mines_count>", value="💣 Mines Game", inline=False)
    embed.add_field(name=".balance", value="💰 Check your balance", inline=False)
    embed.add_field(name=".addpoints <amount>", value="➕ Add Points", inline=False)
    embed.add_field(name=".removepoints <amount>", value="➖ Remove Points", inline=False)
    await ctx.send(embed=embed)


# 🪙 Coinflip Command
@bot.command()
async def cf(ctx, bet: int, choice: str):
    if choice not in ["heads", "tails"]:
        return await ctx.send("❌ Invalid choice! Choose either `heads` or `tails`.")

    user_id = ctx.author.id
    balance = get_balance(user_id)

    if balance < bet or bet <= 0:
        return await ctx.send("❌ You don't have enough points to bet!")

    remove_points(user_id, bet)
    
    result = random.choice(["heads", "tails"])
    
    if result == choice:
        add_points(user_id, bet * 2)
        await ctx.send(f"✅ You won! 🎉 ({result})")
    else:
        await ctx.send(f"❌ You lost! 😢 ({result})")


# 🎲 Dice Command
@bot.command()
async def dice(ctx, bet: int):
    user_id = ctx.author.id
    balance = get_balance(user_id)

    if balance < bet or bet <= 0:
        return await ctx.send("❌ You don't have enough points to bet!")

    remove_points(user_id, bet)
    
    roll = random.randint(1, 6)

    if roll >= 4:
        add_points(user_id, bet * 2)
        await ctx.send(f"🎲 You rolled `{roll}`! ✅ You won!")
    else:
        await ctx.send(f"🎲 You rolled `{roll}`! ❌ You lost!")


# 💣 Mines Command
@bot.command()
async def mines(ctx, bet: int, mines: int):
    user_id = ctx.author.id
    balance = get_balance(user_id)

    if balance < bet or bet <= 0:
        return await ctx.send("❌ You don't have enough points to bet!")

    if mines < 1 or mines > 24:
        return await ctx.send("❌ You can only select between `1 to 24` mines.")

    remove_points(user_id, bet)

    safe_tiles = 25 - mines
    chance = safe_tiles / 25

    if random.random() <= chance:
        win_amount = int(bet * (1 + (mines * 0.3)))
        add_points(user_id, win_amount)
        await ctx.send(f"💣 You survived the mines and won `{win_amount} Points`! 🎉")
    else:
        await ctx.send("❌ You hit a mine and lost your bet! 💀")


# 🃏 Blackjack Command
@bot.command()
async def bj(ctx, bet: int):
    user_id = ctx.author.id
    balance = get_balance(user_id)

    if balance < bet or bet <= 0:
        return await ctx.send("❌ You don't have enough points to bet!")

    remove_points(user_id, bet)

    view = BlackjackButton(ctx.author, bet)
    embed = discord.Embed(title=f"🃏 Blackjack - {ctx.author.name}", color=discord.Color.gold())
    embed.add_field(name="Your Hand", value=f"{view.player_hand} (Total: {view.calculate_score(view.player_hand)})", inline=False)
    embed.add_field(name="Dealer's Hand", value=f"[{view.dealer_hand[0]}, ?]", inline=False)
    await ctx.send(embed=embed, view=view)


# 💰 Balance Command
@bot.command()
async def balance(ctx):
    user_id = ctx.author.id
    balance = get_balance(user_id)
    await ctx.send(f"💰 Your Balance: {balance} Points")


# ➕ Add Points Command
@bot.command()
async def addpoints(ctx, amount: int):
    user_id = ctx.author.id
    add_points(user_id, amount)
    await ctx.send(f"✅ Successfully added {amount} Points to your balance!")


# ➖ Remove Points Command
@bot.command()
async def removepoints(ctx, amount: int):
    user_id = ctx.author.id
    if get_balance(user_id) < amount:
        await ctx.send("❌ Not enough points to remove!")
    else:
        remove_points(user_id, amount)
        await ctx.send(f"✅ Successfully removed {amount} Points from your balance!")


# ✅ Bot Online Event
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")


bot.run(TOKEN)
