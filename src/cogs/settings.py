import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.dialects.postgresql import insert
from database import AsyncSessionLocal, ChannelConfig

class Settings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Базовая группа команды /config
    config_group = app_commands.Group(name="config", description="Configure pierceAI bot settings")

    @config_group.command(name="channel_perms", description="Configure read/write permissions for a channel")
    @app_commands.describe(
        channel="The target channel to configure",
        allow_read="Can the bot read history from this channel?",
        allow_write="Can the bot reply/write in this channel?"
    )
    async def channel_perms(self, interaction: discord.Interaction, channel: discord.TextChannel, allow_read: bool = None, allow_write: bool = None):
        # Проверка прав администратора (как в Laravel Middleware)
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions to use this command.", ephemeral=True)
            return

        async with AsyncSessionLocal() as session:
            # Делаем UPSERT (создать или обновить, если запись уже есть)
            stmt = insert(ChannelConfig).values(
                channel_id=channel.id,
                guild_id=interaction.guild_id,
                allow_read=allow_read if allow_read is not None else True,
                allow_write=allow_write if allow_write is not None else True
            )
            
            update_dict = {}
            if allow_read is not None: update_dict["allow_read"] = allow_read
            if allow_write is not None: update_dict["allow_write"] = allow_write
            
            if update_dict:
                stmt = stmt.on_conflict_do_update(index_elements=["channel_id"], set_=update_dict)
            
            await session.execute(stmt)
            await session.commit()

        await interaction.response.send_message(f"✅ Successfully updated permissions for {channel.mention}!", ephemeral=True)

    @config_group.command(name="behavior", description="Configure cooldown and text limits")
    @app_commands.describe(
        channel="The target channel",
        cooldown="Cooldown between responses in seconds",
        history_days="Lookback period in days (0 for all-time history)",
        text_position="Position of text on image (top, bottom, random)"
    )
    @app_commands.choices(text_position=[
        app_commands.Choice(name="Top Only", value="top"),
        app_commands.Choice(name="Bottom Only", value="bottom"),
        app_commands.Choice(name="Random", value="random")
    ])
    async def behavior(self, interaction: discord.Interaction, channel: discord.TextChannel, cooldown: float = None, history_days: int = None, text_position: str = None):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions to use this command.", ephemeral=True)
            return

        async with AsyncSessionLocal() as session:
            stmt = insert(ChannelConfig).values(
                channel_id=channel.id,
                guild_id=interaction.guild_id,
                cooldown=cooldown if cooldown is not None else 0.0,
                history_days=history_days if history_days is not None else 30,
                text_position=text_position if text_position is not None else "random"
            )
            
            update_dict = {}
            if cooldown is not None: update_dict["cooldown"] = cooldown
            if history_days is not None: update_dict["history_days"] = history_days
            if text_position is not None: update_dict["text_position"] = text_position
            
            if update_dict:
                stmt = stmt.on_conflict_do_update(index_elements=["channel_id"], set_=update_dict)
                
            await session.execute(stmt)
            await session.commit()

        await interaction.response.send_message(f"✅ Successfully updated behavior settings for {channel.mention}!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))