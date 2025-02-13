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

# ----------------------------------------------------------------

tickets = {}
LOGS_CHANNEL_ID = 1339375585859997797  # Remplace par l'ID du salon de logs
TICKET_CATEGORY_ID = 1336456249449123954  # Remplace par l'ID de la catégorie où seront créés les tickets
MOD_ROLE_ID = 1335027928622301284  # ID du rôle qui doit valider la fermeture d'un ticket
TICKET_FILE = "tickets.json"


def save_tickets():
    with open("tickets.json", "w") as f:
        json.dump(tickets, f)

def load_tickets():
    global tickets
    try:
        with open(TICKET_FILE, "r") as f:
            content = f.read().strip()
            tickets = json.loads(content) if content else {}  # Vérifie si le fichier n'est pas vide
    except (FileNotFoundError, json.JSONDecodeError):
        tickets = {}  # Initialise un dictionnaire vide si le fichier est vide ou corrompu



@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")
    load_tickets()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🎫 Ouvrir un ticket", style=discord.ButtonStyle.primary)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild  # Défini correctement interaction ici
        user = interaction.user
        category = discord.utils.get(guild.categories, id=TICKET_CATEGORY_ID)
        mod_role = guild.get_role(MOD_ROLE_ID)  # Récupère le rôle modérateur
        
        if any(channel for channel in guild.text_channels if channel.topic == str(user.id)):
            await interaction.response.send_message("🚨 Tu as déjà un ticket ouvert !", ephemeral=True)
            return
        
        # Définition des permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),  # Bloque tout le monde
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),  # Permet à l'utilisateur de voir et écrire
            mod_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_messages=True)  # Les modérateurs ont un accès complet
        }

        # Création du salon avec les permissions
        ticket_channel = await guild.create_text_channel(
            f"ticket-{user.name}",
            category=category,
            topic=str(user.id),
            overwrites=overwrites
        )

        # Sauvegarde du ticket
        tickets[ticket_channel.id] = {"user": user.id, "open": True}
        save_tickets()

        # Envoie du message avec le bouton de fermeture
        embed = discord.Embed(title="🎫 Ticket ouvert", description=f"{user.mention}, explique ton problème.", color=discord.Color.green())
        close_button = CloseTicketView(ticket_channel.id)
        await ticket_channel.send(embed=embed, view=close_button)
        await interaction.response.send_message(f"✅ Ton ticket a été ouvert ici: {ticket_channel.mention}", ephemeral=True)

        # Logs
        log_channel = bot.get_channel(LOGS_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"📌 Ticket ouvert par {user.mention} ({user.id}) dans {ticket_channel.mention}")


class CloseTicketView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild
        mod_role = discord.utils.get(guild.roles, id=MOD_ROLE_ID)

        if mod_role not in user.roles:
            await interaction.response.send_message("🚨 Seuls les modérateurs peuvent fermer un ticket.", ephemeral=True)
            return

        confirm_view = ConfirmCloseView(self.channel_id)
        await interaction.response.send_message("⚠️ **Confirmation requise** - Un modérateur doit valider la fermeture du ticket.", view=confirm_view)

class ConfirmCloseView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="✅ Confirmer la fermeture", style=discord.ButtonStyle.success)
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = bot.get_channel(self.channel_id)
        if channel:
            await channel.delete()
            del tickets[self.channel_id]
            save_tickets()
            log_channel = bot.get_channel(LOGS_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"🔴 Ticket {channel.name} fermé par {interaction.user.mention}")
            await interaction.response.send_message("✅ Ticket fermé avec succès.", ephemeral=True)

@bot.command()
async def ticket_panel(ctx):
    embed = discord.Embed(title="🎫 Système de Ticket", description="Clique ci-dessous pour ouvrir un ticket.", color=discord.Color.blue())
    await ctx.send(embed=embed, view=TicketView())

# ----------------------------------------------------------------

# ----------------------------------------------------------------

@bot.event
async def on_member_join(member):
    """Envoie un message de bienvenue lorsqu'un membre rejoint le serveur."""
    channel_id_welcome = 1335027849651814441  # Remplace par l'ID du canal de bienvenue
    welcome_channel = bot.get_channel(channel_id_welcome)

    if welcome_channel:
        embed = discord.Embed(
            title="👋 Bienvenue sur le serveur !",
            description=f"Salut {member.mention}, bienvenue sur **{member.guild.name}** ! 🎉\n\n",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        

        await welcome_channel.send(embed=embed)
    
    # Optionnel : Attribuer un rôle automatiquement
    role_id_welcome = 1336773743514746952  # Remplace par l'ID du rôle à attribuer
    role = member.guild.get_role(role_id_welcome)
    if role:
        await member.add_roles(role)


# ----------------------------------------------------------------

keep_alive()
bot.run(TOKEN)
