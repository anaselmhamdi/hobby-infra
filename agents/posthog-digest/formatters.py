from datetime import datetime, timezone

from config import PostHogProject, ProjectMetrics

# Color emoji mapping
COLOR_EMOJIS = {
    3447003: "\U0001f535",    # Blue
    10181046: "\U0001f7e3",   # Purple
    15844367: "\U0001f7e1",   # Gold/Yellow
    3066993: "\U0001f7e2",    # Green
    15158332: "\U0001f534",   # Red (for errors)
}


def format_number(n: int) -> str:
    return f"{n:,}"


def format_change(current: int, previous: int | None) -> str:
    """Format a metric with week-over-week change indicator."""
    if previous is None or previous == 0:
        return format_number(current)

    change = current - previous
    pct = (change / previous) * 100

    if abs(pct) < 1:
        arrow = "\u2194"  # ↔ (no change)
        sign = ""
    elif change > 0:
        arrow = "\u2191"  # ↑
        sign = "+"
    else:
        arrow = "\u2193"  # ↓
        sign = ""

    return f"{format_number(current)} {arrow} {sign}{pct:.0f}%"


def format_metric_row(label: str, current: int, previous: int | None) -> str:
    """Format a single metric with its label and change."""
    return f"{label}: {format_change(current, previous)}"


def format_project_section(project: PostHogProject, metrics: ProjectMetrics) -> str:
    emoji = COLOR_EMOJIS.get(project.color, "\u26aa")

    lines = [
        f"{emoji} **{project.name}**",
        "",
        # User metrics with comparison
        f"DAU: {format_change(metrics.dau, metrics.prev_dau)}",
        f"WAU: {format_change(metrics.wau, metrics.prev_wau)}",
        f"MAU: {format_change(metrics.mau, metrics.prev_mau)}",
        "",
        f"Pageviews: {format_change(metrics.pageviews_24h, metrics.prev_pageviews_24h)}",
    ]

    if metrics.top_pages:
        lines.append("")
        lines.append("Top Pages:")
        for page, views in metrics.top_pages[:5]:
            # Truncate long URLs
            display_page = page if len(page) <= 40 else page[:37] + "..."
            lines.append(f"  {display_page} \u2192 {format_number(views)}")

    if metrics.custom_events:
        lines.append("")
        lines.append("Custom Events:")
        for event, count in metrics.custom_events.items():
            prev_count = metrics.prev_custom_events.get(event)
            lines.append(f"  {event}: {format_change(count, prev_count)}")

    return "\n".join(lines)


def format_error_section(project: PostHogProject, error: str) -> str:
    return f"\U0001f534 **{project.name}** - ERROR\n  {error[:100]}"


def format_summary(results: list[tuple[PostHogProject, ProjectMetrics]]) -> str:
    """Format a summary section with totals across all projects."""
    if not results:
        return ""

    total_dau = sum(m.dau for _, m in results)
    total_prev_dau = sum(m.prev_dau or 0 for _, m in results)
    total_pageviews = sum(m.pageviews_24h for _, m in results)
    total_prev_pageviews = sum(m.prev_pageviews_24h or 0 for _, m in results)

    lines = [
        "\U0001f4ca **Summary (All Projects)**",
        f"Total DAU: {format_change(total_dau, total_prev_dau if total_prev_dau > 0 else None)}",
        f"Total Pageviews: {format_change(total_pageviews, total_prev_pageviews if total_prev_pageviews > 0 else None)}",
    ]

    return "\n".join(lines)


def format_digest(
    results: list[tuple[PostHogProject, ProjectMetrics]],
    errors: list[tuple[PostHogProject, str]],
) -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"\U0001f4c8 **Daily Analytics Digest** - {date_str}",
        "_Week-over-week comparison (vs 7 days ago)_",
        "",
    ]

    # Add summary at the top
    if results:
        lines.append(format_summary(results))
        lines.append("")

    # Individual projects
    for project, metrics in results:
        lines.append("\u2500" * 30)
        lines.append(format_project_section(project, metrics))

    for project, error in errors:
        lines.append("\u2500" * 30)
        lines.append(format_error_section(project, error))

    lines.append("\u2500" * 30)

    return "\n".join(lines)
