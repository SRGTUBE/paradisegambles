import discord
import sqlite3
import random
import os
import requests
import time
from discord.ext import commands
from discord.ui import View, Button

# ✅ Load Secrets from Environment Variables
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LTC_ADDRESS = "LLwEzeJYdSA2X3hAZqNy77jN2N2SuPfCNk"
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY")

# ✅ Fixed Intents
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# ✅ Database Setup
conn = sqlite3.connect("points.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS balances (user_id TEXT PRIMARY KEY, points INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS daily_cooldown (user_id TEXT PRIMARY KEY, last_claimed INTEGER)")
conn.commit()


# ✅ Get Balance
def get_balance(user_id):
    cursor.execute("SELECT points FROM balances WHERE user_id = ?", (str(user_id),))
    result = cursor.fetchone()
    return result[0] if result else 0


# ✅ Update Balance
def update_balance(user_id, amount):
    current_balance = get_balance(user_id)
    if current_balance == 0:
        cursor.execute("INSERT INTO balances (user_id, points) VALUES (?, ?)", (str(user_id), amount))
    else:
        cursor.execute("UPDATE balances SET points = points + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()


# ✅ Remove Balance
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


# ✅ Coinbase Payment Link
def create_coinbase_charge(amount_usd, user_id):
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
        "local_price": {"amount": str(amount_usd), "currency": "USD"},
        "metadata": {
            "ltc_address": LTC_ADDRESS,
            "user_id": str(user_id)
        }
    }

    response = requests.post(url, json=data, headers=headers)
    return response.json()


# 🎮 `.balance` Command
@bot.command()
async def balance(ctx):
    balance = get_balance(ctx.author.id)
    await ctx.send(f"💰 **Your Balance:** {balance} Points")


# ➕ `.addpoints` Command (Fixed)
@bot.command()
async def addpoints(ctx, member: discord.Member, amount: int):
    if ctx.author.id in [1101467683083530331, 1106931469928124498]:  # ✅ Your Admin IDs Here
        update_balance(member.id, amount)
        await ctx.send(f"✅ Added {amount} Points to {member.mention}!")
    else:
        await ctx.send("❌ Only bot admins can use this command!")


# ➖ `.removepoints` Command
@bot.command()
async def removepoints(ctx, member: discord.Member, amount: int):
    if ctx.author.id in [1101467683083530331, 1106931469928124498]:
        remove_balance(member.id, amount)
        await ctx.send(f"✅ Removed {amount} Points from {member.mention}!")
    else:
        await ctx.send("❌ Only bot admins can use this command!")


# 🎁 `.daily` Command (Fixed)
@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)
    cursor.execute("SELECT last_claimed FROM daily_cooldown WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    current_time = int(time.time())

    if result:
        last_claimed = result[0]
        cooldown = 86400  # 24 hours in seconds
        if current_time - last_claimed < cooldown:
            remaining_time = cooldown - (current_time - last_claimed)
            hours = remaining_time // 3600
            minutes = (remaining_time % 3600) // 60
            return await ctx.send(f"❌ You've already claimed your daily reward. Try again in **{hours}h {minutes}m**.")

    update_balance(user_id, 2)
    cursor.execute("INSERT OR REPLACE INTO daily_cooldown (user_id, last_claimed) VALUES (?, ?)", (user_id, current_time))
    conn.commit()
    await ctx.send("🎁 **You've claimed your Daily Reward: +2 Points!**")


# 🎰 Blackjack Command (Fixed)
@bot.command()
async def bj(ctx, bet: int):
    balance = get_balance(ctx.author.id)
    if bet > balance:
        return await ctx.send("❌ You don't have enough points!")

    player_hand = random.randint(7, 12)
    bot_hand = random.randint(14, 21)

    if player_hand > bot_hand or bot_hand > 21:
        update_balance(ctx.author.id, bet)
        result = f"🎉 You Won! (+{bet} Points)"
    elif player_hand < bot_hand:
        remove_balance(ctx.author.id, bet)
        result = f"💀 You Lost! (-{bet} Points)"
    else:
        result = f"🤝 It's a Tie!"

    await ctx.send(f"🎰 **Blackjack Game**\n🃏 Your Cards: `{player_hand}`\n🤖 Bot's Cards: `{bot_hand}`\n\n{result}")


# 🪙 Coinflip Command
@bot.command()
async def cf(ctx, bet: int, side: str):
    balance = get_balance(ctx.author.id)
    if bet > balance:
        return await ctx.send("❌ You don't have enough points!")

    side = side.lower()
    if side not in ['heads', 'tails']:
        return await ctx.send("❌ Invalid side! Choose `heads` or `tails`.")

    result = random.choice(['heads', 'tails'])

    if side == result:
        update_balance(ctx.author.id, bet)
        await ctx.send(f"🪙 Coinflip Result: `{result}`\n✅ You Won! (+{bet} Points)")
    else:
        remove_balance(ctx.author.id, bet)
        await ctx.send(f"🪙 Coinflip Result: `{result}`\n❌ You Lost! (-{bet} Points)")


# 🚀 Bot Ready Event
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")


# 🔥 Run the Bot
bot.run(TOKEN)
