# Simple starter file that will import and run our main bot code
import os
import sys

def main():
    print("Starting bot...")
    print(f"Current directory: {os.getcwd()}")
    print("Directory contents:")
    print(os.listdir())

    try:
        import bot
        print("Bot module imported successfully")
    except Exception as e:
        print(f"Error importing bot: {str(e)}")
        sys.exit(1)

    try:
        bot.bot.run(bot.TOKEN)
    except Exception as e:
        print(f"Error running bot: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 