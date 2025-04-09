import discord
from discord.ext import commands, tasks
import os
from keep_alive import keep_alive
import yt_dlp
import asyncio
import time
import random
from collections import deque

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!!", intents=intents)

song_queue = deque()
auto_disconnect_enabled = True
idle_disconnect_delay = 300  # 5 minutes
stream_cache = {}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X)",
    "Mozilla/5.0 (Windows NT 6.1; WOW64)",
]

def get_audio_url(search):
    user_agent = random.choice(USER_AGENTS)
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'cookiefile': 'cookies.txt',
        'default_search': 'ytsearch',
        'extract_flat': 'in_playlist',
        'user_agent': user_agent,
        'sleep_interval_requests': 2,
        'sleep_interval': 2,
        'max_sleep_interval': 4,
        'ratelimit': 512000,
        'retries': 3,
    }

    try:
        cookie_age = os.path.getmtime('cookies.txt')
        age = time.time() - cookie_age
        if age > 604800:  # 7 days
            print("⚠️ Your cookies.txt is older than 7 days. You may face 403 or 429 errors.")
    except Exception as e:
        print(f"⚠️ Could not check cookie age: {e}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(search, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            return info['url'], info['title'], user_agent
        except Exception as e:
            print(f"❌ Error fetching audio URL: {e}")
            return None, "Unknown Title", user_agent

def get_cached_audio_url(name, search):
    now = time.time()
    if name in stream_cache and now - stream_cache[name]['time'] < 300:
        return stream_cache[name]['url'], stream_cache[name]['title'], stream_cache[name]['user_agent']
    url, title, user_agent = get_audio_url(search)
    if url:
        stream_cache[name] = {'url': url, 'title': title, 'time': now, 'user_agent': user_agent}
    return url, title, user_agent

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    check_idle.start()

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        try:
            await ctx.author.voice.channel.connect()
            await ctx.send("🔊 Joined your voice channel!")
        except discord.ClientException:
            await ctx.send("⚠️ Already connected to a voice channel.")
        except Exception as e:
            await ctx.send(f"❌ Failed to connect: {e}")
    else:
        await ctx.send("<a:exclamation_point:872425113235128322> You're not in a voice channel!")

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

    url, title, user_agent = song_queue.popleft()
    try:
        ffmpeg_options = {
            "before_options": (
                f"-headers \"User-Agent: {user_agent}\\r\\n"
                "Cookie: " + open('cookies.txt').read().replace('\n', '') + "\\r\\n\" "
                "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            ),
            "options": "-vn"
        }
        vc.play(discord.FFmpegPCMAudio(url, **ffmpeg_options),
                after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f"🎶 Now playing: **{title}**")
    except Exception as e:
        await ctx.send(f"❌ Playback failed for **{title}**: {e}")
        await play_next(ctx)

@bot.command()
async def play(ctx, *, song):
    global song_queue
    url, title, user_agent = get_audio_url(song)
    if url is None:
        await ctx.send("❌ Could not fetch the song. Try again later.")
        return

    if ctx.voice_client is None:
        if ctx.author.voice:
            try:
                await ctx.author.voice.channel.connect()
            except Exception as e:
                await ctx.send(f"❌ Failed to connect: {e}")
                return
        else:
            await ctx.send("❌ You're not in a voice channel!")
            return

    vc = ctx.voice_client
    if not vc.is_playing():
        song_queue.appendleft((url, title, user_agent))
        await play_next(ctx)
    else:
        song_queue.append((url, title, user_agent))
        await ctx.send(f"📥 Added to queue: **{title}**")

@bot.command()
async def queue(ctx, *, song):
    global song_queue
    url, title, user_agent = get_audio_url(song)
    if url is None:
        await ctx.send("❌ Could not fetch the song. Try again later.")
        return
    song_queue.append((url, title, user_agent))
    await ctx.send(f"📥 Added to queue: **{title}**")

@bot.command()
async def showqueue(ctx):
    if not song_queue:
        await ctx.send("📭 The queue is empty.")
    else:
        queue_list = "\n".join([f"{i+1}. {title}" for i, (_, title, _) in enumerate(song_queue)])
        await ctx.send(f"🎶 **Upcoming Songs:**\n{queue_list}")

@bot.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ Paused.")

@bot.command()
async def resume(ctx):
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ Resumed.")

@bot.command()
async def stop(ctx):
    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop()
        await ctx.send("⏹️ Stopped.")

@bot.command()
async def skip(ctx):
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("⏭️ Skipped.")

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
    url, title, user_agent = get_cached_audio_url(channel_name.lower(), youtube_streams[channel_name.lower()])
    if url is None:
        await ctx.send("❌ Could not fetch stream URL. Try again later.")
        return
    if ctx.voice_client is None:
        if ctx.author.voice:
            try:
                vc = await ctx.author.voice.channel.connect()
            except Exception as e:
                await ctx.send(f"❌ Failed to connect: {e}")
                return
        else:
            await ctx.send("❌ You're not in a voice channel!")
            return
    else:
        vc = ctx.voice_client
    ffmpeg_options = {
        "before_options": (
            f"-headers \"User-Agent: {user_agent}\\r\\n"
            "Cookie: " + open('cookies.txt').read().replace('\n', '') + "\\r\\n\" "
            "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        ),
        "options": "-vn"
    }
    vc.stop()
    try:
        vc.play(discord.FFmpegPCMAudio(url, **ffmpeg_options))
        await ctx.send(f"📺 Now streaming: **{channel_name.upper()}**")
    except Exception as e:
        await ctx.send(f"❌ Playback failed: {e}")

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
    url, title, user_agent = get_cached_audio_url(station.lower(), radio_stations[station.lower()])
    if url is None:
        await ctx.send("❌ Could not fetch stream URL. Try again later.")
        return
    if ctx.voice_client is None:
        if ctx.author.voice:
            try:
                vc = await ctx.author.voice.channel.connect()
            except Exception as e:
                await ctx.send(f"❌ Failed to connect: {e}")
                return
        else:
            await ctx.send("<a:exclamation_point:872425113235128322> You're not in a voice channel!")
            return
    else:
        vc = ctx.voice_client
    ffmpeg_options = {
        "before_options": (
            f"-headers \"User-Agent: {user_agent}\\r\\n"
            "Cookie: " + open('cookies.txt').read().replace('\n', '') + "\\r\\n\" "
            "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        ),
        "options": "-vn"
    }
    vc.stop()
    try:
        vc.play(discord.FFmpegPCMAudio(url, **ffmpeg_options))
        await ctx.send(f"📻 Now playing: **{station.upper()} FM**")
    except Exception as e:
        await ctx.send(f"<a:exclamation_point:872425113235128322> Playback failed: {e}")

@bot.command()
async def channels(ctx):
    await ctx.send("""📺 **Available Malayalam TV Channels** 📺\n━━━━━━━━━━━━━━━━━━━━━━\n🔹 asianet news\n🔹 news 18 kerala\n🔹 manorama news\n🔹 janam tv\n🔹 mediaone news\n🔹 24 news\n🔹 reporter news\n🔹 kairali news\n🔹 mathrubhumi news\n━━━━━━━━━━━━━━━━━━━━━━\nUse `!!watch <channel>` to stream!""")

@bot.command()
async def stations(ctx):
    await ctx.send("""🎧 **Available Malayalam FM Stations** 🎧\n━━━━━━━━━━━━━━━━━━━━━━\n🎵 radiomirchi\n🎵 clubfm\n🎵 radiocity\n🎵 redfm\n🎵 radiomango\n━━━━━━━━━━━━━━━━━━━━━━\nUse `!!radio <station>` to play!""")

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
⏸️ `!!pause` → Pause playback
▶️ `!!resume` → Resume playback
⏹️ `!!stop` → Stop playback
⏭️ `!!skip` → Skip to next in queue
🔁 `!!persist` → Prevent auto-disconnect from VC
🕐 `!!autopilot` → Enable auto-disconnect after 5 mins
💡 `!!commands` → Show this help panel
━━━━━━━━━━━━━━━━━━━━━━
Enjoy! 😎 Made by Sethu
"""
    await ctx.send(help_text)

keep_alive()
bot.run(os.environ["DISCORD_TOKEN"])
