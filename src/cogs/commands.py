import discord
from discord.ext import commands
from datetime import datetime
from services.generator import PierceGeneratorService
from database import AsyncSessionLocal, ChannelConfig
import config

class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_triggered = {}

    async def _get_channel_config(self, channel_id: int):
        async with AsyncSessionLocal() as session:
            res = await session.get(ChannelConfig, channel_id)
            if res is None:
                return False, config.DEFAULT_COOLDOWN
            return res.allow_write, res.cooldown

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user or not message.guild:
            return

        if message.content.strip() == config.TRIGGER_WORD:
            allow_write, cooldown_seconds = await self._get_channel_config(message.channel.id)
            if not allow_write:
                return

            now = datetime.utcnow().timestamp()
            last_time = self._last_triggered.get(message.channel.id, 0.0)
            if now - last_time < cooldown_seconds:
                return

            self._last_triggered[message.channel.id] = now

            async with message.channel.typing():
                avatar_bytes = await message.author.display_avatar.read()
                image_buffer = await PierceGeneratorService.generate_meme(avatar_bytes, message.channel.id, message.guild.id)
                file = discord.File(fp=image_buffer, filename="absurdity.jpg")
                await message.reply(file=file)
            return

        if message.reference and message.reference.message_id:
            allow_write, _ = await self._get_channel_config(message.channel.id)
            if not allow_write:
                return

            try:
                referenced_msg = message.reference.cached_message or await message.channel.fetch_message(message.reference.message_id)
                if referenced_msg and referenced_msg.author == self.bot.user:
                    async with message.channel.typing():
                        generated_text = await PierceGeneratorService.get_text_for_reply(message.guild.id)
                        await message.reply(content=generated_text)
            except discord.HTTPException:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))