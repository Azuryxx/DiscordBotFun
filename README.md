
# My First Discord Bot

Welcome to **Azuryy_**'s first Discord bot project! 🎉 This bot is designed to offer fun features such as joining voice channels and playing music. It's a great starting point to explore how Discord bots work.

---

## Features

- **Join voice channels**
- **Play music in voice channels**
- **Respond to commands**
- more command :)

---

## Prerequisites

To run this bot, make sure you have the following:

- **Python 3.8+**
- **FFmpeg** (for voice and music features)
- **discord.py** (Discord API wrapper)
- **yt-dlp** (YouTube downloader)
- **PyNaCl** (required for voice support)

---

## Installation

Follow these steps to set up the bot:

1. Clone the repository:

   ```bash
   git clone https://github.com/Azuryxx/DiscordBotFun.git
   ```

2. Change to the project directory:

   ```bash
   cd DiscordBotFun
   ```

3. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  
   ```

4. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. **Install FFmpeg**:
   - Download it from [FFmpeg](https://ffmpeg.org/download.html).
   - Ensure FFmpeg is in your system’s PATH.

6. **Set your Discord bot token**:
   - Create a `.env` file in the root directory.
   - Add your bot's token:

     ```env
     DISCORD_TOKEN=your-discord-bot-token-here
     ```

---

## Running the Bot

To run the bot, use the following command:

```bash
python bot.py
```

If you’re using threading for Flask (or another server):

```python
if __name__ == "__main__":
    bot_thread = threading.Thread(target=bot.run, args=(TOKEN,))
    bot_thread.daemon = True
    bot_thread.start()
    print("Bot thread started")
    run_flask()  # If you're also using Flask
```

---

## Available Commands

- `!aide`: Shows a list of available commands.
- `!play[URL]`: Makes the bot join a voice channel and play a predefined song.

---

## Troubleshooting

- **Bot quits instantly**: Make sure **FFmpeg** is installed and added to your system’s PATH.
- **Music not playing**: Ensure **yt-dlp** and FFmpeg are configured properly.
- **FFmpeg error**: Verify FFmpeg is installed and its path is correctly set.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
