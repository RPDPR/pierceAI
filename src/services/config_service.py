import discord
import logging
from datetime import datetime
from sqlalchemy import delete, select, func
from sqlalchemy.dialects.postgresql import insert
from database import AsyncSessionLocal, ChannelConfig, Message
import config
import asyncio

logger = logging.getLogger("pierceAI.config")

class PierceConfigService:
    @staticmethod
    async def update_channel_perms(guild_id: int, channel_id: int, allow_read: bool = None, allow_write: bool = None, cooldown: float = None):
        async with AsyncSessionLocal() as session:
            stmt = insert(ChannelConfig).values(
                channel_id=channel_id,
                guild_id=guild_id,
                allow_read=allow_read if allow_read is not None else True,
                allow_write=allow_write if allow_write is not None else True,
                cooldown=cooldown if cooldown is not None else config.DEFAULT_COOLDOWN
            )
            update_dict = {}
            if allow_read is not None:
                update_dict["allow_read"] = allow_read
            if allow_write is not None:
                update_dict["allow_write"] = allow_write
            if cooldown is not None:
                update_dict["cooldown"] = cooldown

            if update_dict:
                stmt = stmt.on_conflict_do_update(index_elements=["channel_id"], set_=update_dict)
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def sync_and_purge_server_history_bg(interaction: discord.Interaction, guild: discord.Guild, since_date: datetime):
        try:
            async with AsyncSessionLocal() as session:
                delete_stmt = delete(Message).where(
                    Message.guild_id == guild.id,
                    Message.created_at < since_date
                )
                await session.execute(delete_stmt)
                await session.commit()

            await interaction.edit_original_response(content="✅ History has been synced!")

            batch = []
            for channel in guild.text_channels:
                perms = channel.permissions_for(guild.me)
                if not perms.read_messages or not perms.read_message_history:
                    continue
                try:
                    async for msg in channel.history(after=since_date, oldest_first=False, limit=None):
                        if msg.author.bot or not msg.content or msg.content.strip() == config.TRIGGER_WORD:
                            continue
                        batch.append({
                            "id": msg.id,
                            "channel_id": msg.channel.id,
                            "guild_id": msg.guild.id,
                            "author_id": msg.author.id,
                            "content": msg.content.strip(),
                            "created_at": msg.created_at.replace(tzinfo=None)
                        })
                        if len(batch) >= 200:
                            async with AsyncSessionLocal() as session:
                                stmt = insert(Message).values(batch).on_conflict_do_nothing(index_elements=["id"])
                                await session.execute(stmt)
                                await session.commit()
                            batch = []
                            await asyncio.sleep(0.1)
                except discord.Forbidden:
                    continue

            if batch:
                async with AsyncSessionLocal() as session:
                    stmt = insert(Message).values(batch).on_conflict_do_nothing(index_elements=["id"])
                    await session.execute(stmt)
                    await session.commit()

        except Exception as e:
            logger.error(f"Error during background sync: {e}")