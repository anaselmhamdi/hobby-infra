import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PostHogProject:
    name: str
    project_id: str
    color: int = 3447003  # Default blue
    custom_events: list[str] = field(default_factory=list)


@dataclass
class Config:
    posthog_api_key: str
    posthog_region: str  # "us" or "eu"
    discord_bot_token: str
    discord_user_id: int
    projects: list[PostHogProject]

    @classmethod
    def from_env(cls) -> "Config":
        projects_json = os.environ.get("POSTHOG_PROJECTS", "[]")
        projects_data = json.loads(projects_json)

        projects = [
            PostHogProject(
                name=p["name"],
                project_id=str(p["projectId"]),
                color=p.get("color", 3447003),
                custom_events=p.get("customEvents", []),
            )
            for p in projects_data
        ]

        return cls(
            posthog_api_key=os.environ["POSTHOG_API_KEY"],
            posthog_region=os.environ.get("POSTHOG_REGION", "eu"),
            discord_bot_token=os.environ["DISCORD_BOT_TOKEN"],
            discord_user_id=int(os.environ["DISCORD_USER_ID"]),
            projects=projects,
        )


@dataclass
class ProjectMetrics:
    dau: int = 0
    wau: int = 0
    mau: int = 0
    pageviews_24h: int = 0
    top_pages: list[tuple[str, int]] = field(default_factory=list)
    custom_events: dict[str, int] = field(default_factory=dict)
    # Week-over-week comparison (previous week's values)
    prev_dau: int | None = None
    prev_wau: int | None = None
    prev_mau: int | None = None
    prev_pageviews_24h: int | None = None
    prev_custom_events: dict[str, int] = field(default_factory=dict)
