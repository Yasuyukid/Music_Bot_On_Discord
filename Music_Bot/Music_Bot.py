import discord, nacl, yt_dlp, logging, asyncio, configparser, os, sys
from discord.ext import commands
from typing import Optional, Callable, Any

command_prefix = "!"
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix = command_prefix, help_command = None, intents = intents)

connect_timeout = 30

voice = None
show_finish = True
queue = []
current_song = 0
voice_volume = 0.75
loop_value = True
auto_skip_value = True

help_message = f"""
{command_prefix}help <optional - page: integer>: Show this help embed.

{command_prefix}connect: Make the bot connect to your voice channel.

{command_prefix}disconnect: Make the bot disconnect from your voice channel.

{command_prefix}add <song url: string> <optional - song position: integer>: Add one or more songs to the queue.

{command_prefix}remove <song position: integer> ...: Remove one or more songs from the queue.


Page 1/{{}}
----------Page separator----------
{command_prefix}clear: Clear the queue.

{command_prefix}show: Show the queue.

{command_prefix}play <optional - song position: integer>: Play a song in the queue.

{command_prefix}stop: Stop the current song.

{command_prefix}pause: Pause the current song.


Page 2/{{}}
----------Page separator----------
{command_prefix}resume: Resume playing the current song.

{command_prefix}next <optional - times: integer>: Play the next song.

{command_prefix}previous <optional - times: integer>: Play the previous song.

{command_prefix}volume <between 0 - 100: integer>: Change the song volume. If no value is provided, the current volume is returned.

{command_prefix}loop <on/off: boolean>: Enable/Disable looping the queue. If no value is provided, the current value of loop is returned.


Page 3/{{}}
----------Page separator----------
{command_prefix}auto_skip <on/off: boolean>: Enable/Disable auto-skip to the next song in the queue. If no value is provided, the current value of auto-skip is returned.


Page 4/{{}}
"""

path = os.path.dirname(sys.argv[0])
config_file_path = os.path.join(path, "config.ini")

config = configparser.ConfigParser(strict = True)
config.read(config_file_path)
ffmpeg_path = config.get("config", "ffmpeg_path")
opus_dll_path = config.get("config", "opus_dll_path")
token = config.get("config", "token")

try:
    discord.opus.load_opus(opus_dll_path)
except:
    pass

logger = logging.Logger("yt_dlp")
logger.addHandler(logging.NullHandler())

youtubeDl_options = {
    "format": "bestaudio/best",
    "quiet": True,
    "logger": logger
}

ffmpeg_options = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}

@bot.event
async def on_ready() -> None:
    print(f"{bot.user} just sucessfully connected with discord.")

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
    global voice, show_finish

    if member != bot.user:
        return

    if before.channel and not after.channel and voice:
        show_finish = False
        await voice.disconnect()
        voice = None
    elif before.channel and after.channel and voice.is_playing():
        show_finish = False

        await play_message.channel.send("The song stopped because I was moved to another voice channel.")

@bot.command()
async def help(message: discord.Message, *args) -> None:
    if len(args) == 0:
        help_message_list = help_message.split("----------Page separator----------")
        await message.channel.send(embed = discord.Embed(title = "All available commands", description = help_message_list[0].format(len(help_message_list)), color = 0x0064ff))
    elif len(args) == 1:
        try:
            arg = int(args[0])
            help_message_list = help_message.split("----------Page separator----------")

            if arg < 1 or arg > len(help_message_list):
                await message.reply(f"Invalid page number: {arg}.")
                return

            await message.channel.send(embed = discord.Embed(title = "All available commands", description = help_message_list[arg - 1].format(len(help_message_list)), color = 0x0064ff))
        except ValueError:
            await message.reply(f"Invalid page number: {args[0]}.")
    else:
        await message.reply("Invalid command.")

def finish(error: Callable[[Optional[Exception]], Any]) -> None:
    global play_message, show_finish, current_song

    if not show_finish:
        show_finish = True
        return

    if not auto_skip_value:
        asyncio.run_coroutine_threadsafe(play_message.channel.send("I just finished the song."), bot.loop)
        return

    if current_song == len(queue) - 1:
        current_song = 0
        if loop_value:
            task = asyncio.run_coroutine_threadsafe(play_message.channel.send("I just finished the queue, now looping the queue again..."), bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(play_message.channel.send("I just finished the queue."), bot.loop)
            return
    else:
        current_song += 1
        task = asyncio.run_coroutine_threadsafe(play_message.channel.send("I just finished the song, start playing the next one..."), bot.loop)

    while not task.done():
        pass

    voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[current_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = finish)
    asyncio.run_coroutine_threadsafe(play_message.channel.send(f"Now playing **#{current_song + 1} | {queue[current_song]['title']}** ({format_time(queue[current_song]['duration'])})."), bot.loop)

def format_time(time_in_second: int) -> None:
    if time_in_second >= 3600:
        hours = time_in_second // 3600
        minutes = (time_in_second - hours * 3600) // 60
        seconds = time_in_second - minutes * 60 - hours * 3600

        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        minutes = time_in_second // 60
        seconds = time_in_second - minutes * 60

        return f"{minutes}:{seconds:02d}"

@bot.command()
async def connect(message: discord.Message) -> None:
    global voice

    if not message.author.voice:
        await message.reply("You must connect to a voice channel first.")
        return

    channel = message.author.voice.channel

    if not voice:
        voice = await channel.connect(timeout = connect_timeout)
        await message.reply("I just connected to your voice channel.")
    elif channel == voice.channel:
        await message.reply("I've already connected to your voice channel.")
    else:
        await message.reply("I'm currently in another voice channel, you must disconnect first.")

@bot.command()
async def disconnect(message: discord.Message) -> None:
    global voice, show_finish

    if not voice:
        await message.reply("I'm not connected to any voice channel.")
        return

    show_finish = False
    await voice.disconnect()
    voice = None

    await message.reply("I just disconnected from your voice channel.")

@bot.command()
async def add(message: discord.Message, *args) -> None:
    global current_song

    if len(args) == 0 or len(args) > 2:
        await message.reply("Invalid command.")
        return

    try:
        with yt_dlp.YoutubeDL(youtubeDl_options) as song_url:
            file_or_playlist_info = song_url.extract_info(args[0], download = False)
    except yt_dlp.DownloadError as error:
        await message.reply(f"{'Invalid song url' if 'is not a valid URL' in error.msg else 'Failed to add the song url'}: {args[0]}.")
        return

    infos = file_or_playlist_info.get("entries", [file_or_playlist_info])
    add_index = len(queue) + 1
    if len(args) == 2:
        try:
            song_pos = float(args[1])

            if song_pos != int(song_pos):
                await message.reply(f"Invalid song position: {song_pos}.")
                return

            song_pos = int(song_pos)
        except ValueError:
            await message.reply(f"Invalid song position: {args[1]}.")
            return

        if song_pos < 1 or song_pos > len(queue) + 1:
            await message.reply(f"Invalid song position: {song_pos}.")
            return

        add_index = song_pos
        queue[song_pos - 1:song_pos - 1] = infos
        current_song += len(infos) if song_pos <= current_song + 1 and len(queue) != 1 else 0
    else:
        queue.extend(infos)

    await message.reply(f"Song{'s' if len(infos) >= 2 else ''} added:\n" + "\n".join([f"Song **#{add_index + index} | {info['title']}** ({format_time(info['duration'])}) added." for index, info in enumerate(infos)]))

@bot.command()
async def remove(message: discord.Message, *args) -> None:
    global current_song

    if len(args) == 0:
        await message.reply("Invalid command.")
        return

    removed_song_positions = []
    removed_song_messages = []
    for arg in args:
        try:
            arg = int(arg)
        except ValueError:
            removed_song_messages.append(f"Invalid song position: {arg}.")
            break

        if arg in removed_song_positions:
            removed_song_messages.append(f"Already removed the song at position {arg}.")
            break

        index_offset = sum([(1 if arg > removed_song_position else 0) for removed_song_position in removed_song_positions])
        arg -= index_offset

        if arg < 1 or arg > len(queue):
            removed_song_messages.append(f"Invalid song position: {arg + index_offset}.")
            break
        elif arg == current_song + 1 and voice and voice.is_playing():
            removed_song_messages.append(f"Cannot remove the song at position {arg + index_offset} because it's playing.")
            break
        else:
            title = queue[arg - 1]["title"]
            duration = queue[arg - 1]["duration"]

            if arg <= current_song + 1:
                current_song -= 1
            queue.pop(arg - 1)
            removed_song_positions.append(arg + index_offset)

            removed_song_messages.append(f"Song **#{removed_song_positions[-1]} | {title}** ({format_time(duration)}) removed.")
    else:
        await message.reply(f"Song{'s' if len(removed_song_messages) - 1 >= 2 else ''} removed:\n" + "\n".join(removed_song_messages))
        return

    await message.reply(f"Song{'s' if len(removed_song_messages) >= 2 else ''} removed:\n" + "\n".join(removed_song_messages))

@bot.command()
async def clear(message: discord.Message) -> None:
    global show_finish, current_song, queue

    if voice and voice.is_playing():
        show_finish = False
        voice.stop()

    queue = []
    current_song = 0

    await message.reply("Queue cleared.")

@bot.command()
async def show(message: discord.Message) -> None:
    await message.reply("There are no songs in the queue." if len(queue) == 0 else "Song queue:\n" + "\n".join([f"**#{index + 1} | {info['title']}** ({format_time(info['duration'])}){'  <-- Current song.' if index == current_song else '.'}" for index, info in enumerate(queue)]))

@bot.command()
async def play(message: discord.Message, *args) -> None:
    global play_message, show_finish, current_song

    if not voice:
        await message.reply("I'm not connected to any voice channel.")
        return

    if len(queue) == 0:
        await message.reply("There are no songs in the queue.")
        return
    elif len(args) > 1:
        await message.reply("Invalid command.")
        return

    if len(queue) == 0:
        await message.reply("You haven't added any song.")
        return

    if voice.is_playing():
        show_finish = False
        voice.stop()

    if len(args) == 1:
        try:
            arg = int(args[0])
        except:
            await message.reply(f"Invalid song position: {args[0]}.")
            return

        if arg < 1 or arg > len(queue):
            await message.reply(f"Invalid song position: {arg}.")
        else:
            current_song = arg - 1

    play_message = message

    voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[current_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = finish)
    await message.reply(f"Now playing **#{current_song + 1} | {queue[current_song]['title']}** ({format_time(queue[current_song]['duration'])}).")

@bot.command()
async def stop(message: discord.Message) -> None:
    global show_finish

    if not voice:
        await message.reply("I'm not connected to any voice channel.")
        return

    if voice.is_playing() or voice.is_paused():
        show_finish = False
        voice.stop()

        await message.reply("Song stopped.")
        return

    await message.reply("You haven't played any song.")

@bot.command()
async def pause(message: discord.Message) -> None:
    if not voice:
        await message.reply("I'm not connected to any voice channel.")
        return

    if voice.is_playing():
        voice.pause()
        await message.reply("Song paused.")
    elif voice.is_paused():
        await message.reply("Song is already paused.")
    else:
        await message.reply("You haven't played any song.")

@bot.command()
async def resume(message: discord.Message) -> None:
    if not voice:
        await message.reply("I'm not connected to any voice channel.")
        return

    if not voice.is_playing():
        if voice.is_paused():
            voice.resume()
            await message.reply("Song resumed.")
            return

        await message.reply("You haven't played any song.")
        return

    await message.reply("Song is already playing.")

@bot.command()
async def next(message: discord.Message, *args) -> None:
    global play_message, show_finish, current_song

    if not voice:
        await message.reply("I'm not connected to any voice channel.")
        return
    elif len(queue) == 0:
        await message.reply("There are no songs in the queue.")
        return
    elif len(args) > 1:
        await message.reply("Invalid command.")
        return

    if len(args) == 0:
        current_song = 0 if current_song == len(queue) - 1 else current_song + 1
    else:
        try:
            arg = int(args[0])
        except ValueError:
            await message.reply(f"Invalid times: {args[0]}.")
            return

        if arg <= 0:
            await message.reply(f"The provided times, {arg}, must be greater than 0.")
            return

        current_song = min(current_song + arg, len(queue) - 1)

    if voice.is_playing():
        show_finish = False
        voice.stop()

    play_message = message

    voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[current_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = finish)
    await message.reply(f"Now playing **#{current_song + 1} | {queue[current_song]['title']}** ({format_time(queue[current_song]['duration'])}).")

@bot.command()
async def previous(message: discord.Message, *args) -> None:
    global play_message, show_finish, current_song

    if not voice:
        await message.reply("I'm not connected to any voice channel.")
        return
    elif len(queue) == 0:
        await message.reply("There are no songs in the queue.")
        return
    elif len(args) > 1:
        await message.reply("Invalid command.")
        return

    if len(args) == 0:
        current_song = len(queue) - 1 if current_song == 0 else current_song - 1
    else:
        try:
            arg = int(args[0])
        except ValueError:
            await message.reply(f"Invalid times: {args[0]}.")
            return

        if arg <= 0:
            await message.reply(f"The provided times, {arg}, must be greater than 0.")
            return

        current_song = max(current_song - arg, 0)

    if voice.is_playing():
        show_finish = False
        voice.stop()

    play_message = message

    voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[current_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = finish)
    await message.reply(f"Now playing **#{current_song + 1} | {queue[current_song]['title']}** ({format_time(queue[current_song]['duration'])}).")

@bot.command()
async def volume(message: discord.Message, *args) -> None:
    global voice_volume

    if len(args) > 1:
        await message.reply("Invalid command.")
        return
    elif len(args) == 0:
        await message.reply(f"The current volume is {int(voice_volume * 100)}.")
        return

    try:
        arg = float(args[0])

        if arg != int(arg):
            await message.reply(f"Invalid volume: {arg}.")
            return

        arg = int(arg)
    except ValueError:
        await message.reply(f"Invalid volume: {args[0]}.")
        return

    if arg < 0 or arg > 100:
        await message.reply(f"The provided volume, {arg}, must be between 0 and 100.")
        return

    voice_volume = arg / 100
    if voice and voice.is_playing():
        voice.source.volume = voice_volume

    await message.reply("Volume changed.")

@bot.command()
async def loop(message: discord.Message, *args) -> None:
    global loop_value

    if len(args) > 1:
        await message.reply("Invalid command.")
        return
    elif len(args) == 0:
        await message.reply(f"The current value of loop is {'on' if loop_value else 'off'}.")
        return

    arg = args[0].lower()
    if arg != "on" and arg != "off":
        await message.reply(f"Invalid value: {arg}.")
        return

    loop_value = True if arg == "on" else False
    await message.reply("Value updated.")

@bot.command()
async def auto_skip(message: discord.Message, *args) -> None:
    global auto_skip_value

    if len(args) > 1:
        await message.reply("Invalid command.")
        return
    elif len(args) == 0:
        await message.reply(f"The current value of auto-skip is {'on' if auto_skip_value else 'off'}.")
        return

    arg = args[0].lower()
    if arg != "on" and arg != "off":
        await message.reply(f"Invalid value: {arg}.")
        return

    auto_skip_value = True if arg == "on" else False
    await message.reply("Value updated.")

if __name__ == "__main__" :
    bot.run(token)
