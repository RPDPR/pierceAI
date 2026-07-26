import os
import aiofiles
import aiohttp
import discord
from discord.ext import commands
from sqlalchemy.dialects.postgresql import insert
from database import AsyncSessionLocal, Message
import config

class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        os.makedirs(config.IMAGE_POOL_DIR, exist_ok=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user or not message.guild:
            return

        async with AsyncSessionLocal() as session:
            if message.content and message.content.strip() != config.TRIGGER_WORD:
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
                        file_path = os.path.join(config.IMAGE_POOL_DIR, filename)

                        async with aiohttp.ClientSession() as web_session:
                            async with web_session.get(attachment.url) as response:
                                if response.status == 200:
                                    async with aiofiles.open(file_path, mode="wb") as f:
                                        await f.write(await response.read())

async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))