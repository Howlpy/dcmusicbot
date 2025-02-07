import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os


# Configuración inicial
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cola de reproducción
queues = {}

def get_queue(guild_id):
    return queues.setdefault(guild_id, asyncio.Queue())

# Comando para unirse al canal de voz
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        try:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.send(f"Me uní al canal: {channel}")
        except discord.ClientException as e:
            await ctx.send(f"Error al unirme al canal: {e}")
    else:
        await ctx.send("¡Debes estar en un canal de voz para usar este comando!")

# Comando para salir del canal de voz
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        try:
            await ctx.voice_client.disconnect()
            await ctx.send("Me desconecté del canal.")
        except discord.ClientException as e:
            await ctx.send(f"Error al desconectarme: {e}")
    else:
        await ctx.send("No estoy en ningún canal de voz.")

# Comando para añadir canciones a la cola
@bot.command()
async def play(ctx, *, search: str):
    guild_id = ctx.guild.id
    queue = get_queue(guild_id)

    # Descarga de audio con yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': 'True',
        'quiet': True,
        'default_search': 'ytsearch',
        'extractaudio': False,
        'source_address': '0.0.0.0',
        'socket_timeout': 10,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search, download=False)
            url = info['entries'][0]['url'] if 'entries' in info else info['url']
            title = info['entries'][0]['title'] if 'entries' in info else info['title']

        await queue.put((url, title))
        await ctx.send(f"🎶 Añadido a la cola: **{title}**")

        # Si no se está reproduciendo nada, comienza a reproducir
        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            await play_next(ctx)

    except yt_dlp.utils.DownloadError as e:
        await ctx.send(f"Error al procesar el video: {e}")
    except Exception as e:
        await ctx.send(f"Ocurrió un error inesperado: {e}")

async def play_next(ctx):
    guild_id = ctx.guild.id
    queue = get_queue(guild_id)

    if not queue.empty():
        url, title = await queue.get()

        # Opciones de FFmpeg
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        try:
            ctx.voice_client.play(
                discord.FFmpegPCMAudio(url, **ffmpeg_options),
                after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            )
            await ctx.send(f"🎵 Reproduciendo: **{title}**")
        except discord.ClientException as e:
            await ctx.send(f"Error al reproducir: {e}")
        except Exception as e:
            await ctx.send(f"Ocurrió un error inesperado durante la reproducción: {e}")
    else:
        await ctx.send("La cola está vacía.")

# Comando para ver la lista de reproducción
@bot.command()
async def queue(ctx):
    guild_id = ctx.guild.id
    queue = get_queue(guild_id)

    if queue.empty():
        await ctx.send("La cola está vacía.")
    else:
        songs = list(queue._queue)
        message = "\n".join([f"**{i+1}.** {song[1]}" for i, song in enumerate(songs)])
        await ctx.send(f"🎶 **Cola de reproducción:**\n{message}")

# Evento de inicio
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# Token del bot (reemplázalo con tu token)
bot.run(os.getenv("DISCORD_TOKEN"))
