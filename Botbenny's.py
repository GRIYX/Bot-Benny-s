import discord
from discord.ext import commands
from discord.ui import View, Button
import datetime
import json
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "service_data.json"

HISTORIQUE_CHANNEL_ID = 1337471552182026310  # Remplace par l'ID du salon

# Chargement des données depuis le fichier JSON
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Sauvegarde des données dans le fichier JSON
def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(service_data, f, indent=4)

service_data = load_data()

class ServiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🟢 Prendre son service", style=discord.ButtonStyle.success)
    async def start_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user_id in service_data and service_data[user_id]["end_time"] is None:
            await interaction.response.send_message("🚨 Tu es déjà en service ! Termine-le d'abord.", ephemeral=True)
            return

        service_data[user_id] = {
            "name": interaction.user.name,
            "start_time": now,
            "end_time": None
        }
        save_data()

        await interaction.response.send_message(f"✅ {interaction.user.mention} a commencé son service à {now} !", ephemeral=True)
        await update_history(interaction, new_entry=True)

    @discord.ui.button(label="🔴 Fin de service", style=discord.ButtonStyle.danger)
    async def end_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user_id not in service_data or service_data[user_id]["end_time"] is not None:
            await interaction.response.send_message("⚠️ Tu n'as pas de service en cours.", ephemeral=True)
            return

        service_data[user_id]["end_time"] = now
        save_data()

        await interaction.response.send_message(f"🛑 {interaction.user.mention} a terminé son service à {now} !", ephemeral=True)
        await update_history(interaction)

async def update_history(interaction, new_entry=False):
    """Met à jour l'historique ou crée un NOUVEAU message si un service commence."""
    global history_message
    history_channel = bot.get_channel(HISTORIQUE_CHANNEL_ID)  # Récupération du canal

    if not history_channel:
        await interaction.response.send_message("🚨 Erreur : Canal d'historique introuvable.", ephemeral=True)
        return

    # **Réinitialise l'embed** pour éviter les doublons
    history_embed = discord.Embed(title="📜 Historique des Services", color=discord.Color.blue())

    for user_id, data in service_data.items():
        status = "⏳ En service" if data["end_time"] is None else "✅ Terminé"
        history_embed.add_field(
            name=f"👤 {data['name']}",
            value=f"📅 **Début :** {data['start_time']}\n"
                  f"🕒 **Fin :** {data['end_time'] if data['end_time'] else '🟡 En cours'}\n"
                  f"🔄 **Statut :** {status}",
            inline=False
        )

    # **Correction : Mettre à jour correctement le message**
    if history_message:
        try:
            msg = await history_channel.fetch_message(history_message.id)
            await msg.edit(embed=history_embed)  # Met à jour le message existant
        except discord.NotFound:
            history_message = await history_channel.send(embed=history_embed)  # Recrée le message si introuvable
    else:
        history_message = await history_channel.send(embed=history_embed)  # Crée un nouveau message s'il n'existe pas encore


@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

@bot.command()
async def setup(ctx):
    embed = discord.Embed(title="📢 Gestion des Services", description="Clique sur un bouton ci-dessous pour prendre ou terminer ton service.", color=discord.Color.green())
    await ctx.send(embed=embed, view=ServiceView())

keep_alive()
bot.run(token)
