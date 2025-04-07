# main.py
import discord
from discord.ext import commands
import os
from keep_alive import keep_alive
import yt_dlp

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("🔊 Joined your voice channel!")
    else:
        await ctx.send("❌ You're not in a voice channel!")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Left the voice channel.")
    else:
        await ctx.send("❌ I'm not connected to any voice channel.")

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

    url = youtube_streams[channel_name.lower()]

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'extract_flat': 'in_playlist',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

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
    vc.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options))
    await ctx.send(f"📺 Now streaming: **{channel_name.upper()}**")

@bot.command()
async def radio(ctx, *, station=None):
    radio_stations = {
        "radiomirchi": "https://www.youtube.com/watch?v=0u7YFG1xgjs",
        "clubfm": "https://www.youtube.com/watch?v=G_4D8dNmh3c",
        "radiocity": "https://www.youtube.com/watch?v=wD3UudcAMsQ",
        "redfm": "https://www.youtube.com/watch?v=8Mw26FFtGEM",
        "radiomango": "https://www.youtube.com/watch?v=WBoNfi0XKqU"
    }

    if station is None or station.lower() not in radio_stations:
        await ctx.send("❗ Please provide a valid radio station. Use `!!stations` to see the list.")
        return

    url = radio_stations[station.lower()]

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'extract_flat': 'in_playlist',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

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
    vc.play(discord.FFmpegPCMAudio(audio_url, **ffmpeg_options))
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
💡 `!!commands` → Show this stylish help panel
━━━━━━━━━━━━━━━━━━━━━━
Enjoy! 😎
    """
    await ctx.send(help_text)

keep_alive()
bot.run(os.environ["DISCORD_TOKEN"])
