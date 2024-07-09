import os
import sys
from dotenv import load_dotenv
import discord
from discord.ext import commands
import asyncio
from discord import app_commands

# Load environment variables from .env file
load_dotenv()

# Get the bot token from environment variable
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Specify the full path to your FFmpeg executable
FFMPEG_PATH = r"Folder of the FFmpeg"
print(f"FFmpeg path: {FFMPEG_PATH}")
print(f"FFmpeg exists: {os.path.exists(FFMPEG_PATH)}")

# Specify the path to your MP3 file
MP3_PATH = r"path to mp3"  # Update this to change the mp3 file
print(f"MP3 path: {MP3_PATH}")
print(f"MP3 exists: {os.path.exists(MP3_PATH)}")

# Define intents
intents = discord.Intents.default()
intents.message_content = True  # Enable the message content intent

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    
    # Generate invite link with specific permissions
    permissions = discord.Permissions(
        connect=True,
        speak=True,
        move_members=True,
        send_messages=True,
        use_application_commands=True
    )
    invite_link = discord.utils.oauth_url(bot.user.id, permissions=permissions)
    print(f"Invite the bot using this link: {invite_link}")

@bot.tree.command(name="outro", description="Play an outro song and kick you from the voice channel")
@app_commands.describe(volume="Volume level (0-200)")
async def outro(interaction: discord.Interaction, volume: int = 100):
    if not interaction.user.voice:
        await interaction.response.send_message("You need to be in a voice channel to use this command!")
        return

    # Clamp volume between 0 and 200
    volume = max(0, min(volume, 200))
    
    # Convert to float for discord.py (0.0 to 2.0)
    volume_float = volume / 100.0

    await interaction.response.defer(thinking=True)

    voice_channel = interaction.user.voice.channel
    try:
        if interaction.guild.voice_client is None:
            voice_client = await voice_channel.connect(timeout=60.0)
        else:
            voice_client = interaction.guild.voice_client
            if voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)
            
        # Wait for the voice client to be fully connected
        for _ in range(30):  # Wait up to 3 seconds
            if voice_client.is_connected():
                break
            await asyncio.sleep(0.1)
        else:
            await interaction.followup.send("Failed to establish a stable connection to the voice channel.")
            return

    except asyncio.TimeoutError:
        await interaction.followup.send("Failed to connect to the voice channel in time. Try Again later!")
        return
    except Exception as e:
        await interaction.followup.send(f"An error occurred while connecting to the voice channel: {e}")
        return

    try:
        audio_source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(MP3_PATH, executable=FFMPEG_PATH))
        audio_source.volume = volume_float
        
        def after_playing(error):
            if error:
                print(f'Player error: {error}')
            asyncio.run_coroutine_threadsafe(bot_disconnect(voice_client), bot.loop)

        voice_client.play(audio_source, after=after_playing)
        await interaction.followup.send(f"Now playing outro music at {volume}% volume!")
        
        # Schedule user kick after 13 seconds
        bot.loop.create_task(kick_user(interaction.user, 13))
    except Exception as e:
        print(f"Error in outro command: {e}")
        await interaction.followup.send(f"An error occurred while playing the song: {e}")
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()

async def kick_user(user, delay):
    await asyncio.sleep(delay)
    try:
        await user.move_to(None)
        print(f"Kicked user {user}")
    except discord.errors.HTTPException:
        print(f"Failed to move user {user}. They may have already left the channel.")

async def bot_disconnect(voice_client):
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        print("Successfully disconnected from voice channel")

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error running the bot: {e}")
        sys.exit(1)
