import os
import discord
from discord.ext import commands
import asyncio
import random
import requests
import logging
from flask import Flask, jsonify
import threading
import time
from datetime import datetime
import yt_dlp
import re

TOKEN = os.environ.get('DISCORD_TOKEN', '')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', 'AIzaSyAQIum9S1_I-K3nKBkhXL7OjGuvZ5HQrx8')
GOOGLE_CX = os.environ.get('GOOGLE_CX', 'd34dddde8063b48ed')
STATUS_UPDATE_INTERVAL = 60
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000

PRESENCE_MESSAGES = [
    "!aide pour les commandes",
    "Service 24/7",
    "À votre service !",
    "Prêt à aider !"
]

ERROR_MESSAGES = {
    'general': "Une erreur s'est produite lors du traitement de votre demande.",
    'missing_permissions': "Je n'ai pas les permissions nécessaires pour exécuter cette commande.",
    'user_missing_permissions': "Vous n'avez pas les permissions nécessaires pour utiliser cette commande.",
    'command_not_found': "Commande introuvable. Utilisez !aide pour voir les commandes disponibles.",
    'api_error': "Une erreur s'est produite lors de la connexion à une API externe.",
    'no_voice_channel': "Vous devez être dans un salon vocal pour utiliser cette commande.",
    'invalid_url': "L'URL fournie n'est pas valide ou n'est pas prise en charge.",
    'download_error': "Impossible de télécharger l'audio depuis cette URL.",
    'voice_connection_error': "Impossible de se connecter au salon vocal.",
    'no_music_playing': "Aucune musique n'est en cours de lecture."
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('discord_bot')

bot_start_time = time.time()
last_heartbeat = time.time()
command_count = 0
error_count = 0

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
            if 'entries' in data:
                data = data['entries'][0]
            filename = data['url'] if stream else ytdl.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction audio de {url}: {e}")
            raise


music_players = {}


def update_heartbeat():
    global last_heartbeat
    last_heartbeat = time.time()


def increment_command():
    global command_count
    command_count += 1


def increment_error():
    global error_count
    error_count += 1


def get_uptime():
    uptime_seconds = time.time() - bot_start_time
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
    if hours > 0:
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    if minutes > 0:
        return f"{int(minutes)}m {int(seconds)}s"
    return f"{int(seconds)}s"


def is_bot_alive():
    return time.time() - last_heartbeat < 60


async def send_error_message(ctx, error_type='general'):
    error_message = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES['general'])
    embed = discord.Embed(
        title="❌ Erreur",
        description=error_message,
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)


intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    logger.info(f"{bot.user.name} est en ligne ! ID: {bot.user.id}")
    activity = discord.Activity(type=discord.ActivityType.playing, name="!aide for commands")
    await bot.change_presence(activity=activity)
    bot.loop.create_task(status_task(bot))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)


async def status_task(bot):
    while True:
        try:
            status = random.choice(PRESENCE_MESSAGES)
            activity = discord.Activity(type=discord.ActivityType.playing, name=status)
            await bot.change_presence(activity=activity)
        except Exception as e:
            logger.error(f"Erreur lors du changement de statut : {e}")
        await asyncio.sleep(STATUS_UPDATE_INTERVAL)


@bot.command(name="ping")
async def cmd_ping(ctx):
    increment_command()
    update_heartbeat()
    try:
        latency = round(ctx.bot.latency * 1000)
        await ctx.send(f"Pong! 🏓 Latence : {latency}ms")
    except Exception as e:
        logger.error(f"Erreur dans la commande ping : {e}")
        await send_error_message(ctx)


@bot.command(name="hello")
async def cmd_hello(ctx):
    increment_command()
    update_heartbeat()
    try:
        await ctx.send(f"Salut {ctx.author.mention} ! 👋")
    except Exception as e:
        logger.error(f"Erreur dans la commande hello : {e}")
        await send_error_message(ctx)


@bot.command(name="uptime")
async def cmd_uptime(ctx):
    increment_command()
    update_heartbeat()
    try:
        uptime_str = get_uptime()
        embed = discord.Embed(
            title="⏱️ Temps de fonctionnement",
            description=f"Je fonctionne depuis : **{uptime_str}**",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Erreur dans la commande uptime : {e}")
        await send_error_message(ctx)


@bot.command(name="serveur")
async def cmd_serveur(ctx):
    increment_command()
    update_heartbeat()
    try:
        guild = ctx.guild
        if not guild:
            await ctx.send("Cette commande doit être utilisée dans un serveur.")
            return
        embed = discord.Embed(
            title=guild.name,
            description="📊 Infos du serveur",
            color=discord.Color.blue()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="👥 Membres", value=guild.member_count)
        embed.add_field(name="📅 Créé le", value=guild.created_at.strftime("%d/%m/%Y"))
        embed.add_field(name="👑 Propriétaire", value=guild.owner)
        embed.add_field(name="💬 Salons", value=len(guild.channels))
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Erreur dans la commande serveur : {e}")
        await send_error_message(ctx)


@bot.command(name="userinfo")
async def cmd_userinfo(ctx, member: discord.Member = None):
    increment_command()
    update_heartbeat()
    try:
        member = member or ctx.author
        roles = [role.name for role in member.roles if role.name != "@everyone"]
        embed = discord.Embed(
            title=f'Informations sur {member}',
            color=discord.Color.green()
        )
        embed.add_field(name='Nom', value=member.name, inline=True)
        embed.add_field(name='ID', value=member.id, inline=True)
        embed.add_field(name='Status', value=str(member.status), inline=True)
        embed.add_field(name='Rejoint le', value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name='Compte créé le', value=member.created_at.strftime("%d/%m/%Y"), inline=True)
        if roles:
            embed.add_field(name=f'Rôles [{len(roles)}]', value=', '.join(roles), inline=False)
        else:
            embed.add_field(name='Rôles', value='Aucun', inline=False)
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Erreur dans la commande userinfo : {e}")
        await send_error_message(ctx)


@bot.command(name="avatar")
async def cmd_avatar(ctx, member: discord.Member = None):
    increment_command()
    update_heartbeat()
    try:
        member = member or ctx.author
        if member.avatar:
            embed = discord.Embed(
                title=f"Avatar de {member.name}",
                color=discord.Color.purple()
            )
            embed.set_image(url=member.avatar.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{member.name} n'a pas d'avatar personnalisé.")
    except Exception as e:
        logger.error(f"Erreur dans la commande avatar : {e}")
        await send_error_message(ctx)


@bot.command(name="dog")
async def cmd_dog(ctx):
    increment_command()
    update_heartbeat()
    try:
        response = requests.get("https://dog.ceo/api/breeds/image/random")
        if response.status_code == 200:
            data = response.json()
            dog_image = data['message']
            embed = discord.Embed(
                title="🐶 Chien aléatoire",
                color=discord.Color.gold()
            )
            embed.set_image(url=dog_image)
            await ctx.send(embed=embed)
        else:
            logger.error(f"L'API Dog a retourné le code {response.status_code}")
            await send_error_message(ctx, 'api_error')
    except Exception as e:
        logger.error(f"Erreur dans la commande dog : {e}")
        await send_error_message(ctx)


@bot.command(name="rock")
async def cmd_rock(ctx):
    increment_command()
    update_heartbeat()
    try:
        if not GOOGLE_API_KEY or not GOOGLE_CX:
            await ctx.send("⚠️ Configuration de l'API Google manquante. Configurez les clés API.")
            return
        search_url = f"https://www.googleapis.com/customsearch/v1?q=rock&searchType=image&key={GOOGLE_API_KEY}&cx={GOOGLE_CX}"
        response = requests.get(search_url)
        if response.status_code == 200:
            data = response.json()
            if "items" in data:
                rock_images = [item['link'] for item in data['items']]
                random_rock = random.choice(rock_images)
                embed = discord.Embed(
                    title="🪨 Rocher aléatoire",
                    color=discord.Color.dark_gray()
                )
                embed.set_image(url=random_rock)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Impossible de récupérer une image de rocher. 😢")
        else:
            logger.error(f"L'API Google a retourné le code {response.status_code}")
            await send_error_message(ctx, 'api_error')
    except Exception as e:
        logger.error(f"Erreur dans la commande rock : {e}")
        await send_error_message(ctx)


FUNNY_VERSES = [
    ("Douce est la brise, chaude est ta cousine.",
     "https://media.discordapp.net/attachments/1353859086478999582/1353864315903672330/1_3.png?ex=67e333e6&is=67e1e266&hm=b977b3ffe83d648ee6ec1101850d6334a6f3ad4df6c67dd87f7534dba15d46ed&=&format=webp&quality=lossless"),
    ("Le ciel est clair, mais ton père me prend par l'arrière.",
     "https://media.discordapp.net/attachments/1353859086478999582/1353864339752489081/1_10.png?ex=67e333ec&is=67e1e26c&hm=1a5727c54e560fd5340691b40e880f6ae549d954bd3680f9ef23c51b2a758995&=&format=webp&quality=lossless"),
    ("Douce est la rivière, bonne est ta mère.",
     "https://media.discordapp.net/attachments/1353859086478999582/1353864341199388712/1_15.png?ex=67e333ec&is=67e1e26c&hm=9111e1b1b14e1aad9142c3e157daa9607357610ca0fbccf069fbd563b46ae840&=&format=webp&quality=lossless"),
    ("La nuit est ardente, comme ton ex sous ma tente.",
     "https://media.discordapp.net/attachments/1353859086478999582/1353864340113068123/1_11.png?ex=67e333ec&is=67e1e26c&hm=9836bef139d2c37e0abb188c73dd4babb22a8bf49c974a8b455c251b858e500c&=&format=webp&quality=lossless"),
    ("Belle est la fleur, bonne est ta sœur, j'en ai rien à faire qu'elle soit mineure.",
     "https://media.discordapp.net/attachments/1353859086478999582/1353864315228131338/1_1.png?ex=67e333e6&is=67e1e266&hm=631e11306bdc38d0a9552959aef98024524385daa565df997ee5e8fe913eb48d&=&format=webp&quality=lossless"),
    ("Il vaut mieux manger un hachis parmentier que manger le sperme d'Achille en entier.",
     "https://media.discordapp.net/attachments/1353859086478999582/1353864314854834268/1_9.png?ex=67e333e6&is=67e1e266&hm=b844f4115784ae6608ec0ad96683690f32c16821ae50b4c27984b49de8cd3cac&=&format=webp&quality=lossless"),
    ("Douce est la caresse, maintenant envoie tes fesses.",
     "https://media.discordapp.net/attachments/1353859086478999582/1353864317690445844/1_8.png?ex=67e333e6&is=67e1e266&hm=f4c2c53044bd4e4986877782ac76e5c319234ff34b03b74fb99b1a2e604e40a3&=&format=webp&quality=lossless"),
    ("Faut mieux ranger la classe avec des cloisons que de manger la chiasse de Gaston.",
     "https://media.discordapp.net/attachments/1353859086478999582/1353864340637487195/1_13.png?ex=67e333ec&is=67e1e26c&hm=d763d81e44f913760ef6047773219618a1c8958d73136fb2e9b61e4cb4ff7bb7&=&format=webp&quality=lossless"),
    ("Celui qui se branle au vent fait la bise à ses enfants.",
     "https://media.discordapp.net/attachments/1353859086478999582/1353864316935471134/1_6.png?ex=67e333e6&is=67e1e266&hm=4c114138bb7fef799eec6977adcc647d453337e1e4e99dc5814852a52f0c102a&=&format=webp&quality=lossless"),
]


@bot.command(name="proverbe")
async def cmd_proverbe(ctx):
    increment_command()
    update_heartbeat()
    try:
        verse, image_url = random.choice(FUNNY_VERSES)
        embed = discord.Embed(
            title="📜 Proverbe Chinois",
            description=verse,
            color=discord.Color.gold()
        )
        embed.set_image(url=image_url)
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Erreur dans la commande verse : {e}")
        await send_error_message(ctx)


@bot.command(name="aide")
async def cmd_aide(ctx):
    increment_command()
    update_heartbeat()
    try:
        embed = discord.Embed(
            title="📚 Liste des commandes",
            description="Voici les commandes disponibles :",
            color=discord.Color.red()
        )
        embed.add_field(name="!ping", value="Affiche la latence du bot", inline=True)
        embed.add_field(name="!hello", value="Le bot vous dit bonjour", inline=True)
        embed.add_field(name="!uptime", value="Affiche le temps d'exécution du bot", inline=True)
        embed.add_field(name="!serveur", value="Informations sur le serveur", inline=True)
        embed.add_field(name="!userinfo [utilisateur]", value="Informations sur un utilisateur", inline=True)
        embed.add_field(name="!avatar [utilisateur]", value="Affiche l'avatar d'un utilisateur", inline=True)
        embed.add_field(name="!dog", value="Affiche une image aléatoire de chien", inline=True)
        embed.add_field(name="!rock", value="Affiche une image aléatoire de rocher", inline=True)
        embed.add_field(name="!proverbe", value="Affiche un proverbe chinois aléatoire", inline=True)
        embed.add_field(name="!stats", value="Affiche les statistiques du bot", inline=True)
        embed.add_field(name="!play [url/recherche]", value="Joue de la musique depuis YouTube", inline=True)
        embed.add_field(name="!stop", value="Arrête la lecture et quitte le salon vocal", inline=True)
        embed.add_field(name="!pause", value="Met en pause la lecture", inline=True)
        embed.add_field(name="!resume", value="Reprend la lecture", inline=True)
        embed.add_field(name="!nowplaying", value="Affiche la musique en cours de lecture", inline=True)
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Erreur dans la commande aide : {e}")
        await send_error_message(ctx)


@bot.command(name="stats")
async def cmd_stats(ctx):
    increment_command()
    update_heartbeat()
    try:
        uptime_str = get_uptime()
        embed = discord.Embed(
            title="📊 Statistiques du Bot",
            color=discord.Color.blue()
        )
        embed.add_field(name="⏱️ Temps d'exécution", value=uptime_str, inline=True)
        embed.add_field(name="💬 Commandes traitées", value=str(command_count), inline=True)
        embed.add_field(name="❌ Erreurs", value=str(error_count), inline=True)
        embed.add_field(name="📊 Latence", value=f"{round(ctx.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="🤖 Status", value="En ligne" if is_bot_alive() else "Problèmes", inline=True)
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Erreur dans la commande stats : {e}")
        await send_error_message(ctx)


@bot.command(name="play")
async def cmd_play(ctx, *, query=None):
    increment_command()
    update_heartbeat()
    try:
        if not query:
            await ctx.send("Veuillez spécifier une URL YouTube ou un terme de recherche.")
            return

        if not ctx.author.voice:
            await send_error_message(ctx, 'no_voice_channel')
            return

        voice_channel = ctx.author.voice.channel

        if not re.match(r'https?://', query):
            query = f"ytsearch:{query}"

        voice_client = ctx.voice_client
        if voice_client is None:
            try:
                voice_client = await voice_channel.connect()
            except Exception as e:
                logger.error(f"Erreur lors de la connexion au salon vocal: {e}")
                await send_error_message(ctx, 'voice_connection_error')
                return
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)

        loading_message = await ctx.send("⏳ Chargement de la musique...")

        try:
            async with ctx.typing():
                player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
                voice_client.play(player, after=lambda e: print(f'Erreur de lecture: {e}') if e else None)

            embed = discord.Embed(
                title="🎵 Lecture en cours",
                description=f"[{player.title}]({player.url})",
                color=discord.Color.green()
            )
            await loading_message.edit(content=None, embed=embed)

            music_players[ctx.guild.id] = {
                'title': player.title,
                'url': player.url,
                'start_time': time.time()
            }

        except Exception as e:
            logger.error(f"Erreur lors du téléchargement de l'audio: {e}")
            await loading_message.delete()
            await send_error_message(ctx, 'download_error')
            if voice_client and not voice_client.is_playing():
                await voice_client.disconnect()
    except Exception as e:
        logger.error(f"Erreur dans la commande play: {e}")
        await send_error_message(ctx)


@bot.command(name="stop")
async def cmd_stop(ctx):
    increment_command()
    update_heartbeat()
    try:
        voice_client = ctx.voice_client
        if voice_client is None:
            await send_error_message(ctx, 'no_music_playing')
            return

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
            await voice_client.disconnect()

            if ctx.guild.id in music_players:
                del music_players[ctx.guild.id]

            embed = discord.Embed(
                title="⏹️ Musique arrêtée",
                description="J'ai quitté le salon vocal.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            await send_error_message(ctx, 'no_music_playing')
    except Exception as e:
        logger.error(f"Erreur dans la commande stop: {e}")
        await send_error_message(ctx)


@bot.command(name="pause")
async def cmd_pause(ctx):
    increment_command()
    update_heartbeat()
    try:
        voice_client = ctx.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            embed = discord.Embed(
                title="⏸️ Musique en pause",
                description="Utilisez `!resume` pour reprendre la lecture.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            await send_error_message(ctx, 'no_music_playing')
    except Exception as e:
        logger.error(f"Erreur dans la commande pause: {e}")
        await send_error_message(ctx)


@bot.command(name="resume")
async def cmd_resume(ctx):
    increment_command()
    update_heartbeat()
    try:
        voice_client = ctx.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            embed = discord.Embed(
                title="▶️ Lecture reprise",
                description="La musique reprend.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await send_error_message(ctx, 'no_music_playing')
    except Exception as e:
        logger.error(f"Erreur dans la commande resume: {e}")
        await send_error_message(ctx)


@bot.command(name="nowplaying", aliases=["np"])
async def cmd_nowplaying(ctx):
    increment_command()
    update_heartbeat()
    try:
        voice_client = ctx.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            if ctx.guild.id in music_players:
                player_info = music_players[ctx.guild.id]
                duration = time.time() - player_info['start_time']
                minutes, seconds = divmod(int(duration), 60)

                status = "▶️ En lecture" if voice_client.is_playing() else "⏸️ En pause"
                embed = discord.Embed(
                    title=status,
                    description=f"[{player_info['title']}]({player_info['url']})",
                    color=discord.Color.green() if voice_client.is_playing() else discord.Color.orange()
                )
                embed.add_field(name="⏱️ Durée de lecture", value=f"{minutes}:{seconds:02d}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("Lecture en cours, mais les détails ne sont pas disponibles.")
        else:
            await send_error_message(ctx, 'no_music_playing')
    except Exception as e:
        logger.error(f"Erreur dans la commande nowplaying: {e}")
        await send_error_message(ctx)


@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == bot.user.id and after.channel is None:
        guild = member.guild
        if guild.id in music_players:
            del music_players[guild.id]
            logger.info(f"Déconnecté du salon vocal dans {guild.name}, informations de lecture supprimées.")

    if member.id != bot.user.id and before.channel and not after.channel:
        voice_client = member.guild.voice_client
        if voice_client and voice_client.channel == before.channel:
            members = [m for m in before.channel.members if not m.bot]
            if not members:
                await asyncio.sleep(120)
                members = [m for m in voice_client.channel.members if not m.bot]
                if not members:
                    await voice_client.disconnect()
                    if member.guild.id in music_players:
                        del music_players[member.guild.id]
                    logger.info(f"Déconnecté du salon vocal dans {member.guild.name} car seul dans le canal.")


app = Flask(__name__)


@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        'status': 'online' if is_bot_alive() else 'offline',
        'uptime': get_uptime(),
        'commands_processed': command_count,
        'errors': error_count,
        'last_heartbeat': int(last_heartbeat)
    })


def run_flask():
    app.run(host=FLASK_HOST, port=FLASK_PORT)


def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    bot.run(TOKEN)


if __name__ == "__main__":
    main()
