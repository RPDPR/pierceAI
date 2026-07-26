import discord
from discord.ext import commands
import time
import os
import aiohttp
import aiofiles
from sqlalchemy.dialects.postgresql import insert
from services.generator import PierceGeneratorService
from database import AsyncSessionLocal, ChannelConfig, Message
import config

class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_triggered = {}
        self._cooldown_cache = {}
        self._is_processing = {}

    async def _is_write_allowed(self, channel_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            res = await session.get(ChannelConfig, channel_id)
            if res is None:
                return False
            self._cooldown_cache[channel_id] = res.cooldown
            return res.allow_write

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if message.content.strip() != config.TRIGGER_WORD and message.content:
            async with AsyncSessionLocal() as session:
                stmt = insert(Message).values(
                    id=message.id,
                    channel_id=message.channel.id,
                    guild_id=message.guild.id,
                    author_id=message.author.id,
                    content=message.content.strip(),
                    created_at=message.created_at.replace(tzinfo=None)
                ).on_conflict_do_nothing(index_elements=["id"])
                await session.execute(stmt)
                await session.commit()

        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    file_ext = attachment.filename.split(".")[-1]
                    filename = f"{attachment.id}.{file_ext}"
                    
                    guild_pool_dir = os.path.join(config.IMAGE_POOL_DIR, str(message.guild.id))
                    os.makedirs(guild_pool_dir, exist_ok=True)
                    file_path = os.path.join(guild_pool_dir, filename)
                    
                    async with aiohttp.ClientSession() as web_session:
                        async with web_session.get(attachment.url) as response:
                            if response.status == 200:
                                async with aiofiles.open(file_path, mode="wb") as f:
                                    await f.write(await response.read())

        if message.content.strip() == config.TRIGGER_WORD:
            if self._is_processing.get(message.channel.id, False):
                return

            now = time.time()
            last_time = self._last_triggered.get(message.channel.id, 0.0)
            cooldown_seconds = self._cooldown_cache.get(message.channel.id, config.DEFAULT_COOLDOWN)

            if now - last_time < cooldown_seconds:
                return

            self._is_processing[message.channel.id] = True
            self._last_triggered[message.channel.id] = now

            if not await self._is_write_allowed(message.channel.id):
                self._is_processing[message.channel.id] = False
                return

            try:
                async with message.channel.typing():
                    avatar_bytes = await message.author.display_avatar.read()
                    image_buffer = await PierceGeneratorService.generate_meme(avatar_bytes, message.channel.id, message.guild.id)
                    file = discord.File(fp=image_buffer, filename="meme.jpg")
                    await message.reply(file=file)
            finally:
                self._is_processing[message.channel.id] = False
            return

        if message.reference and message.reference.message_id:
            try:
                referenced_msg = message.reference.cached_message or await message.channel.fetch_message(message.reference.message_id)
                if referenced_msg and referenced_msg.author == self.bot.user:
                    if not await self._is_write_allowed(message.channel.id):
                        return
                    async with message.channel.typing():
                        generated_text = await PierceGeneratorService.get_text_for_reply(message.guild.id)
                        await message.reply(content=generated_text)
            except discord.HTTPException:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))