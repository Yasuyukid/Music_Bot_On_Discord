Have you ever wanted to host a music discord bot? If the answer is yes then this project is for you. You can easily host your own music discord bot with many features in just 3 steps.

# **Dependencies:**

## Python version:

    Python >= 3.8.0

## Python libraries:

|Library   |Version     |
|:---------|:-----------|
|asyncio   |>= 3.4.3    |
|discord.py|>= 2.2.2    |
|PyNaCl    |>= 1.4.0    |
|yt-dlp    |>= 2023.6.22|

# **Help:**

## Step 1: Create a bot.

- You can [click here](https://discord.com/developers/applications) to create a new bot.
- You'll need to change the bot scopes and bot permissions for it to work.
- Finally, create a new token then save it in a safe place as you will only see it once.

## Step 2: Install requirements.

- You can [click here](https://ffmpeg.org/download.html) to download ffmpeg.
- You also need to install other required libraries listed in the [requirements.txt](https://github.com/YoutuberTom/Music_Bot_On_Discord/blob/main/Music_Bot/requirements.txt) file.

## Step 3: Modify config options.

- Open the [config.ini](https://github.com/YoutuberTom/Music_Bot_On_Discord/blob/main/Music_Bot/config.ini) file and change the config options.
- Replace **"ffmpeg"** with the path to ffmpeg (only if your ffmpeg.exe file isn't in the [PATH](https://en.wikipedia.org/wiki/PATH_(variable))).
- Replace **"<Path to opus.dll (optional)>"** with the path to opus.dll (optional).
- Replace **"<Your bot's token>"** with the bot token that you've saved.

And you just finished creating your music discord bot. Now you can start using your self-hosted bot by running [this file](https://github.com/YoutuberTom/Music_Bot_On_Discord/blob/main/Music_Bot/Music_Bot.py).

# **License:**

This project is distributed under [MIT license](https://github.com/YoutuberTom/Music_Bot_On_Discord/blob/main/LICENSE).
