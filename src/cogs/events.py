import os
from discord.ext import commands
import config

class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        os.makedirs(config.IMAGE_POOL_DIR, exist_ok=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))