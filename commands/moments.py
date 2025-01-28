import discord
from discord import app_commands
from typing import Optional, List
from datetime import datetime
import logging

# Temporary storage for moments (consider database in future)
saved_moments = []
incident_logs = {}


async def setup(client):
    # Create command group
    moments_group = app_commands.Group(
        name="moments",
        description="Capture and manage important moments"
    )

    # Funny moment command
    @moments_group.command(
        name="funny",
        description="Tag a funny moment with reactions"
    )
    @app_commands.describe(
        message_link="Link to the funny message",
        description="Optional description"
    )
    async def funny_moment(
        interaction: discord.Interaction,
        message_link: str,
        description: Optional[str] = None
    ):
        """Capture a funny moment with reaction tracking"""
        try:
            # Parse message ID from link
            parts = message_link.split("/")
            channel_id = int(parts[-2])
            message_id = int(parts[-1])

            channel = interaction.guild.get_channel(channel_id)
            message = await channel.fetch_message(message_id)

            # Add tracking reactions
            await message.add_reaction("😂")
            await message.add_reaction("🎉")

            # Store moment
            saved_moments.append({
                "message": message.content,
                "author": message.author.id,
                "description": description,
                "timestamp": datetime.now().isoformat()
            })

            await interaction.response.send_message(
                "✅ Funny moment registered! Reactions added!",
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Funny moment error: {e}")
            await interaction.response.send_message(
                "❌ Failed to register funny moment. Check message link!",
                ephemeral=True
            )

    # Incident tracking command
    @moments_group.command(
        name="incident",
        description="Log an incident with recent messages"
    )
    @app_commands.describe(
        message_count="Number of messages to capture (max 50)",
        reason="Reason for logging"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def incident_log(
        interaction: discord.Interaction,
        message_count: app_commands.Range[int, 1, 50],
        reason: str
    ):
        """Log messages for moderator review"""
        try:
            # Fetch messages
            messages = [
                msg async for msg in interaction.channel.history(limit=message_count)
            ][::-1]  # Reverse to get chronological order

            # Format log
            log_content = "\n".join(
                f"{msg.author.display_name} ({msg.author.id}) | {msg.created_at}:\n"
                f"{msg.content}\n{'-'*40}"
                for msg in messages
            )

            # Store log
            incident_id = f"incident_{datetime.now().timestamp()}"
            incident_logs[incident_id] = {
                "reason": reason,
                "messages": log_content,
                "moderator": interaction.user.id
            }

            # Send confirmation
            await interaction.response.send_message(
                f"✅ Incident logged with ID `{incident_id}`\n"
                f"**Reason:** {reason}\n"
                f"Captured {len(messages)} messages",
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Incident log error: {e}")
            await interaction.response.send_message(
                "❌ Failed to log incident. Check permissions!",
                ephemeral=True
            )

    # Add commands to client
    client.tree.add_command(moments_group)
