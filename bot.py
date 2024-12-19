# FPS.ms entry point
import os
import sys
import discord
from discord.ext import commands

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# Import our main bot code
from main import bot, TOKEN

def main():
    print("Starting bot...")
    print(f"Current directory: {os.getcwd()}")
    print("Directory contents:")
    print(os.listdir())

    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error running bot: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 