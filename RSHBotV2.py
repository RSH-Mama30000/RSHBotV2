# ------------ DÉPENDANCES (import, from) ------------ #

import discord
import datetime
import random
import os
import asyncio
import json

from discord.ext import commands, tasks
from discord import app_commands, Interaction, Member, Embed
from discord import ui
from dotenv import load_dotenv

# ------------ CONFIGURATION ------------ #

OWNER_ID = 979806223580926013
LOG_CHANNEL_ID = 1412454772380008459
VERSION_BOT_INFO = "2.3.0"
VERSION_STATUT = "Version 2.3.0"
VERSION_LOGS = "2.3.0"
MUTED_ROLE_NAME = "Muted"
WARN_ROLE_1_NAME = "Warn 1"
WARN_ROLE_2_NAME = "Warn 2"

MP_FILE = "active_mp_channels.json"
WELCOME_FILE = "welcome_channels.json"
MUTES_FILE = "scheduled_mutes.json"
BANS_FILE = "scheduled_bans.json"
WARN_FILE = "warnings.json"
 
load_dotenv("C:/Users/vegah/Desktop/Codage VSCode/Bot Discord/RSHBot/tokv2.env")
TOKEN = os.getenv("DISCORD_TOKEN")

# ----------- INTENTS ------------ #

intents = discord.Intents.all()
intents.message_content = True
intents.guilds = True   
intents.voice_states = True
intents.members = True 
guild_players = {}
guild_text_channels = {}
queues = {}
volumes = {}
current_track = {}
start_time = None  # Sera initialisé dans on_ready

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None, reconnect=True)

# ------------ JSON ------------ #

if os.path.exists(MP_FILE):
    with open(MP_FILE, "r") as f:
        active_mp_channels = json.load(f)
        active_mp_channels = {int(k): v for k, v in active_mp_channels.items()}
else:
    active_mp_channels = {}
    
def save_active_mp_channels():
    with open(MP_FILE, "w") as f:
        json.dump({str(k): v for k, v in active_mp_channels.items()}, f)

# Gestion persistante des salons d'accueil par guild
if os.path.exists(WELCOME_FILE):
    with open(WELCOME_FILE, "r") as f:
        welcome_channels = json.load(f)
        welcome_channels = {int(k): v for k, v in welcome_channels.items()}
else:
    welcome_channels = {}

def save_welcome_channels():
    with open(WELCOME_FILE, "w") as f:
        json.dump({str(k): v for k, v in welcome_channels.items()}, f)

# Gestion persistante des mutes/bans programmés
if os.path.exists(MUTES_FILE):
    with open(MUTES_FILE, "r") as f:
        scheduled_mutes = json.load(f)
        # convert keys to int
        scheduled_mutes = {int(k): v for k, v in scheduled_mutes.items()}
else:
    scheduled_mutes = {}

def save_scheduled_mutes():
    with open(MUTES_FILE, "w") as f:
        json.dump({str(k): v for k, v in scheduled_mutes.items()}, f)

if os.path.exists(BANS_FILE):
    with open(BANS_FILE, "r") as f:
        scheduled_bans = json.load(f)
        scheduled_bans = {int(k): v for k, v in scheduled_bans.items()}
else:
    scheduled_bans = {}

def save_scheduled_bans():
    with open(BANS_FILE, "w") as f:
        json.dump({str(k): v for k, v in scheduled_bans.items()}, f)

# Gestion persistante des warnings/avertissements
if os.path.exists(WARN_FILE):
    with open(WARN_FILE, "r", encoding="utf-8") as f:
        warnings_data = json.load(f)
        # structure: {guild_id: {user_id: [ {"id":..., "moderator_id":..., "reason":..., "timestamp":...}, ... ]}}
        # convert string keys to int for guilds and users
        warnings = {}
        try:
            for gk, gv in warnings_data.items():
                gid = int(gk)
                warnings[gid] = {}
                for uk, ul in gv.items():
                    uid = int(uk)
                    warnings[gid][uid] = ul
        except Exception:
            # Fallback to raw data if parsing fails
            warnings = warnings_data
else:
    warnings = {}

def save_warnings():
    try:
        to_save = {str(gid): {str(uid): lst for uid, lst in users.items()} for gid, users in warnings.items()}
        with open(WARN_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str) -> str:
    """Ajoute un warning et retourne l'ID du warn."""
    ts = int(datetime.datetime.utcnow().timestamp())
    warn_id = f"{user_id}_{ts}"
    entry = {"id": warn_id, "moderator_id": moderator_id, "reason": reason, "timestamp": ts}
    if guild_id not in warnings:
        warnings[guild_id] = {}
    if user_id not in warnings[guild_id]:
        warnings[guild_id][user_id] = []
    warnings[guild_id][user_id].append(entry)
    save_warnings()
    return warn_id

def remove_warning(guild_id: int, user_id: int, warn_id: str) -> bool:
    """Supprime un warn par ID. Retourne True si supprimé."""
    try:
        user_warns = warnings.get(guild_id, {}).get(user_id, [])
        for i, e in enumerate(user_warns):
            if e.get("id") == warn_id:
                user_warns.pop(i)
                # si liste vide, supprime la clé utilisateur
                if not user_warns:
                    warnings[guild_id].pop(user_id, None)
                    if not warnings[guild_id]:
                        warnings.pop(guild_id, None)
                save_warnings()
                return True
    except Exception:
        pass
    return False

def pop_last_warning(guild_id: int, user_id: int):
    """Supprime et retourne le dernier warn pour un utilisateur, ou None si aucun."""
    try:
        user_warns = warnings.get(guild_id, {}).get(user_id, [])
        if not user_warns:
            return None
        entry = user_warns.pop()
        if not user_warns:
            warnings[guild_id].pop(user_id, None)
            if not warnings[guild_id]:
                warnings.pop(guild_id, None)
        save_warnings()
        return entry
    except Exception:
        return None

# ------------ def ------------ #

async def safe_defer(interaction: discord.Interaction, ephemeral: bool = False):
    """Essaye de `defer` l'interaction de façon sûre.

    Certains cas (interaction expirée ou déjà répondue) lancent
    discord.errors.NotFound. On l'ignore ici pour que le reste
    du traitement puisse continuer (on utilisera `followup.send`).
    """
    try:
        # interaction.response.is_done() retourne True si déjà acknowleged
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=ephemeral)
    except discord.errors.NotFound:
        # Interaction unknown/expired — on ignore, on continuera avec followup
        return
    except Exception as e:
        # Petits logs en console pour débogage sans interrompre la commande
        print(f"safe_defer error: {e}")
        return

 
async def safe_followup(interaction: discord.Interaction, *args, **kwargs):
    """Envoie un followup de façon sûre : si l'interaction est inconnue/expirée,
    tente d'envoyer le message dans le channel courant (si accessible).
    Usage : await safe_followup(interaction, "texte", ephemeral=True) ou kwargs comme embed=..., view=...
    """
    try:
        # Si l'interaction a été initialement acked, followup fonctionnera
        await interaction.followup.send(*args, **kwargs)
    except discord.errors.NotFound:
        # Interaction inconnue/expirée -> fallback : essayer d'envoyer directement au channel
        try:
            ch = getattr(interaction, 'channel', None)
            if ch:
                # Si ephemeral demandé, on ne peut pas reproduire ; envoie public
                await ch.send(*args, **{k: v for k, v in kwargs.items() if k != 'ephemeral'})
        except Exception:
            # Tout échoue silencieusement pour ne pas crasher le bot
            return
    except Exception as e:
        # Log et ignore
        print(f"safe_followup error: {e}")
        return

async def get_muted_role(guild: discord.Guild):
    muted_role = discord.utils.get(guild.roles, name=MUTED_ROLE_NAME)
    if muted_role is None:
        muted_role = await guild.create_role(
            name=MUTED_ROLE_NAME,
            permissions=discord.Permissions(send_messages=False, speak=False),
            reason="Création du rôle Muted pour la modération"
        )
        for channel in guild.channels:
            try:
                await channel.set_permissions(muted_role, send_messages=False, speak=False, add_reactions=False)
            except Exception:
                pass
    return muted_role

async def get_warn_role(guild: discord.Guild, role_name: str) -> discord.Role | None:
    """Retourne le rôle warn demandé, ou le crée automatiquement s'il n'existe pas."""
    role = discord.utils.get(guild.roles, name=role_name)
    if role is None:
        try:
            role = await guild.create_role(
                name=role_name,
                reason=f"Création automatique du rôle {role_name} pour la gestion des warns"
            )
            # Place le rôle juste en dessous du top rôle du bot pour pouvoir l'appliquer
            await role.edit(position=guild.me.top_role.position - 1)
        except Exception as e:
            print(f"[ERREUR] Impossible de créer le rôle {role_name} : {e}")
            return None
    return role

async def process_schedules():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now_ts = int(datetime.datetime.utcnow().timestamp())

        # Traiter les mutes expirés
        try:
            to_unmute = [k for k, v in scheduled_mutes.items() if v.get("expiration", 0) <= now_ts]
            for key in to_unmute:
                entry = scheduled_mutes.pop(key, None)
                if not entry:
                    continue
                guild = bot.get_guild(entry.get("guild_id"))
                if not guild:
                    continue
                try:
                    member = guild.get_member(entry.get("user_id"))
                    muted_role = await get_muted_role(guild)
                    if member and muted_role in member.roles:
                        await member.remove_roles(muted_role, reason="Fin automatique du mute")
                        # Envoi DM
                        try:
                            dm = discord.Embed(
                                title="🔊 Ton mute est terminé",
                                description=f"Ton mute sur **{guild.name}** est maintenant terminé.",
                                color=discord.Color.green(),
                                timestamp=discord.utils.utcnow()
                            )
                            await member.send(embed=dm)
                        except Exception:
                            pass
                except Exception:
                    pass
            if to_unmute:
                save_scheduled_mutes()
        except Exception:
            pass

        # Traiter les bans expirés
        try:
            to_unban = [k for k, v in scheduled_bans.items() if v.get("expiration", 0) <= now_ts]
            for key in to_unban:
                entry = scheduled_bans.pop(key, None)
                if not entry:
                    continue
                guild = bot.get_guild(entry.get("guild_id"))
                if not guild:
                    # Si le bot n'est plus dans la guilde, on ne peut pas unban
                    continue
                try:
                    user = await bot.fetch_user(entry.get("user_id"))
                    await guild.unban(user, reason="Fin automatique du ban")
                    try:
                        dm = discord.Embed(
                            title="✅ Tu as été débanni",
                            description=f"Ton ban sur **{guild.name}** est maintenant levé.",
                            color=discord.Color.green(),
                            timestamp=discord.utils.utcnow()
                        )
                        await user.send(embed=dm)
                    except Exception:
                        pass
                except Exception:
                    pass
            if to_unban:
                save_scheduled_bans()
        except Exception:
            pass

        await asyncio.sleep(30)

# ------------ DONNÉES POUR /commande ------------ #
  
categories = {
    "jeux_fun": {       
        "🎁 Boîte Mystère": {"description": "Ouvre une boîte mystère pour découvrir une récompense aléatoire.", "syntax": "/boitemystere"},
        "🪙 Pile ou Face": {"description": "Lance une pièce pour jouer à Pile ou Face.", "syntax": "/pileouface"},
        "🔮 EightBall": {"description": "Pose une question et reçois une réponse aléatoire.", "syntax": "/eightball"},
    },
    "utilitaires": {
        "ℹ️ Bot Info": {"description": "Affiche des informations sur le bot.", "syntax": "/botinfo"},
        "👥 Équipe": {"description": "Présentation de l'équipe qui a crée RSHBotV2.", "syntax": "/equipe"},
        "🫂 Discord": {"description": "Lien d'invitation du serveur Discord de RSHBotV2.", "syntax": "/discord"},
        "🗣️ Dire": {"description": "Fait dire quelque chose au bot.", "syntax": "/dire [message]"},
        "🧹 Effacer": {"description": "Efface un certain nombre de messages.", "syntax": "/effacer [nombre]"},
        "🖼️ Avatar": {"description": "Affiche la photo de profil d'un utilisateur.", "syntax": "/avatar [ID discord]"},
        "📡 Latence": {"description": "Voir la latence du bot.", "syntax": "/latence"},
        "💬 Message": {"description": "Envoyer un message sous l'identité de RSHBotV2.", "syntax": "/message"},
        "🔐 Secret": {"description": "Commande utilisable seulement par le créateur de RSHBotV2.", "syntax": "/secret"},
        "⏱️ Uptime": {"description": "Affiche depuis combien de temps le bot est en ligne.", "syntax": "/uptime"},
    },
    "discussion": {
        "👋 Bonjour": {"description": "Envoyer des salutations.", "syntax": "/bonjour"},
        "🔥 Morton": {"description": "Tu connais le dicton !", "syntax": "/morton"},
    },
    "moderation": {
        "🦵 Kick": {"description": "Expulse un membre du serveur", "syntax": "/kick"},
        "🔨 Ban": {"description": "Bannir un membre du serveur", "syntax": "/ban"},
        "🔓 Unban": {"description": "Débannir un membre du serveur", "syntax": "/unban"},
        "🗑️ Mute": {"description": "Mute un membre du serveur", "syntax": "/mute"},
        "🔇 Unmute": {"description": "Unmute un membre du serveur", "syntax": "/unmute"},
        "⚠️ Warn": {"description": "Avertir un membre du serveur", "syntax": "/warn"},
        "❌ Unwarn": {"description": "Retirer un avertissement d'un membre", "syntax": "/unwarn"},
        "✨ SetupMP": {"description": "Ouvre un chat privé avec un utilisateur via le bot", "syntax": "/setupmp"},
        "🔚 StopMP": {"description": "Arrête le chat MP dans ce salon", "syntax": "/stopmp"},
        "🏠 Bienvenue Set": {"description": "Définit le salon courant comme salon d'accueil pour les nouveaux membres.", "syntax": "/bienvenue_set"},
        "🏠 Bienvenue Remove": {"description": "Supprime le salon d'accueil configuré pour ce serveur.", "syntax": "/bienvenue_remove"},
        "📋 Warn List": {"description": "Affiche la liste des avertissements d'un membre.", "syntax": "/warnlist"},
        "📜 Ban List": {"description": "Affiche la liste des membres bannis du serveur.", "syntax": "/banlist"},
    },
}

display_names = {
    "jeux_fun": "🎮 Jeux & Fun",
    "utilitaires": "🛠️ Utilitaires",
    "discussion": "💬 Discussion",
    "moderation": "🛡️ Modération"
}

rewards = [
    {"nom": "💰 100 pièces d'or", "effet": "Tu deviens plus riche !"},
    {"nom": "🎟️ Ticket VIP", "effet": "Tu es maintenant un membre d'honneur !"},
    {"nom": "🍀 Trèfle à 4 feuilles", "effet": "La chance est de ton côté !"},
    {"nom": "💎 Diamant rare", "effet": "Tu es maintenant un vrai boss !"},
    {"nom": "👻 Fantôme effrayant", "effet": "Boo ! Il te suit partout maintenant..."},
    {"nom": "🔥 Feu magique", "effet": "Attention, ça brûle !"},
    {"nom": "💩 Tas de caca", "effet": "Oh non... Ça sent mauvais !"},
]  

responses = [
        "Oui !", "Non", "Peut-être...", "Je ne sais pas", "Bien sur", "Je ne pense pas...", "Absolument !", "Jamais !"
]

# ------------ ÉVÉNEMENTS ------------ #

@bot.event
async def on_ready():
    global start_time
    if start_time is None:  # N'initialise que si ce n'est pas déjà fait
        start_time = datetime.datetime.utcnow()
        
    print(f"✅ Connecté en tant que {bot.user} (ID: {bot.user.id})")
    print(f"💻 Version du bot : {VERSION_STATUT}")
    await bot.change_presence(
        activity=discord.CustomActivity(name="💻 " + VERSION_STATUT),
        status=discord.Status.online
    )
    try:
        synced = await bot.tree.sync()
        print(f"🤖 {len(synced)} commandes slash synchronisées.")
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation des commandes slash : {e}")
    # Démarre la tâche de traitement des plans (unmute/unban programmés)
    try:
        bot.loop.create_task(process_schedules())
        print("🕒 Tâche de gestion des mutes/bans programmés démarrée.")
    except Exception as e:
        print(f"❌ Impossible de démarrer la tâche de gestion : {e}")

@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: app_commands.Command):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        invite_link = "Impossible en MP"
        if interaction.guild:
            # Essaye de créer une invite permanente
            try:
                invite = await interaction.channel.create_invite(max_age=0, max_uses=0, unique=False)
                invite_link = invite.url
            except discord.Forbidden:
                invite_link = "⚠️ Le bot n’a pas la permission de créer une invitation"
            except Exception as e:
                invite_link = f"⚠️ Erreur: {e}"

        embed = discord.Embed(
            title="📜 Commande exécutée",
            description=(
                f"**Commande :** /{command.name}\n"
                f"**Utilisateur :** {interaction.user} ({interaction.user.id})\n"
                f"**Serveur :** {interaction.guild.name if interaction.guild else 'En message privé'}\n"
                f"**Invitation :** {invite_link}\n"
                f"**Version : **" + VERSION_BOT_INFO
            ),
            color=discord.Color.blurple()
        )
        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="❌ Erreur de commande",
            description=(
                f"**Commande :** /{interaction.command.name if interaction.command else 'Inconnue'}\n"
                f"**Utilisateur :** {interaction.user} ({interaction.user.id})\n"
                f"**Serveur :** {interaction.guild.name if interaction.guild else 'En message privé'}\n\n"
                f"**Erreur :** `{error}`"
            ),
            color=discord.Color.red()
        )
        embed.timestamp = discord.utils.utcnow()
        await log_channel.send(embed=embed)
    
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Si c'est un MP d'un utilisateur suivi
    if isinstance(message.channel, discord.DMChannel) and message.author.id in active_mp_channels:
        channel_id = active_mp_channels[message.author.id]
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(
                f"📩 **Message reçu de {message.author}** (ID: `{message.author.id}`) :\n\n{message.content}"
            )

    # Si c'est un message dans le salon lié
    elif message.guild and message.channel.id in active_mp_channels.values():
        for user_id, chan_id in active_mp_channels.items():
            if chan_id == message.channel.id:
                target_user = await bot.fetch_user(user_id)
                try:
                    await target_user.send(f"{message.content}")
                except:
                    await message.channel.send("❌ Impossible d'envoyer le message à l'utilisateur.")
                break
    
@bot.event
async def on_member_join(member: discord.Member):
    channel_id = welcome_channels.get(member.guild.id)
    if not channel_id:
        return
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    guild_icon = member.guild.icon.url if member.guild.icon else None

    embed = discord.Embed(
        title="🎉 Bienvenue !",
        description=(
            f"Salut {member.mention} — merci de nous rejoindre sur **{member.guild.name}** !\n\n"
            "Prends un moment pour lire les règles et te présenter. Si tu as des questions, demande à un membre du staff."
        ),
        color=discord.Color.brand_green()
    )
    embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
    embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
    embed.add_field(name="📅 Compte créé le", value=f"<t:{int(member.created_at.timestamp())}:F>", inline=True)
    if guild_icon:
        embed.set_thumbnail(url=guild_icon)
    embed.set_footer(text=f"Bienvenue sur {member.guild.name} — Bon séjour !")
    embed.timestamp = datetime.datetime.utcnow()

    await channel.send(embed=embed)

@bot.event
async def on_member_remove(member: discord.Member):
    channel_id = welcome_channels.get(member.guild.id)
    if not channel_id:
        return
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    guild_icon = member.guild.icon.url if member.guild.icon else None

    embed = discord.Embed(
        title="👋 Départ d'un membre",
        description=(
            f"{member.mention} a quitté **{member.guild.name}**. Nous te souhaitons bonne continuation — tu seras toujours le bienvenu !"
        ),
        color=discord.Color.red()
    )
    embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
    embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
    embed.add_field(name="📅 Compte créé le", value=f"<t:{int(member.created_at.timestamp())}:F>", inline=True)
    if guild_icon:
        embed.set_thumbnail(url=guild_icon)
    embed.set_footer(text=f"Au revoir de la part de {member.guild.name} — Porte-toi bien !")
    embed.timestamp = datetime.datetime.utcnow()

    await channel.send(embed=embed)
    
# ------------ COMMANDES SLASH ------------ #
    
@bot.tree.command(name="commande", description="Affiche les commandes d'une catégorie")
@app_commands.choices(
    catégorie=[
        app_commands.Choice(name="🎮 Jeux & Fun", value="jeux_fun"),
        app_commands.Choice(name="🛠️ Utilitaires", value="utilitaires"),
        app_commands.Choice(name="💬 Discussion", value="discussion"),
        app_commands.Choice(name="🛡️ Modération", value="moderation")
    ]
)
async def commande(interaction: discord.Interaction, catégorie: app_commands.Choice[str]):
    key = catégorie.value
    embed = discord.Embed(
        title=f"{display_names[key]} - Commandes disponibles",
        description=f"Voici les commandes de la catégorie **{display_names[key]}** :",
        color=discord.Color.blurple()
    )

    for nom, info in categories[key].items():
        embed.add_field(
            name=nom,
            value=f"📝 {info['description']}\n💡 Syntaxe : `{info['syntax']}`",
            inline=False
        )

    embed.set_footer(text="RSHBotV2 ・ Que des slashs commandes 💻", icon_url=bot.user.display_avatar.url)
    embed.set_thumbnail(url=bot.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="bonjour", description="Te dit bonjour !")
async def bonjour(interaction: discord.Interaction):
    await interaction.response.send_message(f"Bonjour {interaction.user.mention} 👋🏼 !")
    
@bot.tree.command(name="morton", description="Tu connais le dicton ?")
async def morton(interaction: discord.Interaction):
    await interaction.response.send_message(f"# Morton On Top !")
    
@bot.tree.command(name="secret", description="Commande utilisable seulement par le créateur de RSHBotV2.")
async def secret(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Tu n'es pas le créateur de RSHBotV2 donc tu ne peux pas voir le contenue de cette commande.")
        return
    
    await interaction.response.send_message("✅ Salut patron ! Si tu souhaites voir mon code c'est sur ce discord et après tu as déjà les permissions de voir le salon ! https://discord.gg/mfVvt3j2By")
    
@bot.tree.command(name="equipe", description="Présentation de l'équipe qui a crée RSHBotV2")
async def equipe(interaction: discord.Interaction):
    bot_user = bot.user
    
    embed = discord.Embed(
        title="Développeur de RSHBotV2",
        description="Voici les membres qui ont contribué à mon développement.",
        color=discord.Color.purple()
    )
    embed.set_thumbnail(url=bot_user.avatar.url if bot_user.avatar else bot_user.default_avatar.url)
    embed.add_field(name="👨‍💻 RSH-Mama30000", value="Développeur principal de RSHBotV2", inline=False)
    embed.add_field(name="👨‍🏫 El Tulipe", value="A aidé et appris à RSH-Mama30000 à développer en Python", inline=False)
    embed.add_field(name="Tu veux rejoindre l'équipe ?", value="Si oui ouvre un https://discord.com/channels/1310182105577426994/1343343848004386867 !", inline=False)
    embed.timestamp = discord.utils.utcnow()
    
    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="botinfo", description="Voir les informations de RSHBotV2")
async def botinfo(interaction: discord.Interaction):
    bot_user = bot.user
    
    embed = discord.Embed(
        title="Informations de RSHBotV2",
        description="Voici en gros comment je fonctionne !",
        color=discord.Color.magenta()
    )
    embed.set_thumbnail(url=bot_user.avatar.url if bot_user.avatar else bot_user.default_avatar.url)
    embed.add_field(name="🖥️ Version", value=VERSION_BOT_INFO, inline=True)
    embed.add_field(name="🐍 Langage du bot", value="Python 3.11.9", inline=True)
    embed.add_field(name="📅 Date de création", value="30/05/2025 22h13", inline=True)
    embed.add_field(name="👨‍💻 Développeur", value="Pour avoir toutes les informations /equipe", inline=True)
    embed.add_field(name="📛 Nom du bot", value="RSHBotV2", inline=True)
    embed.add_field(name="🔢 ID du bot", value="1354844575168204840", inline=True)
    embed.add_field(name="Tu veux rejoindre l'équipe ?", value="Si oui ouvre un https://discord.com/channels/1310182105577426994/1343343848004386867 !", inline=False)
    embed.timestamp = discord.utils.utcnow()
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="bienvenue_set", description="Définit le salon courant comme salon d'accueil pour les nouveaux membres.")
async def bienvenue_set(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)
        return

    if not interaction.guild:
        await interaction.response.send_message("❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True)
        return

    welcome_channels[interaction.guild.id] = interaction.channel.id
    save_welcome_channels()

    embed = discord.Embed(
        title="✅ Salon d'accueil défini",
        description=f"Les nouveaux membres recevront maintenant un message dans : {interaction.channel.mention}",
        color=discord.Color.green()
    )
    embed.add_field(name="🔧 Configuration par", value=f"{interaction.user}", inline=True)
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="bienvenue_remove", description="Supprime le salon d'accueil configuré pour ce serveur.")
async def bienvenue_remove(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)
        return

    if not interaction.guild:
        await interaction.response.send_message("❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True)
        return

    if interaction.guild.id not in welcome_channels:
        await interaction.response.send_message("❌ Aucun salon d'accueil configuré pour ce serveur.", ephemeral=True)
        return

    del welcome_channels[interaction.guild.id]
    save_welcome_channels()

    embed = discord.Embed(
        title="🗑️ Salon d'accueil supprimé",
        description="Le salon d'accueil a bien été supprimé. Les messages de bienvenue et départ ne seront plus envoyés.",
        color=discord.Color.orange()
    )
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed, ephemeral=True)
    
@bot.tree.command(name="dire", description="Permet de dire quelque chose sous l'identité de RSHBotV2.")
@app_commands.describe(message="Le message à envoyer sous l'identité de RSHBotV2.")
async def dire(interaction: discord.Interaction, message: str):
    await safe_defer(interaction, ephemeral=True)

    await interaction.channel.send(message)
    
@bot.tree.command(name="effacer", description="Supprime un nombre de messages récents.")
@app_commands.describe(nombre="Nombre de messages à supprimer (1 à 500)")
async def effacer(interaction: discord.Interaction, nombre: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande !", ephemeral=True)
        return
    
    if not interaction.guild.me.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ Je n'ai pas la permission de supprimer des messages.", ephemeral=True)
        return
    
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ Cette commande doit être utilisée dans un salon textuel.", ephemeral=True)
        return

    if nombre <= 0 or nombre > 500:
        await interaction.response.send_message("❌ Veuillez entrer un nombre entre 1 et 500.", ephemeral=True)
        return

    await safe_defer(interaction, ephemeral=True)

    deleted = await interaction.channel.purge(limit=nombre, check=lambda m: not m.pinned)

    await interaction.followup.send(f"✅ {len(deleted)} messages ont été supprimés.", ephemeral=True)
    
@bot.tree.command(name="avatar", description="Voir la photo de profil d'un utilisateur de votre choix grâce à son ID.")
@app_commands.describe(id="ID de la personne que vous voulez voir la photo de profil.")
async def avatar(interaction: discord.Interaction, id: str):
    try:
        user = await bot.fetch_user(id)
        if user.avatar:
            embed = discord.Embed(title=f"Voici l'avatar de {user.name}", color=discord.Color.red())
            embed.set_image(url=user.avatar.url)
            embed.timestamp = discord.utils.utcnow()
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"{user.name} n'a pas d'avatar personnalisé.")
    except discord.NotFound:
        await interaction.response.send_message("Utilisateur introuvable. Vérifie l'ID et réessaye.")
    except discord.HTTPException:
        await interaction.response.send_message("Une erreur est survenue en essayant de récupérer l'utilisateur.")
    
@bot.tree.command(name="latence", description="Permet de voir la latence de RSHBotV2")
async def latence(interaction: discord.Interaction):
    await interaction.response.send_message(f"La latence de RSHBotV2 est de {round(bot.latency * 1000)}")
    
@bot.tree.command(name="boitemystere", description="Ouvre un boîte mystère et gagne un cadeau !")
async def boitemystere(interaction: discord.Interaction):
    reward = random.choice(rewards)
    
    embed = discord.Embed(
        title="🎁 Boîte Mystère Ouverte !",
        description=f"Tu as gagné : **{reward['nom']}**\n\n_{reward['effet']}_",
        color=discord.Color.gold()
    )
    embed.timestamp = discord.utils.utcnow()
    
    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="pileouface", description="Jouer à pile ou face")
@app_commands.choices(choix=[
    app_commands.Choice(name="Pile", value="pile"),
    app_commands.Choice(name="Face", value="face"),
])
@app_commands.describe(choix="Choisis entre pile ou face")
async def pile_ou_face(interaction: discord.Interaction, choix: app_commands.Choice[str]):
    tirage = random.choice(["pile", "face"])
    if choix.value == tirage:
        resultat = f"🎉 Gagné ! C'était **{tirage.capitalize()}**."
    else:
        resultat = f"❌ Perdu ! C'était **{tirage.capitalize()}**."
        
    await interaction.response.send_message(resultat)
    
@bot.tree.command(name="eightball", description="Réponds à une question par une réponse aléatoire !")
@app_commands.describe(question="Pose ta question à la boule magique")
async def eightball(interaction: discord.Interaction, question: str):

    answer = random.choice(responses)
    await interaction.response.send_message(f"Question : {question}\nRéponse : {answer}")

@bot.tree.command(name="message", description="Envoie un MP à quelqu'un")
async def message(interaction: discord.Interaction, user_id: str, *, message: str):
    try:
        user = await bot.fetch_user(user_id)  # Fonctionne même si la personne n'est pas dans le serveur
        await user.send(message)
        await interaction.response.send_message(
            f"✅ Message envoyé à {user.name} ({user.id})"
        )
    except discord.NotFound:
        await interaction.response.send_message("❌ Utilisateur introuvable. Vérifie l'ID.")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Je ne peux pas envoyer de message à cette personne. Peut-être qu’elle a désactivé les DMs ou m’a bloqué.")
    except Exception as e:
        await interaction.response.send_message(f"⚠️ Erreur inconnue : {e}")
    
@bot.tree.command(name="uptime", description="Affiche depuis combien de temps le bot est en ligne.")
async def uptime(interaction: discord.Interaction):
    # Calcul de la durée écoulée
    now = datetime.datetime.utcnow()
    delta = now - start_time

    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format lisible adaptatif
    if days > 0:
        uptime_str = f"{days} jour{'s' if days > 1 else ''}, {hours}h {minutes}m {seconds}s"
        total_days = f"({days} jours au total)"
    elif hours > 0:
        uptime_str = f"{hours}h {minutes}m {seconds}s"
        total_days = ""
    else:
        uptime_str = f"{minutes}m {seconds}s"
        total_days = ""

    # Création de l'embed
    embed = discord.Embed(
        title="⏱️ État de RSHBotV2",
        description="**Le bot est actuellement en ligne**",
        color=discord.Color.green(),
        timestamp=now
    )
    
    # Durée avec format adaptatif
    embed.add_field(
        name="🔼 Temps de fonctionnement",
        value=f"**{uptime_str}**",
        inline=False
    )
    
    # Status du bot
    embed.add_field(
        name="� Status",
        value="✅ Opérationnel",
        inline=False
    )
    
    embed.set_footer(text="RSHBotV2 • Surveillance en temps réel", icon_url=interaction.client.user.display_avatar.url)
    embed.set_thumbnail(url=interaction.client.user.display_avatar.url)

    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="discord", description="Informations pour rejoindre le serveur Discord de RSHBotV2")
async def discord_info(interaction: discord.Interaction):
    bot_user = bot.user
    
    embed = discord.Embed(
        title="Rejoindre le serveur Discord de RSHBotV2",
        description="Pour toute question, suggestion ou simplement pour discuter avec la communauté et l'équipe de développement, rejoins notre serveur Discord !",
        color=discord.Color.blue(),
    )
    embed.set_thumbnail(url=bot_user.avatar.url if bot_user.avatar else bot_user.default_avatar.url)
    embed.add_field(name="🔗 Lien d'invitation", value="[Clique ici pour rejoindre le serveur Discord de RSHBotV2](https://discord.gg/PUgBqTS9df)", inline=False)
    embed.add_field(name="👥 Communauté", value="Rejoins une communauté active et amicale prête à t'aider et à partager des idées.", inline=False)
    embed.add_field(name="🛠️ Support", value="Obtiens de l'aide directement de l'équipe de développement et des autres utilisateurs.", inline=False)
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed) 
    
# ------------ MODÉRATION ------------ #

@bot.tree.command(name="setupmp", description="Ouvre un chat privé avec un utilisateur via le bot")
@app_commands.describe(cible="ID ou utilisateur à contacter")
async def setupmp(interaction: discord.Interaction, cible: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande !", ephemeral=True)
        return
    
    if not interaction.guild:
        await interaction.response.send_message("❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True)
        return
    
    try:
        user_id = int(cible)
        user = await bot.fetch_user(user_id)
    except:
        await interaction.response.send_message("❌ Utilisateur introuvable. Fournis un ID valide.", ephemeral=True)
        return
        
    channel = interaction.channel
    
    if channel.id in active_mp_channels.values():
        await interaction.response.send_message("❌ Ce salon est déjà lié à une autre session MP. Utilise `/stopmp` d'abord.", ephemeral=True)
        return
        
    try:
        embed = discord.Embed(
            title="💬 Demande de discussion",
            description=f"Un staff souhaite discuter avec toi via RSHBotV2. Pour lui répondre envoie direct les messages ici !",
            color=discord.Color.blue()
        )
        embed.add_field(name="🛡️ Nom du Staff", value=f"**{interaction.user}**", inline=False)
        embed.set_footer(text="RSHBotV2", icon_url="https://cdn.discordapp.com/avatars/1354844575168204840/a_6961ac297826d3df38b2e98660d6edbd.gif?size=1024&animated=true")
        embed.timestamp = discord.utils.utcnow()
        
        await user.send(embed=embed)
    except:
        await interaction.response.send_message("❌ Impossible d'envoyer un DM à cet utilisateur.", ephemeral=True)
        return
    
    # Stocke la liaison
    active_mp_channels[user.id] = channel.id
    save_active_mp_channels()
    
    # Rename du salon
    try:
        await interaction.channel.edit(name=f"discussion-avec-{user.name}")
    except:
        pass
    
    await interaction.response.send_message(f"✅ Chat privé créé avec **{user}**.", ephemeral=True)
    
@bot.tree.command(name="stopmp", description="Arrête le chat MP dans ce salon")
async def stopmp(interaction: discord.Interaction):
    channel = interaction.channel
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande !", ephemeral=True)
        return
    
    if not interaction.guild:
        await interaction.response.send_message("❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True)
        return
    
    # Vérifie si ce salon est lié à un utilisateur
    user_id_to_remove = None
    for uid, chan_id in list(active_mp_channels.items()):
        if chan_id == channel.id:
            user_id_to_remove = uid
            break
    
    if not user_id_to_remove:
        await interaction.response.send_message("❌ Aucun chat MP actif dans ce salon.", ephemeral=True)
        return
    
    user = await bot.fetch_user(user_id_to_remove)
    
    embed = discord.Embed(
        title="🔚 Fin de discussion",
        description=f"La discussion avec {interaction.user} est terminée.",
        color=discord.Color.brand_red()
    )
    embed.add_field(name="Tu as eu un problème pendant la discussion ?", value="Si oui ouvre un https://discord.com/channels/1310182105577426994/1343343848004386867 !", inline=False)
    embed.timestamp = discord.utils.utcnow()
    
    try:
        await user.send(embed=embed)
    except:
        pass
    
    # Retire l’utilisateur de la liste active
    del active_mp_channels[user_id_to_remove]
    save_active_mp_channels()
    
    # ⚠️ Répond d'abord à l'interaction
    await interaction.response.send_message("⏳ Fermeture du chat et recréation du salon...", ephemeral=True)
    
    # Supprime le salon
    await channel.delete(reason="Arrêt du MP")
    
    # Crée un nouveau salon
    await interaction.guild.create_text_channel(
        name="message-privé-bot",
        reason="Recréation du salon MP"
    )

@bot.tree.command(name="kick", description="Expulse un membre du serveur")
@app_commands.describe(membre="Le membre à expulser", raison="Raison de l'expulsion")
async def kick(interaction: Interaction, membre: Member, raison: str):
    # Embed pour erreurs kick
    def error_embed_kick(title: str, description: str):
        return Embed(title=title, description=description, color=discord.Color.red())

    # Vérifie que l'utilisateur est dans un serveur
    if not interaction.guild:
        await interaction.response.send_message(embed=error_embed_kick("Erreur", "Cette commande doit être utilisée dans un serveur."), ephemeral=True)
        return

    # Vérifie que l'utilisateur a la permission
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message(embed=error_embed_kick("Permission refusée", "❌ Tu n'as pas la permission de kicker des membres."), ephemeral=True)
        return

    # Vérifie que le bot a la permission
    if not interaction.guild.me.guild_permissions.kick_members:
        await interaction.response.send_message(embed=error_embed_kick("Permission bot", "❌ Je n'ai pas la permission de kicker des membres."), ephemeral=True)
        return

    # Protection contre les rôles supérieurs ou le propriétaire
    if membre.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message(embed=error_embed_kick("Rôle trop élevé", "❌ Tu ne peux pas kicker quelqu'un avec un rôle égal ou supérieur au tien."), ephemeral=True)
        return

    if membre == interaction.guild.owner:
        await interaction.response.send_message(embed=error_embed_kick("Propriétaire", "❌ Impossible de kicker le propriétaire du serveur."), ephemeral=True)
        return

    if membre == interaction.user:
        await interaction.response.send_message(embed=error_embed_kick("Erreur", "❌ Tu ne peux pas te kicker toi-même."), ephemeral=True)
        return

    try:
        try:
            embed_dm = Embed(
                title="⚠️ Saction reçue",
                description=f"Tu as été **expulsé** du serveur **{interaction.guild.name}**.",
                color=discord.Color.orange()
            )
            embed_dm.add_field(name="Raison", value=raison, inline=False)
            embed_dm.set_footer(text=f"Expulsé par {interaction.user}")
            await membre.send(embed=embed_dm)
        except:
            pass
        
        # Kick du membre (argument correct en anglais)
        await membre.kick(reason=raison)

        # Embed succès
        embed_success = Embed(
            title="Membre expulsé",
            description=f"{membre.mention} a été expulsé avec succès.",
            color=discord.Color.green()
        )
        embed_success.add_field(name="Raison", value=raison, inline=False)
        embed_success.set_footer(text=f"Kick demandé par {interaction.user}")
        await interaction.response.send_message(embed=embed_success)

    except discord.Forbidden:
        await interaction.response.send_message(embed=error_embed_kick("Erreur", "❌ Je n'ai pas les permissions nécessaires pour kicker ce membre."), ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(embed=error_embed_kick("Erreur", f"❌ Une erreur est survenue : {e}"), ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(embed=error_embed_kick("Erreur inconnue", f"❌ Une erreur inattendue est survenue : {e}"), ephemeral=True)
    
@bot.tree.command(name="ban", description="Bannir un membre du serveur")
@app_commands.describe(
    membre="Le membre à bannir",
    duree="Durée du ban en jours (0 = permanent)",
    raison="Raison du ban"
)
async def ban(interaction: Interaction, membre: Member, duree: int, raison: str):
    # Embed pour erreurs
    def error_embed_ban(title: str, description: str):
        return Embed(title=title, description=description, color=discord.Color.red())
    
    # Vérifications basiques
    if not interaction.guild:
        await interaction.response.send_message(embed=error_embed_ban("Erreur", "❌ Cette commande doit être utilisée dans un serveur."), ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message(embed=error_embed_ban("Permission refusée", "❌ Tu n'as pas la permission de bannir des membres."), ephemeral=True)
        return
    
    if not interaction.guild.me.guild_permissions.ban_members:
        await interaction.response.send_message(embed=error_embed_ban("Permission bot", "❌ Je n'ai pas la permission de bannir des membres."), ephemeral=True)
        return
    
    if membre.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message(embed=error_embed_ban("Rôle trop élevé", "❌ Tu ne peux pas bannir quelqu'un avec un rôle égal ou supérieur au tien."), ephemeral=True)
        return
    
    if membre == interaction.guild.owner:
        await interaction.response.send_message(embed=error_embed_ban("Propriétaire", "❌ Impossible de bannir le propriétaire du serveur."), ephemeral=True)
        return
    
    if membre == interaction.user:
        await interaction.response.send_message(embed=error_embed_ban("Erreur", "❌ Tu ne peux pas te bannir toi-même."), ephemeral=True)
        return
    
    try:
        try:
            embed_dm = Embed(
                title="⛔ Sanction reçue",
                description=f"Tu as été **banni** du serveur **{interaction.guild.name}**.",
                color=discord.Color.red()
            )
            embed_dm.add_field(name="Raison", value=raison, inline=False)
            if duree == 0:
                embed_dm.add_field(name="Durée", value=f"⏳ Permanent", inline=False)
            else:
                embed_dm.add_field(name="Durée", value=f"⏳ {duree} jour(s)", inline=False)
            embed_dm.set_footer(text=f"Banni par {interaction.user}")
            await membre.send(embed=embed_dm)
        except:
            pass

        # Ban du membre
        await membre.ban(reason=raison)

        # Embed succès
        embed_success_ban = Embed(
            title="🔨 Membre banni",
            description=f"{membre.mention} a été banni avec succès.",
            color=discord.Color.red()
        )
        embed_success_ban.add_field(name="Raison", value=raison, inline=False)
        if duree == 0:
            embed_success_ban.add_field(name="Durée", value="⏳ Permanent", inline=False)
        else:
            embed_success_ban.add_field(name="Durée", value=f"⏳ {duree} jour(s)", inline=False)
        embed_success_ban.set_footer(text=f"Ban demandé par {interaction.user}")
        await interaction.response.send_message(embed=embed_success_ban)

        # Si durée > 0 → planifie l'unban persistant
        if duree > 0:
            # stocke l'unban programmé: key = timestamp_expiration, value = dict(guild_id, user_id, reason)
            expiration = int((datetime.datetime.utcnow() + datetime.timedelta(days=duree)).timestamp())
            # Utilisons un id unique simple (timestamp_userid)
            entry_id = f"{expiration}_{membre.id}"
            scheduled_bans[entry_id] = {
                "guild_id": interaction.guild.id,
                "user_id": membre.id,
                "reason": raison,
                "expiration": expiration
            }
            save_scheduled_bans()
            
    except discord.Forbidden:
        await interaction.response.send_message(embed=error_embed_ban("Erreur", "❌ Je n'ai pas les permissions nécessaires pour bannir ce membre."), ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(embed=error_embed_ban("Erreur", f"❌ Une erreur est survenue : {e}"), ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(embed=error_embed_ban("Erreur inconnue", f"❌ Une erreur inattendue est survenue : {e}"), ephemeral=True)
        
@bot.tree.command(name="unban", description="Débannir un utilisateur du serveur")
@app_commands.describe(
    id="L'ID discord du membre à unban",
    raison="Motif du unban"
)
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, id: str, raison: str):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True)
        return
    
    try:
        user_id_int = int(id)
    except ValueError:
        await interaction.response.send_message("❌ L'ID doit être un nombre valide.", ephemeral=True)
        return
    
    try:
        user = await bot.fetch_user(user_id_int)
        await guild.unban(user)
        
        try:
            embed_dm = Embed(
                title="✅ Tu as été débanni",
                description=f"Tu as été **unban** du serveur **{guild.name}**.",
                color=discord.Color.green()
            )
            embed_dm.add_field(name="Raison", value=raison, inline=False)
            embed_dm.set_footer(text=f"Décision prise par {interaction.user}")
            await user.send(embed=embed_dm)
        except:
            pass
        
        # Nettoie toute planification de ban existante pour cet utilisateur/guild
        try:
            keys_to_remove = [k for k, v in scheduled_bans.items() if v.get("user_id") == user.id and v.get("guild_id") == guild.id]
            for k in keys_to_remove:
                scheduled_bans.pop(k, None)
            if keys_to_remove:
                save_scheduled_bans()
        except Exception:
            pass

        embed_success_unban = discord.Embed(
            title="🔓 Membre débanni",
            description=f"{user.mention} a été unban  avec succès.",
            color=discord.Color.green()
        )
        embed_success_unban.add_field(name="Raison", value=raison, inline=False)
        embed_success_unban.set_footer(text=f"Unban demandé par {interaction.user}")
        await interaction.response.send_message(embed=embed_success_unban)
        
    except discord.NotFound:
        await interaction.response.send_message("❌ Utilisateur introuvable ou pas banni.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Je n'ai pas la permission de débannir cet utilisateur.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur inattendue : `{e}`", ephemeral=True)
    
@bot.tree.command(name="mute", description="Mute un membre dans le serveur")
@app_commands.describe(
    membre="Le membre à muter",
    duree="Durée du mute en minutes",
    raison="Raison du mute"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, membre: discord.Member, duree: int, raison: str = "Aucune raison donnée"):
    if membre == interaction.user:
        return await interaction.response.send_message("❌ Tu ne peux pas te mute toi-même.", ephemeral=True)
    if membre.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Tu ne peux pas mute un administrateur.", ephemeral=True)
    # Défère la réponse pour éviter le timeout si on effectue des opérations longues (DM, écriture JSON...)
    try:
        await safe_defer(interaction)
    except Exception:
        # Si la réponse était déjà faite, on ignore
        pass

    muted_role = await get_muted_role(interaction.guild)

    await membre.add_roles(muted_role, reason=raison)
    # Envoie un DM informatif à l'utilisateur
    try:
        dm_embed = discord.Embed(
            title="🔇 Tu as été mute",
            description=f"Tu as été mute sur **{interaction.guild.name}**.",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        dm_embed.add_field(name="Durée", value=f"{duree} minute(s)", inline=True)
        dm_embed.add_field(name="Modérateur", value=str(interaction.user), inline=True)
        dm_embed.add_field(name="Raison", value=raison, inline=False)
        dm_embed.set_footer(text="Si tu penses que c'est une erreur, contacte le staff.")
        await membre.send(embed=dm_embed)
    except Exception:
        # L'utilisateur a probablement désactivé les DMs ou nous a bloqués
        pass

    # Message de confirmation visible en canal
    embed_confirm = discord.Embed(
        title="🔇 Membre mute",
        description=f"{membre.mention} a été mute pour **{duree} min**.",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    embed_confirm.add_field(name="Raison", value=raison, inline=False)
    embed_confirm.set_footer(text=f"Action effectuée par {interaction.user}")
    # Envoi de la confirmation comme followup car on a déferré la réponse
    try:
        await interaction.followup.send(embed=embed_confirm)
    except Exception:
        # Fallback si followup échoue
        try:
            await interaction.response.send_message(embed=embed_confirm)
        except Exception:
            pass

    # Planification persistante de l'unmute (pour tolérer les redémarrages)
    try:
        expiration_ts = int((datetime.datetime.utcnow() + datetime.timedelta(minutes=max(0, duree))).timestamp())
        entry_id = f"{expiration_ts}_{membre.id}"
        scheduled_mutes[entry_id] = {
            "guild_id": interaction.guild.id,
            "user_id": membre.id,
            "reason": raison,
            "expiration": expiration_ts
        }
        save_scheduled_mutes()
    except Exception:
        # En cas d'erreur d'écriture, ne bloque pas l'action
        pass
        
@bot.tree.command(name="unmute", description="Unmute un membre dans le serveur")
@app_commands.describe(membre="Le membre à unmute")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, membre: discord.Member):
    muted_role = await get_muted_role(interaction.guild)
    if muted_role not in membre.roles:
        return await interaction.response.send_message(f"❌ {membre.mention} n'est pas mute.", ephemeral=True)
    await membre.remove_roles(muted_role, reason=f"Unmute demandé par {interaction.user}")

    # DM informatif
    try:
        dm_embed = discord.Embed(
            title="🔊 Tu as été unmute",
            description=f"Tu as été unmute sur **{interaction.guild.name}**.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        dm_embed.add_field(name="Modérateur", value=str(interaction.user), inline=True)
        dm_embed.set_footer(text="Bonne conversation !")
        await membre.send(embed=dm_embed)
    except Exception:
        pass
    # Nettoie toute planification de mute existante pour cet utilisateur/guild
    try:
        keys_to_remove = [k for k, v in scheduled_mutes.items() if v.get("user_id") == membre.id and v.get("guild_id") == interaction.guild.id]
        for k in keys_to_remove:
            scheduled_mutes.pop(k, None)
        if keys_to_remove:
            save_scheduled_mutes()
    except Exception:
        pass

    await interaction.response.send_message(f"✅ {membre.mention} a été unmute", ephemeral=False)

@bot.tree.command(name="warn", description="Donne un avertissement à un membre (log + DM)")
@app_commands.describe(membre="Le membre à avertir", raison="Raison de l'avertissement")
async def warn(interaction: discord.Interaction, membre: discord.Member, raison: str):
    # Vérification manuelle des permissions (évite d'utiliser le décorateur pour éviter les bugs)
    if not getattr(interaction.user, "guild_permissions", None) or not interaction.user.guild_permissions.moderate_members:
        embed_perm = discord.Embed(
            title="Permission refusée",
            description="❌ Vous n'avez pas les permissions requises pour utiliser cette commande.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        return await interaction.response.send_message(embed=embed_perm, ephemeral=True)
    # Empêche d'avertir soi-même ou le propriétaire
    if membre.id == interaction.user.id:
        return await interaction.response.send_message("❌ Tu ne peux pas t'avertir toi-même.", ephemeral=True)
    if membre == interaction.guild.owner:
        return await interaction.response.send_message("❌ Impossible d'avertir le propriétaire du serveur.", ephemeral=True)

    # Vérification des permissions du bot
    if not interaction.guild.me.guild_permissions.send_messages:
        return await interaction.response.send_message("❌ Je n'ai pas la permission d'envoyer des messages.", ephemeral=True)

    # Ajout du warn
    warn_id = add_warning(interaction.guild.id, membre.id, interaction.user.id, raison)

    # Gestion des rôles d'escalade Warn 1 -> Warn 2 -> Ban 7 jours
    try:
        role1 = await get_warn_role(interaction.guild, WARN_ROLE_1_NAME)
        role2 = await get_warn_role(interaction.guild, WARN_ROLE_2_NAME)
        has_role1 = (role1 in membre.roles) if role1 else False
        has_role2 = (role2 in membre.roles) if role2 else False

        # Cas: aucun warn role -> appliquer Warn 1
        if not has_role1 and not has_role2:
            if role1:
                try:
                    await membre.add_roles(role1, reason=f"Warn 1 donné par {interaction.user}")
                except Exception:
                    pass

        # Cas: déjà Warn 1 -> passer à Warn 2
        elif has_role1 and not has_role2:
            try:
                if role1:
                    await membre.remove_roles(role1, reason="Upgrade vers Warn 2")
                if role2:
                    await membre.add_roles(role2, reason=f"Warn 2 donné par {interaction.user}")
            except Exception:
                pass

        # Cas: déjà Warn 2 -> troisième warn = ban temporaire 7 jours
        elif has_role2:
            try:
                duree_jours = 7
                raison_ban = f"3 avertissements atteints — {raison}"
                # Bannir le membre
                await membre.ban(reason=raison_ban)

                # Planifier l'unban dans scheduled_bans
                expiration_ts = int((datetime.datetime.utcnow() + datetime.timedelta(days=duree_jours)).timestamp())
                entry_id = f"{expiration_ts}_{membre.id}"
                scheduled_bans[entry_id] = {
                    "guild_id": interaction.guild.id,
                    "user_id": membre.id,
                    "reason": raison_ban,
                    "expiration": expiration_ts
                }
                save_scheduled_bans()

                # Tentative d'enlever les rôles warn
                try:
                    if role2:
                        await membre.remove_roles(role2, reason="Banni après 3 warns")
                    if role1:
                        await membre.remove_roles(role1, reason="Banni après 3 warns")
                except Exception:
                    pass

                # DM et embed de ban
                try:
                    dm_ban = discord.Embed(
                        title="🔨 Tu as été banni temporairement",
                        description=f"Tu as été banni du serveur **{interaction.guild.name}** pour {duree_jours} jours suite à 3 avertissements.",
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )
                    dm_ban.add_field(name="Raison", value=raison_ban, inline=False)
                    dm_ban.set_footer(text=f"Banni par {interaction.user}")
                    await membre.send(embed=dm_ban)
                except Exception:
                    pass

                embed_ban = discord.Embed(
                    title="🔨 Membre banni (3 warns)",
                    description=f"{membre.mention} a été banni pour {duree_jours} jours après 3 avertissements.",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                embed_ban.add_field(name="Raison", value=raison_ban, inline=False)
                embed_ban.set_footer(text=f"Action effectuée par {interaction.user}")

                return await interaction.response.send_message(embed=embed_ban)
            except Exception as e:
                try:
                    await interaction.response.send_message(f"❌ Impossible de bannir : {e}", ephemeral=True)
                except Exception:
                    pass
    except Exception:
        pass

    # Déterminer niveau actuel pour afficher (Warn 1 / Warn 2)
    try:
        role1 = await get_warn_role(interaction.guild, WARN_ROLE_1_NAME)
        role2 = await get_warn_role(interaction.guild, WARN_ROLE_2_NAME)
        niveau = "Aucun"
        if role2 and role2 in membre.roles:
            niveau = "Warn 2"
        elif role1 and role1 in membre.roles:
            niveau = "Warn 1"
    except Exception:
        niveau = "Inconnu"

    # Envoi DM à l'utilisateur averti (pour les cas non-ban)
    try:
        dm = discord.Embed(
            title="⚠️ Tu as reçu un avertissement",
            description=f"Tu as reçu un avertissement sur **{interaction.guild.name}**.",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        dm.add_field(name="Raison", value=raison, inline=False)
        dm.add_field(name="Modérateur", value=str(interaction.user), inline=True)
        dm.set_footer(text="Respecte les règles du serveur.")
        await membre.send(embed=dm)
    except Exception:
        pass

    # Embed de confirmation en channel
    embed = discord.Embed(
        title="⚠️ Avertissement donné",
        description=f"{membre.mention} a été averti.",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Raison", value=raison, inline=False)
    embed.set_footer(text=f"Avertissement demandé par {interaction.user}")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unwarn", description="Retire un avertissement d'un membre (choisir 1, 2 ou tous)")
@app_commands.describe(membre="Le membre")
async def unwarn(interaction: discord.Interaction, membre: discord.Member):
    # Vérification manuelle des permissions
    if not getattr(interaction.user, "guild_permissions", None) or not interaction.user.guild_permissions.moderate_members:
        embed_perm = discord.Embed(
            title="Permission refusée",
            description="❌ Vous n'avez pas les permissions requises pour utiliser cette commande.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        return await interaction.response.send_message(embed=embed_perm, ephemeral=True)

    # Empêche d'agir sur le propriétaire
    if membre == interaction.guild.owner and interaction.user != interaction.guild.owner:
        return await interaction.response.send_message("❌ Impossible d'agir sur le propriétaire du serveur.", ephemeral=True)

    # Récupère la liste des warns existants
    existing = warnings.get(interaction.guild.id, {}).get(membre.id, [])
    if not existing:
        return await interaction.response.send_message("❌ Cet utilisateur n'a aucun avertissement.", ephemeral=True)

    # Helper pour ajuster les rôles warn selon le nombre de warns restants
    async def adjust_warn_roles(guild: discord.Guild, member: discord.Member):
        try:
            r1 = await get_warn_role(guild, WARN_ROLE_1_NAME)
            r2 = await get_warn_role(guild, WARN_ROLE_2_NAME)
            remaining = warnings.get(guild.id, {}).get(member.id, [])
            count = len(remaining) if remaining else 0
            if count >= 2:
                try:
                    if r1 and r1 in member.roles:
                        await member.remove_roles(r1, reason="Ajustement warns")
                    if r2 and r2 not in member.roles:
                        await member.add_roles(r2, reason="Ajustement warns")
                except Exception:
                    pass
            elif count == 1:
                try:
                    if r2 and r2 in member.roles:
                        await member.remove_roles(r2, reason="Ajustement warns")
                    if r1 and r1 not in member.roles:
                        await member.add_roles(r1, reason="Ajustement warns")
                except Exception:
                    pass
            else:
                try:
                    if r1 and r1 in member.roles:
                        await member.remove_roles(r1, reason="Ajustement warns")
                    if r2 and r2 in member.roles:
                        await member.remove_roles(r2, reason="Ajustement warns")
                except Exception:
                    pass
        except Exception:
            pass

    # Vue interactive avec boutons
    class UnwarnView(discord.ui.View):
        def __init__(self, author_id: int, *, timeout: int = 60):
            super().__init__(timeout=timeout)
            self.author_id = author_id

        async def interaction_check(self, inter: discord.Interaction) -> bool:
            if inter.user.id != self.author_id:
                await inter.response.send_message("❌ Seul l'auteur de la commande peut utiliser ces boutons.", ephemeral=True)
                return False
            return True

        @discord.ui.button(label="Retirer 1 avertissement", style=discord.ButtonStyle.primary)
        async def remove_one(self, interaction_button: discord.Interaction, button: discord.ui.Button):
            e = pop_last_warning(interaction.guild.id, membre.id)
            if not e:
                return await interaction_button.response.send_message("❌ Aucun avertissement à retirer.", ephemeral=True)
            await adjust_warn_roles(interaction.guild, membre)
            # DM
            try:
                remaining = warnings.get(interaction.guild.id, {}).get(membre.id, [])
                count = len(remaining) if remaining else 0
                niveau = "Warn 2" if count >= 2 else ("Warn 1" if count == 1 else "Aucun")
                dm = discord.Embed(
                    title="ℹ️ Un avertissement a été retiré",
                    description=f"Un de tes avertissements sur **{interaction.guild.name}** a été retiré.",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                dm.add_field(name="Modérateur", value=str(interaction.user), inline=True)
                await membre.send(embed=dm)
            except Exception:
                pass
            embed_res = discord.Embed(
                title="ℹ️ Avertissement retiré",
                description=f"1 avertissement de {membre.mention} a été supprimé.",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed_res.set_footer(text=f"Action effectuée par {interaction.user}")
            await interaction_button.response.edit_message(content=None, embed=embed_res, view=None)

        @discord.ui.button(label="Retirer 2 avertissements", style=discord.ButtonStyle.secondary)
        async def remove_two(self, interaction_button: discord.Interaction, button: discord.ui.Button):
            removed_any = False
            for _ in range(2):
                e = pop_last_warning(interaction.guild.id, membre.id)
                if e:
                    removed_any = True
            if not removed_any:
                return await interaction_button.response.send_message("❌ Aucun avertissement à retirer.", ephemeral=True)
            await adjust_warn_roles(interaction.guild, membre)
            try:
                remaining = warnings.get(interaction.guild.id, {}).get(membre.id, [])
                count = len(remaining) if remaining else 0
                niveau = "Warn 2" if count >= 2 else ("Warn 1" if count == 1 else "Aucun")
                dm = discord.Embed(
                    title="ℹ️ Avertissements retirés",
                    description=f"Jusqu'à 2 avertissements ont été retirés pour **{membre}**.",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                dm.add_field(name="Modérateur", value=str(interaction.user), inline=True)
                await membre.send(embed=dm)
            except Exception:
                pass
            embed_res = discord.Embed(
                title="ℹ️ Avertissements retirés",
                description=f"Jusqu'à 2 avertissements de {membre.mention} ont été supprimés.",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            embed_res.set_footer(text=f"Action effectuée par {interaction.user}")
            await interaction_button.response.edit_message(content=None, embed=embed_res, view=None)

        @discord.ui.button(label="Retirer tous les avertissements", style=discord.ButtonStyle.danger)
        async def remove_all(self, interaction_button: discord.Interaction, button: discord.ui.Button):
            try:
                if interaction.guild.id in warnings and membre.id in warnings[interaction.guild.id]:
                    warnings[interaction.guild.id].pop(membre.id, None)
                    if not warnings[interaction.guild.id]:
                        warnings.pop(interaction.guild.id, None)
                    save_warnings()
                    await adjust_warn_roles(interaction.guild, membre)
                    try:
                        dm = discord.Embed(
                            title="ℹ️ Tous les avertissements ont été retirés",
                            description=f"Tous tes avertissements sur **{interaction.guild.name}** ont été retirés.",
                            color=discord.Color.green(),
                            timestamp=discord.utils.utcnow()
                        )
                        dm.add_field(name="Modérateur", value=str(interaction.user), inline=True)
                        await membre.send(embed=dm)
                    except Exception:
                        pass
                    embed_res = discord.Embed(
                        title="ℹ️ Avertissements supprimés",
                        description=f"Tous les avertissements de {membre.mention} ont été supprimés.",
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed_res.set_footer(text=f"Action effectuée par {interaction.user}")
                    await interaction_button.response.edit_message(content=None, embed=embed_res, view=None)
                else:
                    await interaction_button.response.send_message("❌ Aucun avertissement trouvé.", ephemeral=True)
            except Exception:
                await interaction_button.response.send_message("❌ Une erreur est survenue.", ephemeral=True)

    view = UnwarnView(author_id=interaction.user.id)
    try:
        await interaction.response.send_message(f"Quelle action souhaitez-vous effectuer pour {membre.mention} ?", view=view, ephemeral=True)
    except Exception:
        try:
            await interaction.response.send_message("Impossible d'ouvrir la fenêtre interactive.", ephemeral=True)
        except Exception:
            pass


@bot.tree.command(name="warnlist", description="Liste les avertissements (pour un membre ou pour le serveur)")
@app_commands.describe(membre="Le membre (optionnel)")
async def warnlist(interaction: discord.Interaction, membre: discord.Member = None):
    # Restreindre l'utilisation aux modérateurs
    if not getattr(interaction.user, "guild_permissions", None) or not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)

    if not interaction.guild:
        return await interaction.response.send_message("❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True)

    guild_warnings = warnings.get(interaction.guild.id, {})

    # Si un membre est fourni : lister ses warns
    if membre:
        user_warns = guild_warnings.get(membre.id, [])
        if not user_warns:
            return await interaction.response.send_message(f"ℹ️ {membre.mention} n'a aucun avertissement.", ephemeral=True)

        embed = discord.Embed(
            title=f"Avertissements de {membre}",
            description=f"Total : {len(user_warns)}",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        # limiter pour l'affichage
        max_show = 15
        for i, e in enumerate(user_warns[-max_show:], start=max(1, len(user_warns)-max_show+1)):
            mod_id = e.get("moderator_id")
            try:
                moderator = interaction.guild.get_member(mod_id) or await bot.fetch_user(mod_id)
                moderator_display = f"{moderator} ({mod_id})"
            except Exception:
                moderator_display = str(mod_id)
            ts = e.get("timestamp") or 0
            embed.add_field(name=f"#{i} — ID: {e.get('id')}", value=(f"Raison: {e.get('reason')}\nModérateur: {moderator_display}\nDate: <t:{int(ts)}:F>"), inline=False)

        if len(user_warns) > max_show:
            embed.set_footer(text=f"Affichage des {max_show} derniers warns sur {len(user_warns)}")

        return await interaction.response.send_message(embed=embed, ephemeral=True)

    # Sinon : lister un résumé pour le serveur (utilisateurs et compte de warns)
    if not guild_warnings:
        return await interaction.response.send_message("ℹ️ Aucun avertissement enregistré pour ce serveur.", ephemeral=True)

    embed = discord.Embed(
        title=f"Liste des avertissements — {interaction.guild.name}",
        description="Résumé des membres ayant des avertissements",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )

    # Trier par nombre d'avertissements décroissant
    users_sorted = sorted(guild_warnings.items(), key=lambda kv: len(kv[1]) if kv[1] else 0, reverse=True)
    max_users = 20
    for uid, lst in users_sorted[:max_users]:
        try:
            member = interaction.guild.get_member(uid) or await bot.fetch_user(uid)
            name = f"{member}"
        except Exception:
            name = str(uid)
        embed.add_field(name=name, value=f"{len(lst)} avertissement(s)", inline=True)

    if len(users_sorted) > max_users:
        embed.set_footer(text=f"Affichage des {max_users} premiers utilisateurs sur {len(users_sorted)}")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="banlist", description="Affiche les bans actuels et les bans programmés pour le serveur")
@app_commands.describe(membre="Filtre par membre (optionnel, ID ou mention)")
async def banlist(interaction: discord.Interaction, membre: discord.Member = None):
    # Permissions : ban_members ou modération
    if not getattr(interaction.user, "guild_permissions", None) or not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)

    if not interaction.guild:
        return await interaction.response.send_message("❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True)

    embed = discord.Embed(
        title=f"Bans — {interaction.guild.name}",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )

    # Bans actuels
    try:
        bans = await interaction.guild.bans()
    except Exception:
        bans = []

    if membre:
        # Filtrer par membre
        target_id = membre.id
        current_bans = [b for b in bans if getattr(b.user, 'id', None) == target_id]
    else:
        current_bans = bans

    if current_bans:
        val = []
        for b in current_bans[:15]:
            user = b.user
            reason = b.reason or "Aucune raison fournie"
            val.append(f"{user} (`{user.id}`) — {reason}")
        embed.add_field(name="Bans actuels", value="\n".join(val), inline=False)
        if len(current_bans) > 15:
            embed.add_field(name="...", value=f"Et {len(current_bans)-15} autres bans", inline=False)
    else:
        embed.add_field(name="Bans actuels", value="Aucun ban actuel", inline=False)

    # Bans programmés (scheduled_bans)
    scheduled = [v for k, v in scheduled_bans.items() if v.get("guild_id") == interaction.guild.id]
    if membre:
        scheduled = [s for s in scheduled if s.get("user_id") == membre.id]

    if scheduled:
        lines = []
        for s in sorted(scheduled, key=lambda x: x.get("expiration", 0))[:15]:
            uid = s.get("user_id")
            reason = s.get("reason") or "Aucune raison"
            exp = int(s.get("expiration", 0))
            try:
                user = await bot.fetch_user(uid)
                user_display = f"{user} (`{uid}`)"
            except Exception:
                user_display = f"`{uid}`"
            lines.append(f"{user_display} — {reason} — Fin: <t:{exp}:F>")
        embed.add_field(name="Bans programmés", value="\n".join(lines), inline=False)
        if len(scheduled) > 15:
            embed.add_field(name="...", value=f"Et {len(scheduled)-15} autres bans programmés", inline=False)
    else:
        embed.add_field(name="Bans programmés", value="Aucun ban programmé", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------ LANCEMENT DU BOT ------------ # 

bot.run(TOKEN)