import discord
from discord.ext import commands
from discord.ui import View, Button
import datetime
import json
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

# Chargement des variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Configuration des permissions du bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID du salon d'historique (à remplacer par le bon ID)
HISTORIQUE_CHANNEL_ID = 1337471552182026310

# Fichier de sauvegarde des services
SERVICE_FILE = "services.json"

# Chargement des données de service sauvegardées
def load_services():
    if os.path.exists(SERVICE_FILE):
        with open(SERVICE_FILE, "r") as f:
            return json.load(f)
    return {}

# Sauvegarde des services en cours
def save_services():
    with open(SERVICE_FILE, "w") as f:
        json.dump(service_data, f, indent=4)

# Données des services
service_data = load_services()


class ServiceView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🟢 Prendre son service", style=discord.ButtonStyle.success)
    async def start_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)  # Stocker l'ID en tant que string
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user_id in service_data and service_data[user_id]["end_time"] is None:
            await interaction.response.send_message("🚨 Tu es déjà en service ! Termine-le d'abord.", ephemeral=True)
            return

        service_data[user_id] = {
            "name": interaction.user.name,
            "start_time": now,
            "end_time": None
        }

        save_services()  # Sauvegarde des services après modification

        await interaction.response.send_message(f"✅ {interaction.user.mention} a commencé son service à {now} !", ephemeral=True)
        await log_service(interaction, user_id)

    @discord.ui.button(label="🔴 Fin de service", style=discord.ButtonStyle.danger)
    async def end_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user_id not in service_data or service_data[user_id]["end_time"] is not None:
            await interaction.response.send_message("⚠️ Tu n'as pas de service en cours.", ephemeral=True)
            return

        service_data[user_id]["end_time"] = now
        save_services()  # Sauvegarde des services après modification

        await interaction.response.send_message(f"🛑 {interaction.user.mention} a terminé son service à {now} !", ephemeral=True)
        await log_service(interaction, user_id)


async def log_service(interaction, user_id):
    """Enregistre un service dans l'historique sous forme d'un message séparé."""
    history_channel = bot.get_channel(HISTORIQUE_CHANNEL_ID)

    if not history_channel:
        await interaction.response.send_message("🚨 Erreur : Canal d'historique introuvable.", ephemeral=True)
        return

    data = service_data[user_id]
    status = "⏳ En service" if data["end_time"] is None else "✅ Terminé"

    history_embed = discord.Embed(title="📜 Historique des Services", color=discord.Color.blue())
    history_embed.add_field(
        name=f"👤 {data['name']}",
        value=f"📅 **Début :** {data['start_time']}\n"
              f"🕒 **Fin :** {data['end_time'] if data['end_time'] else '🟡 En cours'}\n"
              f"🔄 **Statut :** {status}",
        inline=False
    )

    await history_channel.send(embed=history_embed)


@bot.command()
async def temps_service(ctx, membre: discord.Member = None):
    """Affiche le temps total passé en service pour un joueur"""
    if membre is None:
        membre = ctx.author

    user_id = str(membre.id)

    if user_id not in service_data:
        await ctx.send(f"❌ {membre.mention} n'a jamais pris de service.")
        return

    start_time = datetime.datetime.strptime(service_data[user_id]["start_time"], "%Y-%m-%d %H:%M:%S")
    end_time_str = service_data[user_id]["end_time"]

    if end_time_str:
        end_time = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        total_time = end_time - start_time
    else:
        total_time = datetime.datetime.now() - start_time

    heures, reste = divmod(total_time.seconds, 3600)
    minutes, secondes = divmod(reste, 60)

    await ctx.send(f"🕒 {membre.mention} a été en service pendant {heures}h {minutes}m {secondes}s.")


@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, *, message: str):
    """Envoie un message avec le bot"""
    await ctx.message.delete()
    await ctx.send(message)


@bot.command()
async def setup(ctx):
    """Commande pour créer le message avec les boutons dans le salon actuel"""
    embed = discord.Embed(
        title="📢 Gestion des Services",
        description="Clique sur un bouton ci-dessous pour prendre ou terminer ton service.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=ServiceView())


@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

    # Ajout automatique des boutons sur un message déjà existant (optionnel)
    for guild in bot.guilds:
        for channel in guild.text_channels:
            async for message in channel.history(limit=50):
                if message.author == bot.user and message.embeds:
                    await message.edit(view=ServiceView())
                    print("✅ Boutons restaurés sur un message existant")
                    return

    print("⚠ Aucun message trouvé, utilise !setup pour recréer les boutons.")


keep_alive()
bot.run(TOKEN)
