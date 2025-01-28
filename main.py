import os
import logging
import discord
from discord import app_commands
from dotenv import load_dotenv
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DISCORD_TOKEN: str
    DISCORD_GUILD: int

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


config = Settings()

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


class EmeraldClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        """Sync commands with test guild"""
        guild = discord.Object(id=config.DISCORD_GUILD)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        logging.info("Commands synced to guild")

    async def on_ready(self):
        logging.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="your requests"
        ))


if __name__ == "__main__":
    load_dotenv()
    client = EmeraldClient()
    client.run(config.DISCORD_TOKEN)