import discord
from discord import app_commands
from typing import Optional
from datetime import datetime
import logging
from utils.database import Database

db = Database()


async def setup(client):
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
        try:
            parts = message_link.split("/")
            channel_id = int(parts[-2])
            message_id = int(parts[-1])

            channel = interaction.guild.get_channel(channel_id)
            message = await channel.fetch_message(message_id)

            await message.add_reaction("😂")
            await message.add_reaction("🎉")

            # Store in database
            record_id = db.add_funny_moment(
                message_link=message_link,
                author_id=message.author.id,
                description=description
            )

            await interaction.response.send_message(
                f"✅ Funny moment registered! (ID: {record_id})",
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Funny moment error: {e}")
            await interaction.response.send_message(
                "❌ Failed to register funny moment. Check message link!",
                ephemeral=True
            )

    # Incident command
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
        try:
            messages = [
                msg async for msg in interaction.channel.history(limit=message_count)
            ][::-1]

            # Prepare messages for storage
            formatted_messages = [{
                "id": msg.id,
                "author_id": msg.author.id,
                "content": msg.content,
                "timestamp": msg.created_at
            } for msg in messages]

            # Generate incident ID
            incident_id = f"incident_{int(datetime.now().timestamp())}"

            # Store in database
            success = db.add_incident(
                incident_id=incident_id,
                reason=reason,
                moderator_id=interaction.user.id,
                messages=formatted_messages
            )

            if not success:
                raise Exception("Database storage failed")

            await interaction.response.send_message(
                f"✅ Incident logged with ID `{incident_id}`\n"
                f"**Reason:** {reason}\n"
                f"Captured {len(messages)} messages",
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Incident log error: {e}")
            await interaction.response.send_message(
                "❌ Failed to log incident. Check permissions and message count!",
                ephemeral=True
            )

    # Add review command
    @moments_group.command(
        name="review",
        description="Review a logged incident"
    )
    @app_commands.describe(
        incident_id="The incident ID to review"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def review_incident(
        interaction: discord.Interaction,
        incident_id: str
    ):
        try:
            incident = db.get_incident(incident_id)
            if not incident:
                await interaction.response.send_message(
                    "❌ Incident not found",
                    ephemeral=True
                )
                return

            # Format response
            messages = "\n\n".join(
                f"**{msg['timestamp']}** <@{msg['author_id']}>:\n"
                f"{msg['content']}"
                for msg in incident['messages']
            )

            embed = discord.Embed(
                title=f"Incident {incident_id}",
                description=f"**Reason:** {incident['details']['reason']}",
                color=0xff0000
            )
            embed.add_field(
                name="Messages",
                value=messages[:1020] + "..." if len(messages) > 1024 else messages,
                inline=False
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Incident review error: {e}")
            await interaction.response.send_message(
                "❌ Failed to retrieve incident",
                ephemeral=True
            )

    client.tree.add_command(moments_group)
