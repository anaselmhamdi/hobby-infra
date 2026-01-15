# PostHog Daily Digest

A Python agent that fetches analytics from all your PostHog projects and sends a daily digest via Discord DM.

## Features

- **Auto-discovers projects** - Finds all projects accessible with your API key
- **Auto-discovers custom events** - Detects top 10 custom events per project
- **Week-over-week comparison** - Shows trends with ↑↓ indicators for all metrics
- **Discord DM delivery** - Sends digest directly to your DMs

## Metrics Included

- DAU / WAU / MAU (Daily, Weekly, Monthly Active Users)
- Pageviews (24h)
- Top 5 pages
- Custom events with counts

## Setup

### 1. Get PostHog API Key

1. Go to PostHog → Settings → Personal API Keys
2. Create a new key with read access

### 2. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create New Application → Name it "PostHog Digest"
3. Go to Bot tab → Click "Reset Token" → Copy the token
4. Invite bot to a server you're in:
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_APP_ID&permissions=0&scope=bot
   ```

### 3. Get Your Discord User ID

1. Discord Settings → Advanced → Enable Developer Mode
2. Right-click your username → Copy User ID

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values
```

Required variables:
| Variable | Description |
|----------|-------------|
| `POSTHOG_API_KEY` | Your PostHog personal API key |
| `POSTHOG_REGION` | `eu` or `us` (default: `eu`) |
| `DISCORD_BOT_TOKEN` | Bot token from Developer Portal |
| `DISCORD_USER_ID` | Your Discord user ID |

## Usage

### Install & Run

```bash
# Install dependencies
uv sync

# Run (loads .env automatically)
uv run python main.py

# Or with explicit env vars
POSTHOG_API_KEY=xxx DISCORD_BOT_TOKEN=xxx DISCORD_USER_ID=123 uv run python main.py
```

### Run Daily (Cron)

```bash
# Edit crontab
crontab -e

# Add line (runs daily at 8am)
0 8 * * * cd /path/to/agents/posthog-digest && set -a && source .env && set +a && uv run python main.py
```

## Example Output

```
📈 Daily Analytics Digest - 2024-01-15
Week-over-week comparison (vs 7 days ago)

📊 Summary (All Projects)
Total DAU: 45 ↑ +12%
Total Pageviews: 1,234 ↓ -5%

──────────────────────────────────
🔵 My App
DAU: 25 ↑ +15%
WAU: 150 ↑ +8%
MAU: 500 ↔ 0%

Pageviews: 800 ↓ -3%

Top Pages:
  /home → 300
  /dashboard → 200

Custom Events:
  signup: 12 ↑ +20%
  purchase: 5 ↓ -10%
──────────────────────────────────
```

## Project Structure

```
posthog-digest/
├── main.py           # Entry point
├── config.py         # Configuration from env vars
├── posthog_client.py # PostHog API client
├── discord_client.py # Discord bot DM sender
├── formatters.py     # Message formatting
├── pyproject.toml    # Dependencies (uv)
└── .env.example      # Environment template
```
