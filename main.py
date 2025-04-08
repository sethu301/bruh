# main.py
import discord
from discord.ext import commands, tasks
import os
from keep_alive import keep_alive
import yt_dlp
import asyncio
from collections import deque

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!!", intents=intents)

song_queue = deque()
auto_disconnect_enabled = True
idle_disconnect_delay = 300  # 5 minutes

def get_audio_url(search):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'cookiefile': 'cookies.txt',
        'default_search': 'ytsearch',
        'extract_flat': 'in_playlist'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        return info['url'], info['title']

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    check_idle.start()

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.send("🔊 Joined your voice channel!")
    else:
        await ctx.send("❌ You're not in a voice channel!")

@bot.command()
async def leave(ctx):
    global song_queue
    song_queue.clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left the voice channel.")
    else:
        await ctx.send("❌ I'm not connected to any voice channel.")

async def play_next(ctx):
    global song_queue
    vc = ctx.voice_client
    if not vc or not song_queue:
        return

    url, title = song_queue.popleft()
    ffmpeg_options = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
    }

    vc.play(discord.FFmpegPCMAudio(url, **ffmpeg_options),
            after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
    await ctx.send(f"🎶 Now playing: **{title}**")

@bot.command()
async def play(ctx, *, song):
    global song_queue
    url, title = get_audio_url(song)

    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ You're not in a voice channel!")
            return

    vc = ctx.voice_client
    if not vc.is_playing():
        song_queue.appendleft((url, title))
        await play_next(ctx)
    else:
        song_queue.append((url, title))
        await ctx.send(f"📥 Added to queue: **{title}**")

@bot.command()
async def queue(ctx, *, song):
    global song_queue
    url, title = get_audio_url(song)
    song_queue.append((url, title))
    await ctx.send(f"📥 Added to queue: **{title}**")

@bot.command()
async def showqueue(ctx):
    if not song_queue:
        await ctx.send("📭 The queue is empty.")
    else:
        queue_list = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(song_queue)])
        await ctx.send(f"🎶 **Upcoming Songs:**\n{queue_list}")

@bot.command()
async def persist(ctx):
    global auto_disconnect_enabled
    auto_disconnect_enabled = False
    await ctx.send("🔁 24/7 mode enabled. I will not auto-disconnect.")

@bot.command()
async def autopilot(ctx):
    global auto_disconnect_enabled
    auto_disconnect_enabled = True
    await ctx.send("🕐 Auto-disconnect after 5 mins of inactivity is enabled.")

@tasks.loop(seconds=60)
async def check_idle():
    if not auto_disconnect_enabled:
        return

    for vc in bot.voice_clients:
        if not vc.is_playing() and not song_queue:
            if hasattr(vc, 'idle_counter'):
                vc.idle_counter += 60
            else:
                vc.idle_counter = 60

            if vc.idle_counter >= idle_disconnect_delay:
                await vc.disconnect()
        else:
            vc.idle_counter = 0

@bot.command()
async def watch(ctx, *, channel_name=None):
    youtube_streams = {
        "asianet news": "https://www.youtube.com/watch?v=Ko18SgceYX8",
        "news 18 kerala": "https://www.youtube.com/watch?v=Jo1rbrweS5s",
        "manorama news": "https://www.youtube.com/watch?v=tgBTspqA5nY",
        "janam tv": "https://www.youtube.com/watch?v=9Txa0xfXRdg",
        "mediaone news": "https://www.youtube.com/watch?v=-8d8-c0yvyU",
        "24 news": "https://www.youtube.com/watch?v=1wECsnGZcfc",
        "reporter news": "https://www.youtube.com/watch?v=HGOiuQUwqEw",
        "kairali news": "https://www.youtube.com/watch?v=wq0ecjkN3G8",
        "mathrubhumi news": "https://www.youtube.com/watch?v=YGEgelAiUf0"
    }

    if channel_name is None or channel_name.lower() not in youtube_streams:
        await ctx.send("❗ Please provide a valid channel name. Use `!!channels` to see available channels.")
        return

    url, _ = get_audio_url(youtube_streams[channel_name.lower()])

    if ctx.voice_client is None:
        if ctx.author.voice:
            vc = await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ You're not in a voice channel!")
            return
    else:
        vc = ctx.voice_client

    ffmpeg_options = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
    }

    vc.stop()
    vc.play(discord.FFmpegPCMAudio(url, **ffmpeg_options))
    await ctx.send(f"📺 Now streaming: **{channel_name.upper()}**")

@bot.command()
async def radio(ctx, *, station=None):
    radio_stations = {
        "radiomirchi": "https://www.youtube.com/watch?v=Lamuk5Jc2Cc",
        "clubfm": "https://www.youtube.com/watch?v=T15lWGwu994",
        "radiocity": "https://www.youtube.com/watch?v=s7i3SVbUdzA",
        "redfm": "https://www.youtube.com/watch?v=4yR5_RcRZ7k",
        "radiomango": "https://www.youtube.com/watch?v=xuohrKlWeJ8"
    }

    if station is None or station.lower() not in radio_stations:
        await ctx.send("❗ Please provide a valid radio station. Use `!!stations` to see the list.")
        return

    url, _ = get_audio_url(radio_stations[station.lower()])

    if ctx.voice_client is None:
        if ctx.author.voice:
            vc = await ctx.author.voice.channel.connect()
        else:
            await ctx.send("❌ You're not in a voice channel!")
            return
    else:
        vc = ctx.voice_client

    ffmpeg_options = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
    }

    vc.stop()
    vc.play(discord.FFmpegPCMAudio(url, **ffmpeg_options))
    await ctx.send(f"📻 Now playing: **{station.upper()} FM**")

@bot.command()
async def channels(ctx):
    fancy_channel_list = """
📺 **Available Malayalam TV Channels** 📺
━━━━━━━━━━━━━━━━━━━━━━
🔹 asianet news
🔹 news 18 kerala
🔹 manorama news
🔹 janam tv
🔹 mediaone news
🔹 24 news
🔹 reporter news
🔹 kairali news
🔹 mathrubhumi news
━━━━━━━━━━━━━━━━━━━━━━
Use `!!watch <channel>` to stream!
    """
    await ctx.send(fancy_channel_list)

@bot.command()
async def stations(ctx):
    fancy_station_list = """
🎧 **Available Malayalam FM Stations** 🎧
━━━━━━━━━━━━━━━━━━━━━━
🎵 radiomirchi
🎵 clubfm
🎵 radiocity
🎵 redfm
🎵 radiomango
━━━━━━━━━━━━━━━━━━━━━━
Use `!!radio <station>` to play!
    """
    await ctx.send(fancy_station_list)

@bot.command()
async def commands(ctx):
    help_text = """
✨✨✨ **BOT COMMANDS PANEL** ✨✨✨
━━━━━━━━━━━━━━━━━━━━━━
🎙️ `!!join` → Join your voice channel  
👋 `!!leave` → Leave the voice channel  
📺 `!!watch <channel>` → Watch Malayalam TV live  
📻 `!!radio <station>` → Listen to Malayalam FM Radio  
📝 `!!channels` → Show all available TV channels  
🎶 `!!stations` → Show all available FM stations  
🎵 `!!play <song>` → Play music or add to queue  
➕ `!!queue <song>` → Add music to the queue  
📋 `!!showqueue` → View the current queue  
🔁 `!!24/7` → Prevent auto-disconnect from VC  
🕐 `!!autopilot` → Enable auto-disconnect after 5 mins  
💡 `!!commands` → Show this help panel  
━━━━━━━━━━━━━━━━━━━━━━
Enjoy! 😎 Made by Sethu. FUCK **NIGGERS!! I do not associate with NIGGERS!!**
    """
    await ctx.send(help_text)

keep_alive()
bot.run(os.environ["DISCORD_TOKEN"])
