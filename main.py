import discord
import sqlite3
import random
import os
import requests
from discord.ext import commands

# ✅ Load Secrets from Environment Variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN") 
LTC_ADDRESS = "LLwEzeJYdSA2X3hAZqNy77jN2N2SuPfCNk" 
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY")

# Fixed Intents
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# Database setup
conn = sqlite3.connect("points.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS balances (user_id TEXT PRIMARY KEY, points INTEGER)")
conn.commit()

# ✅ Balance Functions
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


# ✅ Convert USD to LTC
def usd_to_ltc(usd):
    response = requests.get("https://api.coinbase.com/v2/exchange-rates?currency=LTC")
    rate = float(response.json()["data"]["rates"]["USD"])
    return round(usd / rate, 8)


# ✅ Generate LTC Payment Link using Coinbase API
def create_coinbase_charge(amount_usd):
    url = "https://api.commerce.coinbase.com/charges"
    headers = {
        "Content-Type": "application/json",
        "X-CC-Api-Key": COINBASE_API_KEY,
        "X-CC-Version": "2018-03-22"
    }
    data = {
        "name": "Shulker Gambling Deposit",
        "description": "Deposit to Shulker Gambling Bot",
        "pricing_type": "fixed_price",
        "local_price": {"amount": amount_usd, "currency": "USD"},
        "metadata": {"ltc_address": LTC_ADDRESS}
    }

    response = requests.post(url, json=data, headers=headers)
    return response.json()["data"]["hosted_url"]


# ➕ `.deposit <amount>` Command
@bot.command()
async def deposit(ctx, amount: int):
    if amount < 10:
        await ctx.send("❌ Minimum deposit is 0.1 USD (10 Points).")
        return
    
    usd_amount = amount / 100  # Convert points to USD
    ltc_payment_link = create_coinbase_charge(usd_amount)
    
    await ctx.send(f"✅ **Deposit {usd_amount}$ worth of LTC to earn {amount} Points!**\n\n**Payment Link:** {ltc_payment_link}")



# ➖ `.withdraw <amount>` Command
@bot.command()
async def withdraw(ctx, amount: int):
    if amount < 100:
        return await ctx.send("❌ Minimum withdrawal is 1 USD (100 Points).")
    
    user_id = ctx.author.id
    balance = get_balance(user_id)

    if balance < amount:
        return await ctx.send("❌ Not enough points to withdraw!")

    usd_amount = amount / 100
    ltc_amount = usd_to_ltc(usd_amount)
    remove_balance(user_id, amount)
    
    await ctx.send(f"✅ Successfully withdrawn {usd_amount}$ ({ltc_amount} LTC) to your LTC wallet!")

# 💰 Check Balance
@bot.command()
async def balance(ctx):
    user_id = ctx.author.id
    balance = get_balance(user_id)
    await ctx.send(f"💰 Your Balance: {balance} Points")

# 💎 Help Command
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="💎 Shulker Gambling Bot Commands", color=discord.Color.gold())
    embed.add_field(name=".bj <bet>", value="🎰 Play Blackjack", inline=False)
    embed.add_field(name=".cf <bet> <heads/tails>", value="🪙 Coinflip", inline=False)
    embed.add_field(name=".dice <bet>", value="🎲 Roll Dice", inline=False)
    embed.add_field(name=".mines <bet> <mines_count>", value="💣 Mines Game", inline=False)
    embed.add_field(name=".balance", value="💰 Check your balance", inline=False)
    embed.add_field(name=".deposit <amount>", value="➕ Deposit LTC to get Points", inline=False)
    embed.add_field(name=".withdraw <amount>", value="➖ Withdraw Points to LTC", inline=False)
    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")

bot.run(TOKEN)
