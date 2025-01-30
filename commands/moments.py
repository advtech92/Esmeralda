import discord
from discord import app_commands
from discord.ext import tasks
from typing import Optional
from datetime import datetime, timedelta, time, timezone
import logging
import os
from utils.database import Database

db = Database()


class FunnyMoments:
    def __init__(self, client):
        self.client = client
        self.retention_days = 30
        self.highlight_channel = None  # Will be set in on_ready

        # Start scheduled tasks
        self.weekly_highlight.start()
        self.daily_purge.start()

    async def on_ready(self):
        """Initialize channel after bot is ready"""
        channel_id = int(os.getenv("HIGHLIGHT_CHANNEL_ID"))
        self.highlight_channel = self.client.get_channel(channel_id)
        if not self.highlight_channel:
            logging.error("Invalid highlight channel ID in .env")

    @tasks.loop(time=time(hour=9, minute=0, tzinfo=timezone.utc))
    async def weekly_highlight(self):
        try:
            # Only run on Mondays (0 = Monday)
            if datetime.now(timezone.utc).weekday() != 0:
                return

            start_date = datetime.now(timezone.utc) - timedelta(days=7)
            moments = db.get_funny_moments_since(start_date)

            if not moments or not self.highlight_channel:
                return

            embed = discord.Embed(
                title="😂 Weekly Funny Moments Highlight",
                color=0x00ff00
            )

            for idx, moment in enumerate(moments[:5], 1):
                embed.add_field(
                    name=f"Moment #{idx}",
                    value=f"[Jump to Message]({moment['message_link']})",
                    inline=False
                )

            await self.highlight_channel.send(embed=embed)

        except Exception as e:
            logging.error(f"Weekly highlight error: {str(e)}")

    @tasks.loop(hours=24)
    async def daily_purge(self):
        try:
            cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
            deleted_count = db.purge_old_funny_moments(cutoff)
            logging.info(f"Purged {deleted_count} old funny moments")
        except Exception as e:
            logging.error(f"Purge error: {str(e)}")

    @weekly_highlight.before_loop
    @daily_purge.before_loop
    async def before_tasks(self):
        await self.client.wait_until_ready()


def setup(client):
    # Create command group
    moments_group = app_commands.Group(name="moments", description="Manage funny moments")

    # Add purge command to the group
    @moments_group.command(
        name="purge",
        description="Purge old funny moments"
    )
    @app_commands.describe(days="Purge moments older than X days (0 to disable)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge_funny(interaction: discord.Interaction, days: int = 30):
        try:
            if days < 0:
                raise ValueError("Days must be >= 0")

            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            deleted_count = db.purge_old_funny_moments(cutoff)

            await interaction.response.send_message(
                f"✅ Purged {deleted_count} moments older than {days} days",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )

    # Create FunnyMoments instance
    funny_moments = FunnyMoments(client)

    # Context menu command
    @client.tree.context_menu(name="Mark as Funny Moment")
    async def mark_funny(interaction: discord.Interaction, message: discord.Message):
        try:
            await message.add_reaction("😂")
            await message.add_reaction("🎉")

            message_link = f"https://discord.com/channels/{interaction.guild_id}/{message.channel.id}/{message.id}"
            record_id = db.add_funny_moment(
                message_link=message_link,
                author_id=message.author.id
            )

            embed = discord.Embed(
                title="😂 Funny Moment Saved",
                description=f"[Jump to Message]({message_link})",
                color=0x00ff00
            ).set_author(
                name=message.author.display_name,
                icon_url=message.author.avatar.url
            ).add_field(
                name="Message Preview",
                value=message.content[:100] + "..." if len(message.content) > 100 else message.content,
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logging.error(f"Context menu error: {e}")
            await interaction.response.send_message(
                "❌ Couldn't mark this message. Is it too old?",
                ephemeral=True
            )

    # Purge command
    @app_commands.command(name="purge_funny")
    @app_commands.describe(days="Purge moments older than X days (0 to disable)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge_funny(interaction: discord.Interaction, days: int = 30):
        try:
            if days < 0:
                raise ValueError("Days must be >= 0")

            cutoff = datetime.utcnow() - timedelta(days=days)
            deleted_count = db.purge_old_funny_moments(cutoff)

            await interaction.response.send_message(
                f"✅ Purged {deleted_count} moments older than {days} days",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )

    client.tree.add_command(moments_group)
