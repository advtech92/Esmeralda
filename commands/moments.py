import discord
from discord import app_commands
from typing import Optional, List
from datetime import datetime
import logging
from utils.database import Database

db = Database()


class IncidentModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Log Incident")
        self.reason = discord.ui.TextInput(
            label="Reason for logging",
            style=discord.TextStyle.long,
            required=True
        )
        self.message_count = discord.ui.TextInput(
            label="Messages to capture (1-50)",
            default="10",
            required=True
        )

        self.add_item(self.reason)
        self.add_item(self.message_count)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            count = int(self.message_count.value)
            if not 1 <= count <= 50:
                raise ValueError

            messages = [
                msg async for msg in interaction.channel.history(limit=count)
            ][::-1]

            formatted_messages = [{
                "id": msg.id,
                "author_id": msg.author.id,
                "content": msg.content,
                "timestamp": msg.created_at
            } for msg in messages]

            incident_id = f"incident_{int(datetime.now().timestamp())}"

            success = db.add_incident(
                incident_id=incident_id,
                reason=self.reason.value,
                moderator_id=interaction.user.id,
                messages=formatted_messages
            )

            if not success:
                raise Exception("Database storage failed")

            embed = discord.Embed(
                title="Incident Logged",
                description=f"**ID:** `{incident_id}`\n**Reason:** {self.reason.value}",
                color=0xff0000
            )
            preview = messages[0].content[:50] + "..." if messages else "No messages"
            embed.add_field(name="First Message", value=preview, inline=False)

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a number between 1-50",
                ephemeral=True
            )


async def setup(client):
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

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        except Exception as e:
            logging.error(f"Context menu error: {e}")
            await interaction.response.send_message(
                "❌ Couldn't mark this message. Is it too old?",
                ephemeral=True
            )

    # Command group
    moments_group = app_commands.Group(
        name="moments",
        description="Manage memorable moments"
    )

    # Incident command
    @moments_group.command(
        name="incident",
        description="Log an incident with recent messages"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def incident_log(interaction: discord.Interaction):
        await interaction.response.send_modal(IncidentModal())

    # Review command
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

    # Autocomplete
    @review_incident.autocomplete("incident_id")
    async def incident_autocomplete(
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        incidents = db.get_recent_incidents(interaction.user.id, 25)
        return [
            app_commands.Choice(name=inc["id"], value=inc["id"])
            for inc in incidents if current.lower() in inc["id"].lower()
        ][:25]

    client.tree.add_command(moments_group)
