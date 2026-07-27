import discord
from datetime import datetime
from discord import app_commands
from discord.ext import commands
import asyncio
from services.config_service import PierceConfigService

class Settings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    config_group = app_commands.Group(name="config", description="Configure pierceAI bot settings")

    @config_group.command(name="channel_settings", description="Set channel access and cooldown for pierceAI")
    @app_commands.describe(
        channel="Target channel to configure",
        allow_read="Can the bot use this channel's text as a source for generating memes?",
        allow_write="Can the bot post memes or reply to users in this channel?",
        allow_save_images="Can the bot download images from this channel into the guild pool?",
        cooldown="Cooldown between triggers in seconds (e.g., 5.0)"
    )
    async def channel_settings(self, interaction: discord.Interaction, channel: discord.TextChannel, allow_read: bool = None, allow_write: bool = None, allow_save_images: bool = None, cooldown: float = None):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin permissions required.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await PierceConfigService.update_channel_perms(interaction.guild_id, channel.id, allow_read, allow_write, allow_save_images, cooldown)
        await interaction.followup.send(f"✅ Settings updated for {channel.mention}!")

    @config_group.command(name="sync_history", description="Sync history in background and purge older messages")
    @app_commands.describe(
        since_date="Keep messages starting from this date. Format: YYYY-MM-DD"
    )
    async def sync_history(self, interaction: discord.Interaction, since_date: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin permissions required.", ephemeral=True)
            return
        try:
            parsed_date = datetime.strptime(since_date.strip(), "%Y-%m-%d")
        except ValueError:
            await interaction.response.send_message("❌ Invalid date format! Use YYYY-MM-DD.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        asyncio.create_task(
            PierceConfigService.sync_and_purge_server_history_bg(interaction, interaction.guild, parsed_date)
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))