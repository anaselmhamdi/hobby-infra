#!/usr/bin/env python3
import asyncio
import logging
import sys

from config import Config
from discord_client import DiscordClient
from formatters import format_digest
from posthog_client import PostHogClient, PostHogAPIError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> int:
    logger.info("Starting PostHog daily digest")

    try:
        config = Config.from_env()
    except KeyError as e:
        logger.error(f"Missing required environment variable: {e}")
        return 1

    results = []
    errors = []

    async with PostHogClient(config) as posthog:
        # Auto-discover projects if none configured
        projects = config.projects
        if not projects:
            logger.info("No projects configured, discovering from PostHog...")
            try:
                projects = await posthog.discover_projects()
                logger.info(f"Discovered {len(projects)} projects")
            except PostHogAPIError as e:
                logger.error(f"Failed to discover projects: {e}")
                return 1

        if not projects:
            logger.error("No projects found")
            return 1

        logger.info(f"Fetching metrics for {len(projects)} projects")
        for project in projects:
            try:
                logger.info(f"Fetching metrics for {project.name}")
                metrics = await posthog.fetch_project_metrics(project)
                results.append((project, metrics))
                logger.info(
                    f"  DAU={metrics.dau}, WAU={metrics.wau}, MAU={metrics.mau}"
                )
            except PostHogAPIError as e:
                logger.error(f"PostHog API error for {project.name}: {e}")
                errors.append((project, str(e)))
            except Exception as e:
                logger.exception(f"Unexpected error for {project.name}")
                errors.append((project, str(e)))

    if not results and not errors:
        logger.warning("No data to send")
        return 0

    # Format the digest message
    message = format_digest(results, errors)
    logger.info(f"Formatted digest ({len(message)} chars)")

    # Send via Discord DM
    discord = DiscordClient(config)
    try:
        await discord.send_dm(message)
        logger.info("Digest sent successfully")
    except Exception as e:
        logger.error(f"Failed to send Discord DM: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
