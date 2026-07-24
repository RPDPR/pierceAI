import discord
from discord.ext import commands
import config

class TextGeneration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        if message.content.strip() == config.TRIGGER_WORD:
            await message.channel.send(config.TEST_RESPONSE)

async def setup(bot: commands.Bot):
    await bot.add_cog(TextGeneration(bot))
