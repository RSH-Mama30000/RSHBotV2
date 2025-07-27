# ------------ DÉPENDANCES (import, from) ------------

import discord
import yt_dlp
import platform
import random
import os

from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv

# ------------ CONFIGURATION ------------

load_dotenv(r"Bot Discord/RSHBot/tokv2.env")
OWNER_ID = 979806223580926013
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True   
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
 
# ------------ DONNÉES POUR /commande ------------ 
  
categories = {
    "musique": {
        "▶️ Jouer": {"description": "Joue de la musique dans un salon vocal.", "syntax": "/jouer [URL]"},
        "⏹️ Arrêter": {"description": "Arrête la musique en cours.", "syntax": "/arrêter"},
        "📥 Rejoindre": {"description": "Fait rejoindre le bot dans un salon vocal.", "syntax": "/rejoindre"},
        "📤 Quitter": {"description": "Quitte le salon vocal.", "syntax": "/quitter"},
    },
    "jeux_fun": {       
        "🎁 Boîte Mystère": {"description": "Ouvre une boîte mystère pour découvrir une récompense aléatoire.", "syntax": "/boitemystere"},
        "🪙 Pile ou Face": {"description": "Lance une pièce pour jouer à Pile ou Face.", "syntax": "/pileouface"},
        "🔮 EightBall": {"description": "Pose une question et reçois une réponse aléatoire.", "syntax": "/eightball"},
    },
    "utilitaires": {
        "ℹ️ Bot Info": {"description": "Affiche des informations sur le bot.", "syntax": "/botinfo"},
        "🗣️ Dire": {"description": "Fait dire quelque chose au bot.", "syntax": "/dire [message]"},
        "🧹 Effacer": {"description": "Efface un certain nombre de messages.", "syntax": "/effacer [nombre]"},
        "🖼️ Avatar": {"description": "Affiche la photo de profil d'un utilisateur.", "syntax": "/avatar [ID discord]"},
        "📡 Latence": {"description": "Voir la latence du bot.", "syntax": "/latence"},
    },
    "discussion": {
        "👋 Bonjour": {"description": "Envoyer des salutations.", "syntax": "/bonjour"},
        "🔥 Morton": {"description": "Tu connais le dicton !", "syntax": "/morton"},
    }   
}

display_names = {
    "musique": "🎵 Musique",
    "jeux_fun": "🎮 Jeux & Fun",
    "utilitaires": "🛠️ Utilitaires",
    "discussion": "💬 Discussion"
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

# ------------ ÉVÉNEMENTS ------------

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="Version 1.0.0"),
        status=discord.Status.online
    )   
    try:
        synced = await bot.tree.sync()
        print(f"🤖 {len(synced)} commandes slash synchronisées.")
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation des commandes slash : {e}")
    
# ------------ COMMANDES SLASH ------------
    
@bot.tree.command(name="commande", description="Affiche les commandes d'une catégorie")
@app_commands.choices(
    catégorie=[
        app_commands.Choice(name="🎵 Musique", value="musique"),
        app_commands.Choice(name="🎮 Jeux & Fun", value="jeux_fun"),
        app_commands.Choice(name="🛠️ Utilitaires", value="utilitaires"),
        app_commands.Choice(name="💬 Discussion", value="discussion"),
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

    embed.set_footer(text="RSHBotV2 • Que des slashs commandes 💻", icon_url=bot.user.display_avatar.url)
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
    
    await interaction.response.send_message("✅ Salut patron ! Si tu souhaites voir mon code c'est sur ce discord et après tu as déjà les permissions de voir le salon ! https://discord.gg/mfVvt3j2By", ephemeral=True)
    
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
    embed.add_field(name="🖥️ Version", value="1.0.0", inline=True)
    embed.add_field(name="🐍 Langage du bot", value="Python 3.13.5", inline=True)
    embed.add_field(name="📅 Date de création", value="30/05/2025 22h13", inline=True)
    embed.add_field(name="👨‍💻 Développeur", value="Pour avoir toutes les informations /equipe", inline=True)
    embed.add_field(name="📛 Nom du bot", value="RSHBotV2", inline=True)
    embed.add_field(name="🔢 ID du bot", value="1354844575168204840", inline=True)
    embed.add_field(name="Tu veux rejoindre l'équipe ?", value="Si oui ouvre un https://discord.com/channels/1310182105577426994/1343343848004386867 !", inline=False)
    embed.timestamp = discord.utils.utcnow()
    
    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="dire", description="Permet de dire quelque chose sous l'identité de RSHBotV2.")
@app_commands.describe(message="Le message à envoyer sous l'identité de RSHBotV2.")
async def dire(interaction: discord.Interaction, message: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande !", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    await interaction.channel.send(message)
    
@bot.tree.command(name="effacer", description="Supprime un nombre de messages récents.")
@app_commands.describe(nombre="Nombre de messages à supprimer (1 à 500)")
async def effacer(interaction: discord.Interaction, nombre: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande !", ephemeral=True)
        return

    if nombre <= 0 or nombre > 500:
        await interaction.response.send_message("❌ Veuillez entrer un nombre entre 1 et 500.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    deleted = await interaction.channel.purge(limit=nombre)

    await interaction.followup.send(f"✅ {len(deleted)} messages ont été supprimés.", ephemeral=True)
    
@bot.tree.command(name="avatar", description="Voir la photo de profil d'un utilisateur de votre choix grâce à son ID.")
@app_commands.describe(id="ID de la personne que vous voulez voir la photo de profil.")
async def avatar(interaction: discord.Interaction, id: str):
    try:
        user = await bot.fetch_user(id)
        if user.avatar:
            embed = discord.Embed(title=f"Voici l'avatar de {user.name}", color=discord.Color.red())
            embed.set_image(url=user.avatar.url)
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
    responses = [
        "Oui !", "Non", "Peut-être...", "Je ne sais pas", "Bien sur", "Je ne pense pas...", "Absolument !", "Jamais !"
    ]
    answer = random.choice(responses)
    await interaction.response.send_message(f"Question : {question}\nRéponse : {answer}")
    
# ------------ MUSIQUE ------------    
    
@bot.tree.command(name="rejoindre", description="Le bot rejoint le vocal dans lequel tu te trouves.")
async def rejoindre(interaction: discord.Interaction):
    if interaction.user.voice and interaction.user.voice.channel:
        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        try:
            await interaction.response.defer()  # Délai de réponse

            if voice_client and voice_client.is_connected():
                if voice_client.channel.id == channel.id:
                    await interaction.followup.send(f"Je suis déjà dans le salon vocal : **{channel.name}**")
                else:
                    await voice_client.move_to(channel)
                    await interaction.followup.send(f"Je me déplace vers le salon vocal : **{channel.name}**")
            else:
                await channel.connect()
                await interaction.followup.send(f"Je rejoins le salon vocal : **{channel.name}**")

        except Exception as e:
            await interaction.followup.send(f"Je n'ai pas pu rejoindre le salon vocal : {e}", ephemeral=True)
    else:
        await interaction.response.send_message("Tu dois être dans un salon vocal pour que je puisse te rejoindre.", ephemeral=True)
        
@bot.tree.command(name="quitter", description="Le bot quitte le vocal dans lequel il se trouve.")
async def quitter(interaction: discord.Interaction):
    if interaction.user.bot:
        return 

    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        await interaction.response.send_message("Je quitte le salon vocal.")
        print(f"[INFO] Déconnexion vocale du bot dans la guilde: {interaction.guild.name}")
    else:
        await interaction.response.send_message("Je ne suis pas dans un salon vocal.")

@bot.tree.command(name="jouer", description="Jouer de la musique depuis une URL")
@app_commands.describe(url="URL de la musique à jouer")
async def jouer(interaction: discord.Interaction, url: str):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Tu dois être dans un canal vocal pour utiliser cette commande.")
        return

    await interaction.response.defer()

    channel = interaction.user.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if voice_client is None:
        voice_client = await channel.connect()
    else:
        await voice_client.move_to(channel)

    if voice_client.is_playing():
        voice_client.stop()

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            audio_url = info['url']
            title = info.get('title', 'Musique inconnue')
    except Exception as e:
        await interaction.followup.send(f"Impossible de lire la musique : {e}", ephemeral=True)
        return

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
    voice_client.play(source)

    await interaction.followup.send(f"🎵 Je joue : **{title}**")

@bot.tree.command(name='arreter', description='Arrêter la musique')
async def arreter(interaction: discord.Interaction):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Tu dois être dans un salon vocal pour arrêter la musique.", ephemeral=True)
        return

    if voice_client and voice_client.is_connected():
        if voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("🛑 Musique arrêtée.")
        else:
            await interaction.response.send_message("Aucune musique n'est en cours de lecture.", ephemeral=True)
            
    else:
        await interaction.response.send_message("Je ne suis connecté à aucun salon vocal.", ephemeral=True)
      
# ------------ LANCEMENT DU BOT ------------

bot.run(TOKEN)
