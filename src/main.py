import asyncio
import logging
import discord
from discord.ext import commands
from sqlalchemy import text
import config
from database import AsyncSessionLocal, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pierceAI")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def load_extensions():
    # Load all our architectural cogs
    extensions = ["cogs.settings"]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            logger.info(f"✅ Loaded extension: {ext}")
        except Exception as e:
            logger.error(f"❌ Failed to load extension {ext}: {e}")

@bot.event
async def on_ready():
    logger.info(f"✅ pierceAI bot successfully started as {bot.user}")
    try:
        # Syncing slash commands globally
        await bot.tree.sync()
        logger.info("🔄 Globally synced slash commands tree.")
    except Exception as e:
        logger.error(f"❌ Failed to sync commands tree: {e}")

async def main():
    if not config.DISCORD_TOKEN:
        logger.critical("❌ DISCORD_TOKEN missing!")
        return

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("✅ Database connected successfully!")
    except Exception as e:
        logger.critical(f"❌ Database connection failed: {e}")
        return

    await load_extensions()
    await bot.start(config.DISCORD_TOKEN)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())