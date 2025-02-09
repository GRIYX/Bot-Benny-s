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

service_data = {}  # Dictionnaire pour stocker les heures de service
history_message = None  # ID du message d'historique

HISTORIQUE_CHANNEL_ID = 1337471552182026310  # Remplace par l'ID du salon


class ServiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🟢 Prendre son service", style=discord.ButtonStyle.success)
    async def start_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Vérifie si l'utilisateur est déjà en service et n'a pas terminé
        if user_id in service_data and service_data[user_id]["end_time"] is None:
            await interaction.response.send_message("🚨 Tu es déjà en service ! Termine-le d'abord.", ephemeral=True)
            return

            if user_id not in service_data:
            service_data[user_id] = []
    
            service_data[user_id].append({
            "start_time": now,
            "end_time": None
            })


        await interaction.response.send_message(f"✅ {interaction.user.mention} a commencé son service à {now} !", ephemeral=True)
        await update_history(interaction, new_entry=True)  # Nouveau message à chaque début de service

    @discord.ui.button(label="🔴 Fin de service", style=discord.ButtonStyle.danger)
    async def end_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Vérifie si l'utilisateur a bien un service en cours
        if user_id not in service_data or service_data[user_id]["end_time"] is not None:
            await interaction.response.send_message("⚠️ Tu n'as pas de service en cours.", ephemeral=True)
            return

        # Met à jour la fin du service
        service_data[user_id][-1]["end_time"] = now

        await interaction.response.send_message(f"🛑 {interaction.user.mention} a terminé son service à {now} !", ephemeral=True)
        await update_history(interaction)  # Mise à jour de l'historique


async def update_history(interaction, new_entry=False):
    """Met à jour l'historique ou crée un NOUVEAU message si un service commence."""
    global history_message
    history_channel = bot.get_channel(HISTORIQUE_CHANNEL_ID)  # Récupération du canal

    if not history_channel:
        await interaction.response.send_message("🚨 Erreur : Canal d'historique introuvable.", ephemeral=True)
        return

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

    if new_entry or not history_message:  # Nouveau message si un service commence
        history_message = await history_channel.send(embed=history_embed)
    else:
        try:
            msg = await history_channel.fetch_message(history_message.id)
            await msg.edit(embed=history_embed)  # Mise à jour de l'ancien message
        except:
            history_message = await history_channel.send(embed=history_embed)  # Si erreur, recrée un message



    # Vérifie si on a un message existant pour l'historique
    if history_message:
        try:
            msg = await history_channel.fetch_message(history_message.id)
            await msg.edit(embed=history_embed)  # Mise à jour du message
        except:
            history_message = await history_channel.send(embed=history_embed)  # Si erreur, recrée le message
    else:
        history_message = await history_channel.send(embed=history_embed)


SETUP_MESSAGE_FILE = "setup_message.json"

def save_message_ids(setup_message_id, history_message_id):
    data = {"setup_message_id": setup_message_id, "history_message_id": history_message_id}
    with open(SETUP_MESSAGE_FILE, "w") as f:
        json.dump(data, f)

def load_message_ids():
    if os.path.exists(SETUP_MESSAGE_FILE):
        with open(SETUP_MESSAGE_FILE, "r") as f:
            return json.load(f)
    return {"setup_message_id": None, "history_message_id": None}


@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

    # Charger les IDs des messages sauvegardés
    message_ids = load_message_ids()
    setup_message_id = message_ids["setup_message_id"]

    if setup_message_id:
        for guild in bot.guilds:
            for channel in guild.text_channels:
                try:
                    msg = await channel.fetch_message(setup_message_id)
                    await msg.edit(view=ServiceView())  # Réassocie les boutons
                    print("✅ Message des services récupéré avec succès !")
                    return
                except:
                    pass  # Ignore les erreurs si le message n'est pas trouvé

    print("⚠ Aucun message trouvé, utilise !setup pour recréer les boutons.")

@bot.command()
async def service_time(ctx, member: discord.Member = None):
    """Affiche le temps total passé en service par un utilisateur."""
    member = member or ctx.author  # Si aucun membre n'est spécifié, prend l'auteur
    user_id = member.id

    if user_id not in service_data:
        await ctx.send(f"❌ {member.mention} n'a aucun service enregistré.")
        return

    total_duration = datetime.timedelta()  # Initialise un temps total à 0

    for session in service_data[user_id]:  # Parcours toutes les sessions
        start_time = datetime.datetime.strptime(session["start_time"], "%Y-%m-%d %H:%M:%S")
        end_time = session["end_time"]

        if end_time:  # Vérifie si le service est terminé
            end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            total_duration += (end_time - start_time)

    # Convertit en heures, minutes et secondes
    hours, remainder = divmod(total_duration.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)

    await ctx.send(f"⏳ {member.mention} a passé un total de **{int(hours)}h {int(minutes)}m {int(seconds)}s** en service.")


@bot.command()
async def temps_service(ctx, membre: discord.Member = None):
    """Affiche le temps total passé en service pour un joueur"""
    if membre is None:
        membre = ctx.author  # Si aucun joueur n'est mentionné, on prend l'auteur

    user_id = membre.id

    if user_id not in service_data:
        await ctx.send(f"❌ {membre.mention} n'a jamais pris de service.")
        return

    for session in service_data[user_id]:  
    start_time = datetime.datetime.strptime(session["start_time"], "%Y-%m-%d %H:%M:%S")
    end_time = session["end_time"]

    if end_time:
        end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        total_duration += (end_time - start_time)

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
async def setup(ctx):
    """Commande pour créer le message avec les boutons dans le salon actuel et l'historique ailleurs"""
    embed = discord.Embed(title="📢 Gestion des Services", description="Clique sur un bouton ci-dessous pour prendre ou terminer ton service.", color=discord.Color.green())
    setup_msg = await ctx.send(embed=embed, view=ServiceView())

    history_channel = bot.get_channel(HISTORIQUE_CHANNEL_ID)
    if history_channel:
        history_msg = await history_channel.send(embed=discord.Embed(title="📜 Historique des Services", description="Aucun service enregistré.", color=discord.Color.blue()))
        save_message_ids(setup_msg.id, history_msg.id)  # Sauvegarde des IDs
    else:
        await ctx.send("🚨 Erreur : Salon d'historique introuvable. Vérifie l'ID !")

keep_alive()
bot.run(token=token)
