import logging

import discord

from config import Config

logger = logging.getLogger(__name__)


class DiscordClient:
    def __init__(self, config: Config):
        self.config = config
        self.client = discord.Client(intents=discord.Intents.default())

    async def send_dm(self, message: str) -> None:
        await self.client.login(self.config.discord_bot_token)

        try:
            user = await self.client.fetch_user(self.config.discord_user_id)
            dm_channel = await user.create_dm()

            # Discord has a 2000 character limit per message
            # Split into chunks if needed
            chunks = self._split_message(message, 1900)

            for chunk in chunks:
                await dm_channel.send(chunk)
                logger.info(f"Sent message chunk ({len(chunk)} chars)")

        finally:
            await self.client.close()

    def _split_message(self, message: str, max_length: int) -> list[str]:
        if len(message) <= max_length:
            return [message]

        chunks = []
        lines = message.split("\n")
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.rstrip())
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"

        if current_chunk:
            chunks.append(current_chunk.rstrip())

        return chunks
