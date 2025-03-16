import discord
import sqlite3
import random
import os
import requests
from discord.ext import commands
from discord.ui import View, Button

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
# ✅ Fixed Get Balance Function
def get_balance(user_id):
    cursor.execute("SELECT points FROM balances WHERE user_id = ?", (str(user_id),))  # Convert to string here
    result = cursor.fetchone()
    return result[0] if result else 0



# ✅ Fixed Update Balance Function
def update_balance(user_id, amount):
    current_balance = get_balance(user_id)

    if current_balance == 0:
        cursor.execute("INSERT INTO balances (user_id, points) VALUES (?, ?)", (str(user_id), amount))
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


# ➕ `.deposit <amount>` Command
@bot.command()
async def deposit(ctx, amount: int):
    if amount < 10:
        await ctx.send("❌ Minimum deposit is 0.1 USD (10 Points).")
        return
    
    usd_amount = amount / 100  # Convert points to USD
    
    # ✅ Generate Coinbase Payment Link
    ltc_payment_link = create_coinbase_charge(usd_amount, ctx.author.id)

    # ✅ Check if Coinbase API responded properly
    if ltc_payment_link:
        update_balance(ctx.author.id, amount)  # ✅ Add Points to Database
        
        await ctx.send(f"✅ **Deposit {usd_amount}$ worth of LTC to earn {amount} Points!**\n\n**Payment Link:** {ltc_payment_link}")
    
    else:
        await ctx.send("❌ Coinbase API didn't respond properly!")


# bj
@bot.command()
async def bj(ctx, bet: int):
    balance = get_balance(ctx.author.id)
    if bet > balance:
        return await ctx.send("❌ You don't have enough points!")

    player_hand = random.randint(7, 12)
    bot_hand = random.randint(14, 21)

    embed = discord.Embed(title="🎰 Blackjack Game", description=f"🃏 Your Cards: `{player_hand}`\n🤖 Bot's Cards: `Hidden`", color=discord.Color.gold())
    msg = await ctx.send(embed=embed)

    class BlackjackView(View):
        @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
        async def hit(self, interaction: discord.Interaction, button: Button):
            nonlocal player_hand
            card = random.randint(1, 11)
            player_hand += card
            
            if player_hand > 21:
                remove_balance(ctx.author.id, bet)
                await interaction.response.edit_message(embed=discord.Embed(title="🎰 Blackjack", description=f"💀 You Busted with `{player_hand}` Points! -{bet} Points!", color=discord.Color.red()))
                self.stop()
            else:
                embed.description = f"🃏 Your Cards: `{player_hand}`\n🤖 Bot's Cards: `Hidden`"
                await interaction.response.edit_message(embed=embed)

        @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
        async def stand(self, interaction: discord.Interaction, button: Button):
            nonlocal bot_hand
            if player_hand > bot_hand or bot_hand > 21:
                update_balance(ctx.author.id, bet)
                result = f"🎉 You Won! (+{bet} Points)"
            elif player_hand < bot_hand:
                remove_balance(ctx.author.id, bet)
                result = f"💀 You Lost! (-{bet} Points)"
            else:
                result = f"🤝 It's a Tie!"

            final_embed = discord.Embed(title="🎰 Blackjack", description=f"🃏 Your Cards: `{player_hand}`\n🤖 Bot's Cards: `{bot_hand}`\n\n{result}", color=discord.Color.gold())
            await interaction.response.edit_message(embed=final_embed)
            self.stop()

    view = BlackjackView()
    await msg.edit(view=view)

#mines

game_state = {}  # ✅ Store Game State for Each User


class MinesView(View):
    def __init__(self, user_id, bet, mines_count, grid):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.bet = bet
        self.mines_count = mines_count
        self.grid = grid
        self.revealed = set()
        self.profit = 0

        # 🎮 Create 25 Buttons
        for i in range(25):
            button = Button(label=str(i + 1), style=discord.ButtonStyle.gray, custom_id=str(i))
            button.callback = self.button_callback  # ✅ Fix Here
            self.add_item(button)


    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    async def on_timeout(self):
        game_state.pop(self.user_id, None)

    @discord.ui.button(label="💰 Cashout", style=discord.ButtonStyle.green, row=5)
    async def cashout(self, interaction: discord.Interaction, button: Button):
        update_balance(self.user_id, self.profit)
        await interaction.response.edit_message(content=f"✅ **You cashed out with {self.profit} Points! 🎰**", view=None)
        game_state.pop(self.user_id, None)

    @discord.ui.button(label="💥 End Game", style=discord.ButtonStyle.red, row=5)
    async def end_game(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="💥 **You hit a mine and lost your bet! ❌**", view=None)
        game_state.pop(self.user_id, None)

    async def button_callback(self, interaction: discord.Interaction):
        tile_index = int(interaction.data["custom_id"])

        if tile_index in self.revealed:
            return await interaction.response.defer()

        self.revealed.add(tile_index)

        if self.grid[tile_index] == "💣":
            await self.end_game.callback(interaction)

        else:
            self.profit += int(self.bet * 0.5)
            button = [item for item in self.children if item.custom_id == str(tile_index)][0]
            button.style = discord.ButtonStyle.green
            button.label = "💎"
            await interaction.response.edit_message(content=f"✅ Safe Tile! Current Profit: **{self.profit} Points.**\nPress **Cashout** to collect or continue!", view=self)


@bot.command()
async def mines(ctx, bet: int, mines_count: int):
    if bet <= 0 or not (2 <= mines_count <= 24):
        return await ctx.send("❌ Invalid bet or mines count (2-24).")

    user_id = ctx.author.id
    balance = get_balance(user_id)

    if bet > balance:
        return await ctx.send("❌ You don't have enough points.")

    # 💣 Generate Grid
    grid = ["💎"] * 25
    mine_positions = random.sample(range(25), mines_count)

    for pos in mine_positions:
        grid[pos] = "💣"

    # ✅ Remove Points from User's Balance
    remove_balance(user_id, bet)

    # 🎮 Store Game State
    game_state[user_id] = {
        "grid": grid,
        "revealed": set(),
        "bet": bet,
        "mines_count": mines_count,
        "profit": 0,
    }

    view = MinesView(user_id, bet, mines_count, grid)
    await ctx.send("💣 **Mines Game Started!**\nClick on tiles to reveal. Avoid the mines!", view=view)

#dice

@bot.command()
async def dice(ctx, bet: int):
    balance = get_balance(ctx.author.id)
    if bet > balance:
        return await ctx.send("❌ You don't have enough points!")

    player_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)

    if player_roll > bot_roll:
        update_balance(ctx.author.id, bet)
        await ctx.send(f"🎲 **You Rolled {player_roll} | Bot Rolled {bot_roll} - 🎉 You Won +{bet} Points!**")
    elif player_roll < bot_roll:
        remove_balance(ctx.author.id, bet)
        await ctx.send(f"🎲 **You Rolled {player_roll} | Bot Rolled {bot_roll} - 💀 You Lost -{bet} Points!**")
    else:
        await ctx.send(f"🎲 **It's a Tie! Both Rolled {player_roll} 🎮**")

#cf

@bot.command()
async def cf(ctx, bet: int, side: str):
    balance = get_balance(ctx.author.id)
    if bet > balance:
        return await ctx.send("❌ You don't have enough points!")

    # ✅ Normalize Input for Head/Tail
    side = side.lower()
    if side in ['h', 'head', 'heads']:
        side = 'heads'
    elif side in ['t', 'tail', 'tails']:
        side = 'tails'
    else:
        return await ctx.send("❌ Invalid side! Choose `heads` or `tails`.")

    # 🎯 Random Coinflip
    result = random.choice(['heads', 'tails'])

    # 🎉 Check Win or Lose
    if side == result:
        update_balance(ctx.author.id, bet)
        await ctx.send(f"🪙 Coinflip Result: `{result}`\n✅ You Won! +{bet} Points")
    else:
        remove_balance(ctx.author.id, bet)
        await ctx.send(f"🪙 Coinflip Result: `{result}`\n❌ You Lost! -{bet} Points")



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
    embed = discord.Embed(title="💎 Paradise Gambles Bot Commands", color=discord.Color.gold())
    embed.add_field(name=".bj <bet>", value="🎰 Play Blackjack", inline=False)
    embed.add_field(name=".cf <bet> <choice>", value="🪙 Coinflip", inline=False)
    embed.add_field(name=".dice <bet>", value="🎲 Roll Dice", inline=False)
    embed.add_field(name=".mines <bet> <mines_count>", value="💣 Mines Game", inline=False)
    embed.add_field(name=".balance", value="💰 Check your balance", inline=False)
    embed.add_field(name=".daily", value="🎁 Claim Daily +2 Points", inline=False)
    embed.add_field(name=".deposit <amount>", value="➕ Deposit LTC to get Points", inline=False)
    embed.add_field(name=".withdraw <amount>", value="➖ Withdraw Points to LTC", inline=False)
    embed.add_field(name=".addpoints <@user> <amount>", value="➕ Add Points to User (Admin Only)", inline=False)
    embed.add_field(name=".removepoints <@user> <amount>", value="➖ Remove Points from User (Admin Only)", inline=False)
    await ctx.send(embed=embed)



ADMIN_IDS = [1101467683083530331, 1106931469928124498]  # ✅ Your Admin IDs Here

# ✅ Fixed .setbalance Command
# ✅ .addpoints Command (Only Admins)

@bot.command()
async def removepoints(ctx, member: discord.Member, amount: int):
    if ctx.author.id in ADMIN_IDS:
        remove_balance(member.id, amount)
        await ctx.send(f"✅ Removed {amount} Points from {member.mention}!")
    else:
        await ctx.send("❌ Only bot admins can use this command!")

@bot.command()
async def addpoints(ctx, member: discord.Member, amount: int):
    if ctx.author.id in ADMIN_IDS:
        update_balance(member.id, amount)
        await ctx.send(f"✅ Added {amount} Points to {member.mention}!")
    else:
        await ctx.send("❌ Only bot admins can use this command!")

# ✅ Daily Cooldown Table (At the top with other database stuff)
cursor.execute("CREATE TABLE IF NOT EXISTS daily_cooldown (user_id TEXT PRIMARY KEY, last_claimed INTEGER)")
conn.commit()

# ✅ .daily Command (Paste Here)
import time

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)

    # ✅ Check if user has claimed before
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
            return await ctx.send(f"❌ You already claimed your daily reward! ⏳ Try again in **{hours}h {minutes}m**.")

    # ✅ Add 2 Points to Balance
    update_balance(user_id, 2)

    # ✅ Update Last Claimed Time in Database
    cursor.execute("INSERT OR REPLACE INTO daily_cooldown (user_id, last_claimed) VALUES (?, ?)", (user_id, current_time))
    conn.commit()
    
    await ctx.send("🎁 **You've claimed your Daily Reward: +2 Points!**")

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")


bot.run(TOKEN)
