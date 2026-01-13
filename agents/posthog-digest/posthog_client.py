import asyncio
import logging
from typing import Any

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import Config, PostHogProject, ProjectMetrics

logger = logging.getLogger(__name__)


class PostHogAPIError(Exception):
    pass


# Default colors for auto-discovered projects
PROJECT_COLORS = [3447003, 10181046, 15844367, 3066993, 15105570, 3426654, 16776960, 9807270]


class PostHogClient:
    def __init__(self, config: Config):
        self.config = config
        self.base_url = f"https://{config.posthog_region}.posthog.com"
        self.headers = {
            "Authorization": f"Bearer {config.posthog_api_key}",
            "Content-Type": "application/json",
        }
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def discover_projects(self) -> list[PostHogProject]:
        """Discover all projects accessible with the API key."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")

        url = f"{self.base_url}/api/projects/"
        async with self.session.get(url, headers=self.headers) as response:
            if response.status >= 400:
                text = await response.text()
                raise PostHogAPIError(f"Failed to list projects: {response.status} - {text[:200]}")
            data = await response.json()

        projects = []
        results = data.get("results", data) if isinstance(data, dict) else data

        for i, project in enumerate(results):
            project_id = str(project.get("id", ""))
            name = project.get("name", f"Project {project_id}")
            if project_id:
                projects.append(PostHogProject(
                    name=name,
                    project_id=project_id,
                    color=PROJECT_COLORS[i % len(PROJECT_COLORS)],
                    custom_events=[],
                ))
                logger.info(f"Discovered project: {name} (ID: {project_id})")

        return projects

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(aiohttp.ClientError),
    )
    async def _query(self, project_id: str, query: dict[str, Any]) -> dict[str, Any]:
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")

        url = f"{self.base_url}/api/projects/{project_id}/query/"
        async with self.session.post(
            url, json={"query": query}, headers=self.headers
        ) as response:
            if response.status == 429:
                raise PostHogAPIError("Rate limited")
            if response.status >= 400:
                text = await response.text()
                raise PostHogAPIError(f"API error {response.status}: {text[:200]}")
            return await response.json()

    async def fetch_project_metrics(self, project: PostHogProject) -> ProjectMetrics:
        # Add small delay between projects for rate limiting
        await asyncio.sleep(0.3)

        # Fetch current period metrics
        dau = await self._fetch_active_users(project.project_id, "dau", "-1d")
        wau = await self._fetch_active_users(project.project_id, "weekly_active", "-7d")
        mau = await self._fetch_active_users(project.project_id, "monthly_active", "-30d")
        pageviews, top_pages = await self._fetch_pageviews(project.project_id, "-1d")

        # Fetch previous period metrics (7 days ago) for comparison
        prev_dau = await self._fetch_active_users(project.project_id, "dau", "-8d", "-7d")
        prev_wau = await self._fetch_active_users(project.project_id, "weekly_active", "-14d", "-7d")
        prev_mau = await self._fetch_active_users(project.project_id, "monthly_active", "-60d", "-30d")
        prev_pageviews, _ = await self._fetch_pageviews(project.project_id, "-8d", "-7d")

        # Auto-discover custom events (non-PostHog events) or use configured list
        event_names = project.custom_events
        if not event_names:
            event_names = await self._discover_custom_events(project.project_id)

        # Fetch custom events (current and previous)
        custom_events = {}
        prev_custom_events = {}
        for event_name in event_names:
            custom_events[event_name] = await self._fetch_event_count(
                project.project_id, event_name, "-1d"
            )
            prev_custom_events[event_name] = await self._fetch_event_count(
                project.project_id, event_name, "-8d", "-7d"
            )

        return ProjectMetrics(
            dau=dau,
            wau=wau,
            mau=mau,
            pageviews_24h=pageviews,
            top_pages=top_pages,
            custom_events=custom_events,
            prev_dau=prev_dau,
            prev_wau=prev_wau,
            prev_mau=prev_mau,
            prev_pageviews_24h=prev_pageviews,
            prev_custom_events=prev_custom_events,
        )

    async def _discover_custom_events(self, project_id: str, limit: int = 10) -> list[str]:
        """Discover top custom events (non-PostHog events) from the last 7 days."""
        query = {
            "kind": "HogQLQuery",
            "query": f"""
                SELECT
                    event,
                    count() as count
                FROM events
                WHERE timestamp >= now() - INTERVAL 7 DAY
                  AND event NOT LIKE '$%'
                  AND event NOT LIKE '!%'
                GROUP BY event
                ORDER BY count DESC
                LIMIT {limit}
            """,
        }
        try:
            result = await self._query(project_id, query)
            events = [str(r[0]) for r in result.get("results", []) if r[0]]
            logger.info(f"Discovered {len(events)} custom events: {events}")
            return events
        except Exception as e:
            logger.warning(f"Failed to discover custom events: {e}")
            return []

    async def _fetch_active_users(
        self, project_id: str, math: str, date_from: str, date_to: str = "now"
    ) -> int:
        query = {
            "kind": "TrendsQuery",
            "series": [{"kind": "EventsNode", "event": "$pageview", "math": math}],
            "dateRange": {"date_from": date_from, "date_to": date_to},
        }
        result = await self._query(project_id, query)
        return self._extract_trend_value(result)

    async def _fetch_pageviews(
        self, project_id: str, date_from: str = "-1d", date_to: str = "now"
    ) -> tuple[int, list[tuple[str, int]]]:
        # Calculate interval based on date range
        if date_to == "now":
            interval = "1 DAY"
            time_filter = "timestamp >= now() - INTERVAL 1 DAY"
        else:
            # For previous period comparison (e.g., -8d to -7d)
            time_filter = f"timestamp >= now() - INTERVAL 8 DAY AND timestamp < now() - INTERVAL 7 DAY"

        query = {
            "kind": "HogQLQuery",
            "query": f"""
                SELECT
                    properties.$current_url as page,
                    count() as views
                FROM events
                WHERE event = '$pageview'
                  AND {time_filter}
                GROUP BY page
                ORDER BY views DESC
                LIMIT 10
            """,
        }
        result = await self._query(project_id, query)

        results = result.get("results", [])
        top_pages = [(str(r[0])[:50], int(r[1])) for r in results[:5] if r[0]]
        total_pageviews = sum(int(r[1]) for r in results if len(r) > 1)

        return total_pageviews, top_pages

    async def _fetch_event_count(
        self, project_id: str, event_name: str, date_from: str = "-1d", date_to: str = "now"
    ) -> int:
        query = {
            "kind": "TrendsQuery",
            "series": [{"kind": "EventsNode", "event": event_name, "math": "total"}],
            "dateRange": {"date_from": date_from, "date_to": date_to},
        }
        result = await self._query(project_id, query)
        return self._extract_trend_value(result)

    def _extract_trend_value(self, result: dict[str, Any]) -> int:
        try:
            data = result.get("results", [{}])[0].get("data", [])
            if data:
                return int(data[-1])
            return 0
        except (KeyError, IndexError, TypeError):
            return 0
