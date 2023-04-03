import discord, yt_dlp, logging, asyncio, nacl, configparser, datetime, os, sys
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix = "!", help_command = None, intents = intents)

voice = None
show_finish = True

queue = []
current_song = 0
voice_volume = 0.75
loop = True
auto_skip = True

total_page_number = 4
help_message = f"""
!help <optinal - page: integer>: Show this help embed.

!join: Make the bot join your voice chat.

!disconnect: Make the bot leave your voice chat.

!add <url: string> <optinal - song position: integer>: Add an url into the queue.

!remove <song position: integer>: Remove an url from the queue.


Page 1/{total_page_number}
----------Page separator----------
!clear: Clear the queue.

!show: Show the queue.

!play <optinal - song position: integer>: Make the bot play song that's in the queue.

!stop: Stop the song.

!pause: Pause the song.


Page 2/{total_page_number}
----------Page separator----------
!resume: Continue playing the song.

!next <optinal - times: integer>: Play the next song.

!previous <optinal - times: integer>: Play the previous song.

!volume <between 0 - 100: integer>: Change the song volume.

!loop <on/off: boolean>: Loop playing the song.


Page 3/{total_page_number}
----------Page separator----------
!auto_skip <on/off: boolean>: Auto skip to the next song in the queue.


Page 4/{total_page_number}
"""

path = os.path.dirname(sys.argv[0])
config_file_path = os.path.join(path, "config.ini")

config = configparser.ConfigParser(strict = True)
config.read(config_file_path)
ffmpeg_path = config.get("config", "ffmpeg_path")
TOKEN = config.get("config", "token")

logger = logging.Logger("yt_dlp")
logger.addHandler(logging.NullHandler())

youtubeDl_options = {
    "format": "bestaudio/best",
    "restrictfilenames": True,
    "noplaylist": True,
    "quiet": True,
    "logger": logger
}

ffmpeg_options = {
    "options": "-vn",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}

@bot.event
async def on_ready():
    print(f"{bot.user} just sucessfully connected with discord!")

@bot.command()
async def help(message, *args):
    if len(args) == 0:
        help_message_list = help_message.split("----------Page separator----------")

        help_embed = discord.Embed(title = "All available commands!", description = help_message_list[0], color = 0x0064ff)
        await message.channel.send(embed = help_embed)
    elif len(args) == 1:
        args = list(args)

        try:
            args[0] = int(args[0])
            help_message_list = help_message.split("----------Page separator----------")

            if args[0] < 1 or args[0] > len(help_message_list):
                await message.reply("Invalid page number!")
            else:
                help_embed = discord.Embed(title = "All available commands!", description = help_message_list[args[0] - 1], color = 0x0064ff)
                await message.channel.send(embed = help_embed)
        except ValueError:
            await message.reply("Invalid page number!")
    else:
        await message.reply("Invalid command!")

def finish(message):
    global show_finish, current_song

    if show_finish:
        if auto_skip:
            if current_song == len(queue) - 1:
                current_song = 0

                if loop:
                    task = asyncio.run_coroutine_threadsafe(message.channel.send("I just finished the queue, now looping the queue again...!"), bot.loop)
                else:
                    asyncio.run_coroutine_threadsafe(message.channel.send("I just finished the queue!"), bot.loop)
                    return
            else:
                current_song += 1

                task = asyncio.run_coroutine_threadsafe(message.channel.send("I just finished the song, starting next one...!"), bot.loop)
            
            while not task.done():
                pass

            voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[current_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = lambda placeholder: finish(message))
            voice.source.volume = voice_volume

            title = queue[current_song]["title"]
            duration = queue[current_song]["duration"]
            asyncio.run_coroutine_threadsafe(message.channel.send(f"Now playing **#{current_song + 1} | {title}** ({format_time(duration)})!"), bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(message.channel.send("I just finished the song!"), bot.loop)
    else:
        show_finish = True

def format_time(time_in_second):
    formated_time = datetime.timedelta(seconds = time_in_second)

    if time_in_second >= 3600:
        formated_time = f"{formated_time.days * 24 + formated_time.seconds // 3600}:{(formated_time.seconds % 3600) // 60:02}:{formated_time.seconds % 60:02}"
    else:
        formated_time = f"{(formated_time.seconds % 3600) // 60}:{formated_time.seconds % 60:02}"

    return formated_time

@bot.command()
async def join(message):
    global voice

    if message.author.voice:
        channel = message.author.voice.channel

        if not voice:
            voice = await channel.connect()
            await message.reply("I just connected to your voice channel!")
        else:
            await message.reply("I'm current in another voice channel, you must disconnect first!")
    else:
        await message.reply("You must connect to a voice channel first!")

@bot.command()
async def disconnect(message):
    global voice, show_finish

    if voice:
        show_finish = False
        await voice.disconnect()
        voice = None

        await message.reply("Disconnected!")
    else:
        await message.reply("I'm not connected to any voice channel!")

@bot.command()
async def add(message, *args):
    global current_song

    if len(args) == 0 or len(args) > 2:
        await message.reply("Invalid command!")
        return

    try:
        with yt_dlp.YoutubeDL(youtubeDl_options) as ytdlp:
            info = ytdlp.extract_info(args[0], download = False)
    except yt_dlp.DownloadError:
        await message.reply("Invalid url!")
        return
    
    if len(args) == 2:
        try:
            song_pos = float(args[1])

            if song_pos != int(song_pos):
                await message.reply("Invalid song position!")
                return
            else:
                song_pos = int(song_pos)
        except ValueError:
            await message.reply("Invalid song position!")
            return
        
        if song_pos < 1 or song_pos > len(queue) + 1:
            await message.reply("Invalid song position!")
        else:
            queue.insert(song_pos - 1, info)

            if song_pos <= current_song + 1 and len(queue) != 1:
                current_song += 1
    else:
        queue.append(info)

    title = info["title"]
    duration = info["duration"]
    await message.reply(f"Song **#{len(queue) if len(args) == 1 else song_pos} | {title}** ({format_time(duration)}) added!")

@bot.command()
async def remove(message, *args):
    global current_song

    if len(args) == 1:
        args = list(args)

        try:
            args[0] = int(args[0])
        except ValueError:
            await message.reply("You must enter an integer!")
            return
        
        if args[0] < 1 or args[0] > len(queue):
            await message.reply("Invalid song position!")
        else:
            if args[0] == current_song + 1:
                await message.reply("Cannot remove the song that's playing!")
            elif args[0] > current_song + 1:
                remove_title = queue[args[0] - 1]["title"]
                remove_duration = queue[args[0] - 1]["duration"]

                queue.pop(args[0] - 1)

                await message.reply(f"Song **#{args[0]} | {remove_title}** ({format_time(remove_duration)}) removed!")
            elif args[0] < current_song + 1:
                remove_title = queue[args[0] - 1]["title"]
                remove_duration = queue[args[0] - 1]["duration"]

                current_song -= 1
                queue.pop(args[0] - 1)

                await message.reply(f"Song **#{args[0]} | {remove_title}** ({format_time(remove_duration)}) removed!")
    else:
        await message.reply("Invalid command!")

@bot.command()
async def clear(message):
    global show_finish, current_song, queue

    if voice:
        if voice.is_playing():
            show_finish = False
            voice.stop()

        queue = []
        current_song = 0

        await message.reply("Queue cleared!")
    else:
        queue = []
        current_song = 0

        await message.reply("Queue cleared!")

@bot.command()
async def show(message):
    if len(queue) == 0:
        await message.reply("There are no songs in the queue!")
    else:
        queue_name = []

        for order, info in enumerate(queue):
            title = info["title"]
            duration = info["duration"]

            if order != current_song:
                queue_name.append(f"**#{queue.index(info) + 1} | {title}** ({format_time(duration)})")
            else:
                queue_name.append(f"**#{queue.index(info) + 1} | {title}** ({format_time(duration)})  <-- Current song.")

        await message.reply("Song queue:\n" + "\n".join(queue_name))

@bot.command()
async def play(message, *args):
    global show_finish, current_song

    if voice:
        if len(queue) == 0:
            await message.reply("There are no songs in the queue!")
            return
        elif len(args) > 1:
            await message.reply("Invalid command!")
            return

        if len(queue) > 0:
            if voice.is_playing():
                show_finish = False
                voice.stop()
            
            if len(args) == 1:
                args = list(args)

                try:
                    args[0] = int(args[0])
                except:
                    await message.reply("You must enter an integer!")
                    return
                
                if args[0] < 1 or args[0] > len(queue):
                    await message.reply("Invalid song position!")
                else:
                    current_song = args[0] - 1

            voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[current_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = lambda placeholder: finish(message))
            voice.source.volume = voice_volume

            title = queue[current_song]["title"]
            duration = queue[current_song]["duration"]
            await message.reply(f"Now playing **#{current_song + 1} | {title}** ({format_time(duration)})!")
        else:
            await message.reply("You haven't added any song!")
    else:
        await message.reply("I'm not connected to any voice channel!")

@bot.command()
async def stop(message):
    global show_finish

    if voice:
        if voice.is_playing():
            show_finish = False
            voice.stop()

            await message.reply("Song stopped!")
        elif not voice.is_paused():
            await message.reply("You haven't played any song!")
    else:
        await message.reply("I'm not connected to any voice channel!")

@bot.command()
async def pause(message):
    if voice:
        if voice.is_playing():
            voice.pause()
            await message.reply("Song paused!")
        else:
            if voice.is_paused():
                await message.reply("Song is already paused!")
            else:
                await message.reply("You haven't played any song!")
    else:
        await message.reply("I'm not connected to any voice channel!")

@bot.command()
async def resume(message):
    if voice:
        if not voice.is_playing():
            if voice.is_paused():
                voice.resume()
                await message.reply("Song resumed!")
            else:
                await message.reply("You haven't played any song!")
        else:
            await message.reply("Song is already playing!")
    else:
        await message.reply("I'm not connected to any voice channel!")

@bot.command()
async def next(message, *args):
    global show_finish, current_song

    if not voice:
        await message.reply("I'm not connected to any voice channel!")
        return
    elif len(queue) == 0:
        await message.reply("There are no songs in the queue!")
        return
    elif len(args) > 1:
        await message.reply("Invalid command!")
        return

    if len(args) == 0:
        if current_song == len(queue) - 1:
            current_song = 0
        else:
            current_song += 1
    else:
        args = list(args)

        try:
            args[0] = int(args[0])
        except ValueError:
            await message.reply("You must enter an integer!")
            return

        if args[0] <= 0:
            await message.reply("You must enter an integer greater than 0!")
            return

        current_song = min(current_song + args[0], len(queue) - 1)

    if voice.is_playing():
        show_finish = False
        voice.stop()

    voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[current_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = lambda placeholder: finish(message))
    voice.source.volume = voice_volume

    title = queue[current_song]["title"]
    duration = queue[current_song]["duration"]
    await message.reply(f"Now playing **#{current_song + 1} | {title}** ({format_time(duration)})!")

@bot.command()
async def previous(message, *args):
    global show_finish, current_song

    if not voice:
        await message.reply("I'm not connected to any voice channel!")
        return
    elif len(queue) == 0:
        await message.reply("There are no songs in the queue!")
        return
    elif len(args) > 1:
        await message.reply("Invalid command!")
        return
    
    if len(args) == 0:
        if current_song == 0:
            current_song = len(queue) - 1
        else:
            current_song -= 1
    else:
        args = list(args)

        try:
            args[0] = int(args[0])
        except ValueError:
            await message.reply("You must enter an integer!")
            return

        if args[0] <= 0:
            await message.reply("You must enter an integer greater than 0!")
            return

        current_song = max(current_song - args[0], 0)
    
    if voice.is_playing():
        show_finish = False
        voice.stop()

    voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[current_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = lambda placeholder: finish(message))
    voice.source.volume = voice_volume

    title = queue[current_song]["title"]
    duration = queue[current_song]["duration"]
    await message.reply(f"Now playing **#{current_song + 1} | {title}** ({format_time(duration)})!")

@bot.command()
async def volume(message, *args):
    global voice_volume

    if len(args) == 1:
        args = list(args)

        try:
            args[0] = float(args[0])

            if args[0] != int(args[0]):
                await message.reply("Volume must be an integer!")
                return
            else:
                args[0] = int(args[0])
        except ValueError:
            await message.reply("Volume must be an integer!")
            return

        if args[0] < 0 or args[0] > 100:
            await message.reply("Volume must be between 0 and 100!")
        else:
            voice_volume = args[0] / 100

            if voice:
                voice.source.volume = voice_volume

            await message.reply("Volume changed!")
    else:
        await message.reply("Invalid command!")

@bot.command()
async def loop(message, *args):
    global loop

    if len(args) == 1:
        args = list(args)
        args[0] = args[0].lower()

        if args[0] == "on":
            loop = True
            await message.reply("Value updated!")
        elif args[0] == "off":
            loop = False
            await message.reply("Value updated!")
        else:
            await message.reply("Invalid value!")
    else:
        await message.reply("Invalid command!")

@bot.command()
async def auto_skip(message, *args):
    global auto_skip

    if len(args) == 1:
        args = list(args)
        args[0] = args[0].lower()

        if args[0] == "on":
            auto_skip = True
            await message.reply("Value updated!")
        elif args[0] == "off":
            auto_skip = False
            await message.reply("Value updated!")
        else:
            await message.reply("Invalid value!")
    else:
        await message.reply("Invalid command!")

if __name__ == "__main__" :
    bot.run(TOKEN)