import os
import logging
import discord
from discord import app_commands
from dotenv import load_dotenv
from pydantic_settings import BaseSettings


# Configuration
class Settings(BaseSettings):
    DISCORD_TOKEN: str
    DISCORD_GUILD: int

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


config = Settings()


# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


class EmeraldClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.reactions = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Load commands
        from commands.moments import setup as moments_setup
        await moments_setup(self)

        # Sync commands
        guild = discord.Object(id=config.DISCORD_GUILD)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        logging.info("Commands synced")

    async def on_ready(self):
        logging.info(f"Logged in as {self.user}")
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="/moments"
        ))


if __name__ == "__main__":
    load_dotenv()
    client = EmeraldClient()

    # Global error handler
    @client.tree.error
    async def on_error(interaction: discord.Interaction, error):
        logging.error(f"Error: {error}")
        await interaction.response.send_message(
            "⚠️ Something went wrong. Please try again.",
            ephemeral=True
        )

    client.run(config.DISCORD_TOKEN)
