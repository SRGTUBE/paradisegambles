import discord
import sqlite3
import random
import os
import requests
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LTC_ADDRESS = "YOUR_LTC_WALLET_ADDRESS"  # Your LTC Wallet Address
COINBASE_API_KEY = "YOUR_COINBASE_API_KEY"  # Coinbase API Key

# Fixed Intents
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# Database setup
conn = sqlite3.connect("points.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS balances (user_id TEXT PRIMARY KEY, points INTEGER)")
conn.commit()


# Balance Functions...
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


# 🎰 Blackjack Command
@bot.command()
async def bj(ctx, bet: int):
    user_id = ctx.author.id
    balance = get_balance(user_id)

    if balance < bet or bet <= 0:
        return await ctx.send("❌ You don't have enough points to bet!")

    remove_balance(user_id, bet)

    roll = random.randint(1, 10)
    if roll >= 6:
        update_balance(user_id, bet * 2)
        await ctx.send(f"🎰 You won {bet * 2} points!")
    else:
        await ctx.send(f"🎰 You lost {bet} points!")


# 🎲 Dice Command
@bot.command()
async def dice(ctx, bet: int):
    user_id = ctx.author.id
    balance = get_balance(user_id)

    if balance < bet or bet <= 0:
        return await ctx.send("❌ You don't have enough points to bet!")

    roll = random.randint(1, 6)
    if roll >= 4:
        update_balance(user_id, bet * 2)
        await ctx.send(f"🎲 You rolled {roll} and won {bet * 2} points!")
    else:
        remove_balance(user_id, bet)
        await ctx.send(f"🎲 You rolled {roll} and lost {bet} points!")


# 💣 Mines Command
@bot.command()
async def mines(ctx, bet: int, mines: int):
    await ctx.send("💣 Mines game coming soon!")


# 💰 Check Balance
@bot.command()
async def balance(ctx):
    user_id = ctx.author.id
    balance = get_balance(user_id)
    await ctx.send(f"💰 Your Balance: {balance} Points")


# ➕ Deposit Command
@bot.command()
async def deposit(ctx, amount: int):
    if amount < 10:
        return await ctx.send("❌ Minimum deposit is 0.1 USD (10 Points).")
    update_balance(ctx.author.id, amount)
    await ctx.send(f"✅ Successfully added {amount} Points to your balance!")


# ➖ Withdraw Command (Sends LTC to your LTC wallet)
@bot.command()
async def withdraw(ctx, amount: int):
    if amount < 100:
        return await ctx.send("❌ Minimum withdrawal is 1 USD (100 Points).")
    
    user_id = ctx.author.id
    balance = get_balance(user_id)

    if balance < amount:
        return await ctx.send("❌ Not enough points to withdraw!")

    # Calculate LTC amount
    usd_amount = amount / 100
    ltc_amount = usd_to_ltc(usd_amount)

    # Send LTC to your wallet using Coinbase API
    result = send_ltc(ltc_amount)

    if result:
        remove_balance(user_id, amount)
        await ctx.send(f"✅ Successfully withdrawn {usd_amount}$ ({ltc_amount} LTC) to your LTC address!")
    else:
        await ctx.send("❌ LTC transaction failed!")


# 💎 Help Command
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="💎 Shulker Gambling Bot Commands", color=discord.Color.gold())
    embed.add_field(name=".bj <bet>", value="🎰 Play Blackjack", inline=False)
    embed.add_field(name=".cf <bet> <heads/tails>", value="🪙 Coinflip", inline=False)
    embed.add_field(name=".dice <bet>", value="🎲 Roll Dice", inline=False)
    embed.add_field(name=".mines <bet> <mines_count>", value="💣 Mines Game", inline=False)
    embed.add_field(name=".balance", value="💰 Check your balance", inline=False)
    embed.add_field(name=".deposit <amount>", value="➕ Add Points", inline=False)
    embed.add_field(name=".withdraw <amount>", value="➖ Withdraw Points (LTC)", inline=False)
    await ctx.send(embed=embed)


# ✅ Function to Convert USD to LTC
def usd_to_ltc(usd):
    response = requests.get("https://api.coinbase.com/v2/exchange-rates?currency=LTC")
    rate = float(response.json()["data"]["rates"]["USD"])
    return round(usd / rate, 8)


# ✅ Function to Send LTC to Your Wallet via Coinbase API
def send_ltc(amount):
    url = "https://api.commerce.coinbase.com/charges"
    headers = {
        "Content-Type": "application/json",
        "X-CC-Api-Key": COINBASE_API_KEY,
        "X-CC-Version": "2018-03-22"
    }
    data = {
        "name": "Shulker Gambling Bot Withdrawal",
        "description": "LTC Withdrawal",
        "pricing_type": "fixed_price",
        "local_price": {"amount": amount, "currency": "LTC"},
        "redirect_url": "https://discord.gg/shulker",
        "cancel_url": "https://discord.gg/shulker",
        "metadata": {"wallet_address": LTC_ADDRESS}
    }

    response = requests.post(url, json=data, headers=headers)
    return response.status_code == 201


@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")


bot.run(TOKEN)
