import discord
import sqlite3
import random
import os
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

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


# 🎰 Blackjack Button Class
class BlackjackButton(discord.ui.View):
    def __init__(self, player, bet):
        super().__init__()
        self.player = player
        self.bet = bet
        self.deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        random.shuffle(self.deck)
        self.player_hand = [self.draw_card(), self.draw_card()]
        self.dealer_hand = [self.draw_card(), self.draw_card()]

    def draw_card(self):
        return self.deck.pop()

    def calculate_score(self, hand):
        score = sum(hand)
        aces = hand.count(11)
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    async def update_embed(self, interaction):
        embed = discord.Embed(title=f"🃏 Blackjack - {self.player.name}", color=discord.Color.gold())
        embed.add_field(name="Your Hand", value=f"{self.player_hand} (Total: {self.calculate_score(self.player_hand)})", inline=False)
        embed.add_field(name="Dealer's Hand", value=f"[{self.dealer_hand[0]}, ?]", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.player:
            return await interaction.response.send_message("You are not playing this game!", ephemeral=True)
        
        self.player_hand.append(self.draw_card())
        player_score = self.calculate_score(self.player_hand)
        
        if player_score > 21:
            await self.end_game(interaction, "❌ You Busted! Dealer Wins!", False)
        else:
            await self.update_embed(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.player:
            return await interaction.response.send_message("You are not playing this game!", ephemeral=True)
        
        while self.calculate_score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.draw_card())
        
        player_score = self.calculate_score(self.player_hand)
        dealer_score = self.calculate_score(self.dealer_hand)
        
        if dealer_score > 21 or player_score > dealer_score:
            await self.end_game(interaction, "🎉 You Win!", True)
        elif player_score < dealer_score:
            await self.end_game(interaction, "❌ Dealer Wins!", False)
        else:
            await self.end_game(interaction, "🤝 It's a Tie!", None)

    async def end_game(self, interaction, result, player_won):
        self.clear_items()
        embed = discord.Embed(title=f"🃏 Blackjack - {self.player.name}", color=discord.Color.gold())
        embed.add_field(name="Your Hand", value=f"{self.player_hand} (Total: {self.calculate_score(self.player_hand)})", inline=False)
        embed.add_field(name="Dealer's Hand", value=f"{self.dealer_hand} (Total: {self.calculate_score(self.dealer_hand)})", inline=False)
        embed.add_field(name="Result", value=result, inline=False)
        await interaction.response.edit_message(embed=embed, view=None)

        if player_won:
            update_balance(self.player.id, self.bet * 2)  
        elif player_won is False:
            remove_balance(self.player.id, self.bet)  
        else:
            update_balance(self.player.id, self.bet)  


@bot.command()
async def bj(ctx, bet: int):
    user_id = ctx.author.id
    balance = get_balance(user_id)

    if balance < bet or bet <= 0:
        return await ctx.send("❌ You don't have enough points to bet!")

    # Deduct bet from user's balance
    remove_balance(user_id, bet)

    # Start Blackjack Game
    view = BlackjackButton(ctx.author, bet)
    embed = discord.Embed(title=f"🃏 Blackjack - {ctx.author.name}", color=discord.Color.gold())
    embed.add_field(name="Your Hand", value=f"{view.player_hand} (Total: {view.calculate_score(view.player_hand)})", inline=False)
    embed.add_field(name="Dealer's Hand", value=f"[{view.dealer_hand[0]}, ?]", inline=False)
    await ctx.send(embed=embed, view=view)


@bot.command()
async def balance(ctx):
    user_id = ctx.author.id
    balance = get_balance(user_id)
    await ctx.send(f"💰 Your Balance: {balance} Points")


@bot.command()
async def deposit(ctx, amount: int):
    user_id = ctx.author.id
    update_balance(user_id, amount)
    await ctx.send(f"✅ Successfully added {amount} Points to your balance!")


@bot.command()
async def withdraw(ctx, amount: int):
    user_id = ctx.author.id
    if get_balance(user_id) < amount:
        await ctx.send("❌ Not enough points to withdraw!")
    else:
        remove_balance(user_id, amount)
        await ctx.send(f"✅ Successfully withdrawn {amount} Points from your balance!")


@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")


bot.run(TOKEN)
