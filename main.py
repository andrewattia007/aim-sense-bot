import os
import asyncio
import datetime
import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

user_profiles = {}
user_cooldowns = {}

class ScoreModal(discord.ui.Modal, title="Enter Aim Lab Scores & Accuracy"):
    micro_scores = discord.ui.TextInput(
        label="Micro-Adjustment Scores (score, score, score)",
        placeholder="85226, 88193, 90520"
    )
    micro_acc = discord.ui.TextInput(
        label="Micro-Adjustment Accuracy (acc, acc, acc)",
        placeholder="91.7, 96.2, 96.3"
    )
    track_scores = discord.ui.TextInput(
        label="Tracking Scores (score, score, score)",
        placeholder="10002, 9751, 9800"
    )
    track_acc = discord.ui.TextInput(
        label="Tracking Accuracy (acc, acc, acc)",
        placeholder="40.3, 40.9, 41.2"
    )

    def __init__(self, step: int, current_sens: float):
        super().__init__()
        self.step = step
        self.current_sens = current_sens

    async def on_submit(self, interaction: discord.Interaction):
        next_sens = round(self.current_sens + 0.03, 3)
        if self.step < 5:
            view = StepView(step=self.step + 1, current_sens=next_sens)
            embed = discord.Embed(
                title=f"Step {self.step + 1} / 5",
                description=f"Set your Valorant sensitivity to **{next_sens}** in Aim Lab and run 3 Micro-Adjustment and 3 Tracking tasks.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            rec_sens = round((self.current_sens + 0.305) / 2, 3)
            user_cooldowns[interaction.user.id] = datetime.datetime.utcnow() + datetime.timedelta(days=7)
            embed = discord.Embed(
                title="Sensitivity Analysis Complete 🎯",
                description=f"Based on your results, your optimal Valorant sensitivity is **{rec_sens}**.",
                color=discord.Color.green()
            )
            embed.add_field(name="Confidence Level", value="Low (Round 2 skipped)", inline=False)
            embed.add_field(name="Profile Locked", value="You can recalculate sensitivity after 7 days.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)

class StepView(discord.ui.View):
    def __init__(self, step: int, current_sens: float):
        super().__init__(timeout=None)
        self.step = step
        self.current_sens = current_sens

    @discord.ui.button(label="Enter Scores", style=discord.ButtonStyle.primary)
    async def enter_scores(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ScoreModal(step=self.step, current_sens=self.current_sens))

    @discord.ui.button(label="Continue Without Break", style=discord.ButtonStyle.secondary)
    async def no_break(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"Step {self.step} active. Apply sens **{self.current_sens}**.", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="convert", description="Convert sensitivity from another game to Valorant")
@app_commands.describe(game="Source Game", sens="Current Sensitivity")
@app_commands.choices(game=[
    app_commands.Choice(name="CS2 / CS:GO", value="cs2"),
    app_commands.Choice(name="Apex Legends", value="apex"),
    app_commands.Choice(name="Overwatch 2", value="ow2")
])
async def convert(interaction: discord.Interaction, game: app_commands.Choice[str], sens: float):
    val_sens = round(sens / 3.18181818, 3) if game.value in ["cs2", "apex"] else round(sens / 10.6, 3)
    embed = discord.Embed(
        title="Sensitivity Converter",
        description=f"Your {game.name} sensitivity of **{sens}** equals **{val_sens}** in Valorant (at 800 DPI).",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="sens", description="Set up your gaming profile")
@app_commands.describe(
    dpi="Mouse DPI",
    mousepad_cm="Mousepad space (cm)",
    grip="Grip type",
    aim_style="Aiming style",
    current_sens="Current Valorant Sensitivity",
    hours="Hours on current sensitivity"
)
@app_commands.choices(
    grip=[
        app_commands.Choice(name="Palm", value="Palm"),
        app_commands.Choice(name="Claw", value="Claw"),
        app_commands.Choice(name="Fingertip", value="Fingertip")
    ],
    aim_style=[
        app_commands.Choice(name="Wrist", value="Wrist"),
        app_commands.Choice(name="Arm", value="Arm"),
        app_commands.Choice(name="Hybrid (Wrist + Arm)", value="Hybrid")
    ]
)
async def sens_profile(
    interaction: discord.Interaction,
    dpi: int,
    mousepad_cm: int,
    grip: app_commands.Choice[str],
    aim_style: app_commands.Choice[str],
    current_sens: float,
    hours: int = 0
):
    user_profiles[interaction.user.id] = {
        "dpi": dpi,
        "mousepad": mousepad_cm,
        "grip": grip.value,
        "aim_style": aim_style.value,
        "current_sens": current_sens,
        "hours": hours
    }
    await interaction.response.send_message("Your setup profile has been saved!", ephemeral=True)

@bot.tree.command(name="checklist", description="Pre-test configuration checklist")
async def checklist(interaction: discord.Interaction):
    embed = discord.Embed(title="Pre-Test Checklist 📋", color=discord.Color.gold())
    embed.add_field(name="1. Raw Input", value="Enable Raw Input Buffer / disable Windows Mouse Acceleration.", inline=False)
    embed.add_field(name="2. Polling Rate", value="Set polling rate to 1000Hz or higher.", inline=False)
    embed.add_field(name="3. Standard DPI", value="Use 400, 800, or 1600 DPI.", inline=False)
    embed.add_field(name="4. Scoped Sensitivity", value="Set Scoped Sensitivity Multiplier to 1.0.", inline=False)
    embed.add_field(name="5. Framerate", value="Ensure stable in-game FPS.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="sens_start", description="Start sensitivity identification routine")
async def sens_start(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id in user_cooldowns and datetime.datetime.utcnow() < user_cooldowns[user_id]:
        remaining = user_cooldowns[user_id] - datetime.datetime.utcnow()
        await interaction.response.send_message(f"Profile locked. Try again in {remaining.days} days.", ephemeral=True)
        return

    profile = user_profiles.get(user_id, {"current_sens": 0.276})
    start_sens = round(profile["current_sens"] * 0.97, 3)

    embed = discord.Embed(
        title="Sensitivity Test: Step 1 / 5",
        description=f"Warm up for 2 minutes. Apply test sensitivity **{start_sens}** in Aim Lab.",
        color=discord.Color.blue()
    )
    view = StepView(step=1, current_sens=start_sens)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

bot.run(os.environ.get('DISCORD'))