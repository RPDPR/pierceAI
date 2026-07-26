import discord
from datetime import datetime
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from database import AsyncSessionLocal, ChannelConfig, Message
import config

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
    async def sync_and_purge_server_history(guild: discord.Guild, since_date: datetime) -> tuple[int, int]:
        async with AsyncSessionLocal() as session:
            delete_stmt = delete(Message).where(
                Message.guild_id == guild.id,
                Message.created_at < since_date
            )
            result = await session.execute(delete_stmt)
            deleted_count = result.rowcount
            await session.commit()

        total_count = 0
        batch = []
        for channel in guild.text_channels:
            perms = channel.permissions_for(guild.me)
            if not perms.read_messages or not perms.read_message_history:
                continue
            try:
                async for msg in channel.history(after=since_date, oldest_first=False, limit=None):
                    if msg.author.bot or not msg.content or msg.content.strip() == "g.i":
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
                        total_count += len(batch)
                        batch = []
            except discord.Forbidden:
                continue

        if batch:
            async with AsyncSessionLocal() as session:
                stmt = insert(Message).values(batch).on_conflict_do_nothing(index_elements=["id"])
                await session.execute(stmt)
                await session.commit()
            total_count += len(batch)

        return total_count, deleted_count