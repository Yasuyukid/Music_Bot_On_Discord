import discord, nacl, youtube_dl, asyncio, os, datetime
from dotenv import load_dotenv
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix = "!", help_command = None, intents = intents)

voice = None
show_finish = True

queue = []
currect_song = 0
loop = True
auto_skip = True

total_page_number = 4
help_message = f"""
!help <optinal - page: integer>: Show this help embed

!join: Make the bot join your voice chat

!disconnect: Make the bot leave your voice chat

!add <url: string> <optinal - song position: integer>: Add your youtube url into queue

!remove <song number: integer>: Remove your youtube url from queue


Page 1/{total_page_number}
----------Page separator----------
!clear: Clear the music queue

!show: Show your music queue

!play <optinal - song number: integer>: Make the bot play your song in the queue

!stop: Stop playing music

!pause: Pause music


Page 2/{total_page_number}
----------Page separator----------
!resume: Continue playing music

!next <optinal - next times: integer>: Play the next song

!previous <optinal - previous times: integer>: Play the previous song

!volume <volume between 0 - 100: integer>: Change the music volume

!loop <on/off: boolean>: Loop playing music


Page 3/{total_page_number}
----------Page separator----------
!auto_skip <on/off: boolean>: Auto skip to next song in queue


Page 4/{total_page_number}
"""

voice_volume = 0.75

youtubeDl_options = {
    "format": "bestaudio/best",
    "restrictfilenames": True,
    "extractaudio": True,
    "noplaylist": True,
    "quiet": True,
    "audioformat": "mp3",
    "default_search": "auto"
}
#To download age restricted video you'll need to add "cookiefile" option

ffmpeg_path = r"ffmpeg.exe"
#Put the path to ffmpeg.exe here

ffmpeg_options = {
    "options": "-vn",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}

@bot.event
async def on_ready():
    print(f"{bot.user} just sucessfully connected with discord!")

@bot.command()
async def help(context, *argument):
    argument = list(argument)

    if len(argument) == 1:
        try:
            argument[0] = int(argument[0])

            help_message_list = help_message.split("----------Page separator----------")

            if argument[0] < 1 or argument[0] > len(help_message_list):
                await context.channel.send(f"{context.author.mention} must input the correct page number!")
            else:
                help_embed = discord.Embed(title = "All available commands!", description = help_message_list[argument[0] - 1], color = 0x0064ff)
                await context.channel.send(embed = help_embed)
        except:
            await context.channel.send(f"{context.author.mention} must input the correct page number!")
    else:
        if len(argument) > 1:
            await context.channel.send(f"{context.author.mention} must write the correct command!")
        elif len(argument) == 0:
            help_message_list = help_message.split("----------Page separator----------")

            help_embed = discord.Embed(title = "All available commands!", description = help_message_list[0], color = 0x0064ff)
            await context.channel.send(embed = help_embed)

def finish_music(context):
    global voice, voice_volume, show_finish, currect_song, queue, loop, auto_skip

    if show_finish:
        if auto_skip:
            if currect_song == len(queue) - 1:
                currect_song = 0

                if loop:
                    task = asyncio.run_coroutine_threadsafe(context.channel.send("I just finished the queue, now looping the queue again...!"), bot.loop)

                    while not task.done():
                        pass

                    voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[currect_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = lambda placeholder: finish_music(context))
                    voice.source.volume = voice_volume

                    title = queue[currect_song]["title"]
                    duration = queue[currect_song]["duration"]
                    asyncio.run_coroutine_threadsafe(context.channel.send(f"Now playing **#{currect_song + 1} | {title}** ({format_time(duration)})!"), bot.loop)
                else:
                    asyncio.run_coroutine_threadsafe(context.channel.send("I just finished the queue!"), bot.loop)
            else:
                currect_song += 1

                task = asyncio.run_coroutine_threadsafe(context.channel.send("I just finished the song, starting next one...!"), bot.loop)

                while not task.done():
                    pass

                voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[currect_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = lambda placeholder: finish_music(context))
                voice.source.volume = voice_volume

                title = queue[currect_song]["title"]
                duration = queue[currect_song]["duration"]
                asyncio.run_coroutine_threadsafe(context.channel.send(f"Now playing **#{currect_song + 1} | {title}** ({format_time(duration)})!"), bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(context.channel.send("I just finished the song!"), bot.loop)
    else:
        show_finish = True

def format_time(time_in_second):
    formated_time = datetime.timedelta(seconds = time_in_second)

    if time_in_second >= 3600:
        edited_formated_time = f"{formated_time.days * 24 + formated_time.seconds // 3600}:{(formated_time.seconds % 3600) // 60:02}:{formated_time.seconds % 60:02}"
    else:
        edited_formated_time = f"{(formated_time.seconds % 3600) // 60}:{formated_time.seconds % 60:02}"

    return edited_formated_time

@bot.command()
async def join(context):
    global voice

    if context.author.voice:
        channel = context.author.voice.channel

        if voice == None:
            voice = await channel.connect()

            await context.reply("I just connected to your voice channel!")
        else:
            await context.reply("I'm currect in another voice channel, you must disconnect first!")
    else:
        await context.reply(f"{context.author.mention} must connect to a voice channel first!")

@bot.command()
async def disconnect(context):
    global voice, show_finish

    if voice == None:
        await context.reply("I haven't connected to a voice channel yet!")
    else:
        show_finish = False

        await voice.disconnect()
        voice = None

        await context.reply("Disconnected!")

@bot.command()
async def add(context, *argument):
    global queue, currect_song

    user_input = list(argument)

    if len(user_input) == 1:
        try:
            with youtube_dl.YoutubeDL(youtubeDl_options) as ytdl:
                info = ytdl.extract_info(argument[0], download = False)
        except:
            await context.reply("Something's wrong with the url, please try again!")
            return

        queue.append(info)

        title = info["title"]
        duration = info["duration"]
        await context.reply(f"Song **#{len(queue)} | {title}** ({format_time(duration)}) added!")
    elif len(user_input) == 2:
        try:
            with youtube_dl.YoutubeDL(youtubeDl_options) as ytdl:
                info = ytdl.extract_info(argument[0], download = False)
        except:
            await context.reply("Something's wrong with the url, please try again!")
            return
        
        try:
            song_pos = float(argument[1])

            if song_pos != int(song_pos):
                await context.reply("Invaid song position!")
                return
            else:
                song_pos = int(song_pos)
        except:
            await context.reply("Invaid song position!")
            return
        
        if song_pos < 1 or song_pos > len(queue) + 1:
            await context.reply("Invaid song position!")
        else:
            queue.insert(song_pos - 1, info)

            if song_pos <= currect_song + 1 and len(queue) != 1:
                currect_song += 1

            title = info["title"]
            duration = info["duration"]
            await context.reply(f"Song **#{song_pos} | {title}** ({format_time(duration)}) added!")
    else:
        await context.reply("Please input a correct youtube url!")

@bot.command()
async def remove(context, *argument):
    global currect_song, queue

    if len(list(argument)) == 1:
        try:
            argument = list(argument)
            argument[0] = int(argument[0])
        except:
            await context.reply("Please input a correct integer!")
            return
        
        if argument[0] < 1 or argument[0] > len(queue):
            await context.reply("Invaid song!")
        else:
            if argument[0] == currect_song + 1:
                await context.reply("Cannot remove in-play song!")
            elif argument[0] > currect_song + 1:
                remove_title = queue[argument[0] - 1]["title"]
                remove_duration = queue[argument[0] - 1]["duration"]

                queue.pop(argument[0] - 1)

                await context.reply(f"Song **#{argument[0]} | {remove_title}** ({format_time(remove_duration)}) removed!")
            elif argument[0] < currect_song + 1:
                remove_title = queue[argument[0] - 1]["title"]
                remove_duration = queue[argument[0] - 1]["duration"]

                currect_song -= 1
                queue.pop(argument[0] - 1)

                await context.reply(f"Song **#{argument[0]} | {remove_title}** ({format_time(remove_duration)}) removed!")
    else:
        await context.reply("Please input a correct integer!")

@bot.command()
async def clear(context):
    global show_finish, currect_song, queue

    if voice == None:
        queue = []
        currect_song = 0

        await context.reply("Queue cleared!")
    else:
        if voice.is_playing():
            show_finish = False

            voice.stop()

        queue = []
        currect_song = 0

        await context.reply("Queue cleared!")

@bot.command()
async def show(context):
    global queue

    if len(queue) == 0:
        await context.reply("There're currectly no song in queue!")
    else:
        queue_name = []
        currect = queue[currect_song]

        for info in queue:
            title = info["title"]
            duration = info["duration"]

            if currect != info:
                queue_name.append(f"**#{queue.index(info) + 1} | {title}** ({format_time(duration)})")
            else:
                queue_name.append(f"**#{queue.index(info) + 1} | {title}** ({format_time(duration)})  <-- You're here")

        await context.reply("Currect music queue:\n" + "\n".join(queue_name))

@bot.command()
async def play(context, *argument):
    global voice, voice_volume, show_finish, queue, currect_song

    if voice == None:
        await context.reply("I haven't connected to a voice channel yet!")
    else:
        if len(list(argument)) == 1:
            if len(queue) >= 1:
                if voice.is_playing():
                    show_finish = False

                    voice.stop()
                
                try:
                    argument = list(argument)
                    argument[0] = int(argument[0])
                except:
                    await context.reply("Please input a correct integer!")
                    return
                
                if argument[0] < 1 or argument[0] > len(queue):
                    await context.reply("Invaid song!")
                else:
                    currect_song = argument[0] - 1

                    voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[currect_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = lambda placeholder: finish_music(context))
                    voice.source.volume = voice_volume

                    title = queue[currect_song]["title"]
                    duration = queue[currect_song]["duration"]
                    await context.reply(f"Now playing **#{currect_song + 1} | {title}** ({format_time(duration)})!")
            else:
                await context.reply(f"{context.author.mention} haven't added any song!")
        elif len(list(argument)) == 0:
            if len(queue) >= 1:
                if voice.is_playing():
                    show_finish = False

                    voice.stop()

                voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[currect_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = lambda placeholder: finish_music(context))
                voice.source.volume = voice_volume

                title = queue[currect_song]["title"]
                duration = queue[currect_song]["duration"]
                await context.reply(f"Now playing **#{currect_song + 1} | {title}** ({format_time(duration)})!")
            else:
                await context.reply(f"{context.author.mention} haven't added any song!")
        else:
            await context.reply("Please input a correct integer!")

@bot.command()
async def stop(context):
    global voice, show_finish

    if voice == None:
        await context.reply("I haven't connected to a voice channel yet!")
    else:
        if voice.is_playing():
            show_finish = False

            voice.stop()

            await context.reply("Music stopped!")
        elif not voice.is_paused():
            await context.reply(f"{context.author.mention} haven't played any song!")

@bot.command()
async def pause(context):
    if voice == None:
        await context.reply("I haven't connected to a voice channel yet!")
    else:
        if voice.is_playing():
            voice.pause()

            await context.reply("Paused!")
        else:
            if voice.is_paused():
                await context.reply(f"{context.author.mention} music is already paused!")
            else:
                await context.reply(f"{context.author.mention} haven't played any song!")

@bot.command()
async def resume(context):
    if voice == None:
        await context.reply("I haven't connected to a voice channel yet!")
    else:
        if not voice.is_playing():
            if voice.is_paused():
                voice.resume()

                await context.reply("Resumed!")
            else:
                await context.reply(f"{context.author.mention} haven't played any music yet!")
        else:
            await context.reply("Already playing music!")

@bot.command()
async def next(context, *argument):
    global voice, voice_volume, show_finish, currect_song, queue

    if len(list(argument)) == 1:
        try:
            argument = list(argument)
            argument[0] = int(argument[0])
        except:
            await context.reply("Please input a correct integer!")
            return

        if argument[0] <= 0:
            await context.reply("Please input a correct integer!")
        elif currect_song + argument[0] >= len(queue) - 1:
            if voice.is_playing():
                show_finish = False
                voice.stop()

                currect_song = len(queue) - 1

                voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[currect_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = lambda placeholder: finish_music(context))
                voice.source.volume = voice_volume

                title = queue[currect_song]["title"]
                duration = queue[currect_song]["duration"]
                await context.reply(f"Now playing **#{currect_song + 1} | {title}** ({format_time(duration)})!")
            else:
                await context.reply(f"{context.author_metion} must be playing music in order to change song!")
    else:
        if len(list(argument)) == 0:
            if voice.is_playing():
                show_finish = False
                voice.stop()

                if currect_song < len(queue) - 1:
                    currect_song += 1

                voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[currect_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = lambda placeholder: finish_music(context))
                voice.source.volume = voice_volume

                title = queue[currect_song]["title"]
                duration = queue[currect_song]["duration"]
                await context.reply(f"Now playing **#{currect_song + 1} | {title}** ({format_time(duration)})!")
            else:
                await context.reply(f"{context.author_metion} must be playing music in order to change song!")
        else:
            await context.reply("Please input a correct integer!")

@bot.command()
async def previous(context, *argument):
    global voice, voice_volume, show_finish, currect_song, queue

    if len(list(argument)) == 1:
        try:
            argument = list(argument)
            argument[0] = int(argument[0])
        except:
            await context.reply("Please input a correct integer!")
            return

        if argument[0] <= 0:
            await context.reply("Please input a correct integer!")
        elif currect_song - argument[0] <= 0:
            if voice.is_playing():
                show_finish = False
                voice.stop()
                
                currect_song = 0

                voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[currect_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = lambda placeholder: finish_music(context))
                voice.source.volume = voice_volume

                title = queue[currect_song]["title"]
                duration = queue[currect_song]["duration"]
                await context.reply(f"Now playing **#{currect_song + 1} | {title}** ({format_time(duration)})!")
            else:
                await context.reply(f"{context.author_metion} must be playing music in order to change song!")
    else:
        if len(list(argument)) == 0:
            if voice.is_playing():
                show_finish = False
                voice.stop()
                
                if currect_song > 0:
                    currect_song -= 1

                voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(queue[currect_song]["url"], **ffmpeg_options, executable = ffmpeg_path), voice_volume), after = lambda placeholder: finish_music(context))
                voice.source.volume = voice_volume

                title = queue[currect_song]["title"]
                duration = queue[currect_song]["duration"]
                await context.reply(f"Now playing **#{currect_song + 1} | {title}** ({format_time(duration)})!")
            else:
                await context.reply(f"{context.author_metion} must be playing music in order to change song!")
        else:
            await context.reply("Please input a correct integer!")

@bot.command()
async def volume(context, *argument):
    global voice_volume

    if len(list(argument)) == 1:
        try:
            argument = list(argument)
            argument[0] = float(argument[0])
        except:
            await context.reply("Volume must be an integer!")
            return

        if argument[0] < 0 or argument[0] > 100:
            await context.reply("Volume must be between 0 and 100!")
        else:
            voice_volume = argument[0] / 100

            try:
                voice.source.volume = voice_volume
            except:
                pass

            await context.reply("Volume changed!")
    else:
        await context.reply("Please input a correct volume!")

@bot.command()
async def loop(context, *argument):
    global loop

    if len(list(argument)) == 1:
        argument = list(argument)

        if argument[0].lower() == "on":
            loop = True

            await context.reply("Value updated!")
        elif argument[0].lower() == "off":
            loop = False

            await context.reply("Value updated!")
        else:
            await context.reply("Please input a correct value!")
    else:
        await context.reply("Please input a correct value!")

@bot.command()
async def auto_skip(context, *argument):
    global auto_skip

    if len(list(argument)) == 1:
        argument = list(argument)

        if argument[0].lower() == "on":
            auto_skip = True

            await context.reply("Value updated!")
        elif argument[0].lower() == "off":
            auto_skip = False

            await context.reply("Value updated!")
        else:
            await context.reply("Please input a correct value!")
    else:
        await context.reply("Please input a correct value!")

load_dotenv()
TOKEN = os.getenv("discord_bot_token")

if __name__ == "__main__" :
    bot.run(TOKEN)
