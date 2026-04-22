---
name: content-intelligence
description: Use when scanning the data ecosystem for content opportunities, generating a daily content brief, or populating the Content Pipeline Notion database with ranked content ideas tied to dbt Labs content pillars
---

# Content Intelligence Agent

Scans RSS feeds, Hacker News, Reddit, and news sources for trending data ecosystem conversations. Scores signals by strategic relevance, freshness, and engagement. Writes a ranked daily brief to Notion and creates Content Pipeline database entries.

## When to Use

- Morning content brief generation ("run today's content scan")
- Ad-hoc signal scanning ("what's trending in analytics engineering?")
- Populating the Content Pipeline with new ideas
- Researching a specific topic across data ecosystem sources

## Mode 1: MCP Playbook (Cowork / Claude Code)

Follow these 6 steps using WebFetch, WebSearch, and Notion MCP tools. No Python or API keys needed.

### Step 1 — Gather Signals

Fetch from ALL sources. If one fails, skip it and continue.

**RSS Feeds** (WebFetch each):

| Source | URL |
|--------|-----|
| Snowflake Blog | `https://www.snowflake.com/feed/` |
| Databricks Blog | `https://www.databricks.com/feed` |
| dbt Discourse | `https://discourse.getdbt.com/latest.rss` |
| r/dataengineering | `https://www.reddit.com/r/dataengineering/hot.json?limit=25` |

**Hacker News** (WebFetch each separately — Algolia doesn't support OR):
- `https://hn.algolia.com/api/v1/search_by_date?query=dbt&tags=story&hitsPerPage=10`
- `https://hn.algolia.com/api/v1/search_by_date?query=%22analytics+engineering%22&tags=story&hitsPerPage=10`
- `https://hn.algolia.com/api/v1/search_by_date?query=%22data+transformation%22&tags=story&hitsPerPage=10`

**Web Search** (WebSearch each):
- `"analytics engineering" trending news`
- `"dbt data" news this week`
- `"agentic data engineering" OR "AI data pipelines"`

Extract from each: title, URL, summary, publish date, engagement metrics.

### Step 2 — Filter by Content Pillars

Keep only items matching at least one pillar:

| Pillar | Keywords |
|--------|----------|
| **Agentic Eng** | agentic, ai agent, llm pipeline, autonomous data, vibe coding, copilot data |
| **Analytics Eng** | analytics engineering, dbt, sql transformation, data testing, data modeling, semantic layer |
| **Modern Data Stack** | modern data stack, data warehouse, lakehouse, snowflake, databricks, bigquery, orchestration, data observability |
| **dbt Product** | dbt cloud, dbt core, dbt mesh, dbt explorer, dbt semantic layer |
| **Data Culture** | data governance, data contracts, data mesh org, data team, analytics team, data literacy |

Discard pure ML/deep learning or unrelated product announcements.

### Step 3 — Score (1-10)

For each signal, compute: `score = (strategic x 0.5) + (freshness x 0.3) + (engagement x 0.2)`

**Strategic fit (50%):** 10 = directly about dbt/AE, 7 = adjacent with clear angle, 4 = tangential, 1 = barely relevant

**Freshness (30%):** 10 = today, 7 = yesterday, 4 = 2 days, 1 = 3+ days

**Engagement (20%):** 10 = viral (100+ points), 7 = strong (50+), 4 = moderate (10+), 1 = low

For each, also generate: a 1-2 sentence content angle, suggested format(s), and engagement level (High/Medium/Low).

### Step 4 — Write Notion Brief

Create a page under **Content Intelligence Briefs** (page ID: `32ebb38e-bda7-8120-8362-dbbba6349d53`) using `mcp__claude_ai_Notion__notion-create-pages`.

Properties: `title`: "Content Brief -- [YYYY-MM-DD]", `icon`: "📊"

Page content (Notion-flavored Markdown):

```
## Top 3 Opportunities

### 1. [Title]
**Pillar:** [name] · **Score:** [X.X]/10 · **Source:** [platform]

[2-3 sentence content angle]

**Suggested format:** [format(s)]

---

[repeat for #2, #3]

## Full Ranked List

<table header-row="true" fit-page-width="true">
  <tr>
    <td>**#**</td>
    <td>**Opportunity**</td>
    <td>**Pillar**</td>
    <td>**Score**</td>
    <td>**Source**</td>
    <td>**Why Now**</td>
  </tr>
  [one row per opportunity, sorted by score desc]
</table>

## Raw Signals

- [Title](URL) -- 1-line context
[for each source signal]
```

### Step 5 — Create Content Pipeline DB Entries

For the **top 10**, create entries in the Content Pipeline database using `mcp__claude_ai_Notion__notion-create-pages` with `data_source_id: 3e757691-8564-403f-bab4-4ad466f98683`.

Properties per entry:

| Property | Value |
|----------|-------|
| `"Title"` | opportunity headline |
| `"Stage"` | `"Backlog"` |
| `"Pillar"` | JSON array from `["Agentic Eng", "Analytics Eng", "Modern Data Stack", "dbt Product", "Data Culture"]` |
| `"Content Type"` | JSON array from `["Blog post", "Social post", "Newsletter", "Video", "Webinar", "Short-form", "Podcast", "Case Study"]` |
| `"Content Angle"` | 1-2 sentence angle |
| `"Score"` | float (composite score) |
| `"Engagement Signal"` | `"High"`, `"Medium"`, or `"Low"` |
| `"Source URL"` | link to original |
| `"Source Platform"` | one of `"Reddit"`, `"HN"`, `"Snowflake Blog"`, `"Databricks Blog"`, `"BigQuery Blog"`, `"Discourse"`, `"News"` |
| `"date:Brief Date:start"` | `YYYY-MM-DD` |
| `"date:Brief Date:is_datetime"` | `0` |
| `"Quarter"` | JSON array with current FQ (dbt FY starts Feb 1; e.g. Mar 2026 = `["FY26 Q3"]`) |

Batch all 10 in one `mcp__claude_ai_Notion__notion-create-pages` call.

### Step 6 — Summary

Report: signals gathered, signals after filtering, DB entries created, top opportunity title and score.

---

## Mode 2: Python Agent (Local / Cron)

For running as a standalone Python script with API-based scoring and persistent deduplication. Requires `ANTHROPIC_API_KEY` and `NOTION_TOKEN` env vars.

**Setup:**
```bash
uv init --name contented-but-not-satisfied --python 3.12
mkdir -p src/collectors src/scoring src/outputs tests
touch src/__init__.py src/collectors/__init__.py src/scoring/__init__.py src/outputs/__init__.py tests/__init__.py
```

Add to `pyproject.toml` dependencies:
```
anthropic>=0.50.0
feedparser>=6.0
httpx>=0.27
notion-client>=2.0
```

### src/config.py

```python
"""Configuration for the Content Intelligence Agent."""

from dataclasses import dataclass, field

PILLARS: dict[str, list[str]] = {
    "Agentic Eng": [
        "agentic", "ai agent", "llm pipeline", "autonomous data",
        "vibe coding", "ai-assisted", "copilot data", "genie code",
    ],
    "Analytics Eng": [
        "analytics engineering", "dbt", "sql transformation", "data testing",
        "data documentation", "data modeling", "semantic layer", "metrics layer",
    ],
    "Modern Data Stack": [
        "modern data stack", "data warehouse", "lakehouse", "snowflake",
        "databricks", "bigquery", "orchestration", "data observability",
        "data catalog", "data lineage",
    ],
    "dbt Product": [
        "dbt cloud", "dbt core", "dbt mesh", "dbt explorer",
        "dbt semantic layer", "dbt build", "dbt run", "dbt test",
    ],
    "Data Culture": [
        "data governance", "data contracts", "data mesh org",
        "data team", "analytics team", "data culture", "data literacy",
    ],
}

RSS_FEEDS: dict[str, str] = {
    "Snowflake Blog": "https://www.snowflake.com/feed/",
    "Databricks Blog": "https://www.databricks.com/feed",
    "Discourse": "https://discourse.getdbt.com/latest.rss",
}

REDDIT_JSON_URL = "https://www.reddit.com/r/dataengineering/hot.json"
REDDIT_USER_AGENT = "ContentAgent/1.0"

HN_API_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_QUERIES = ["dbt", '"analytics engineering"', '"data transformation"']

WEB_SEARCH_QUERIES = [
    '"analytics engineering" trending news',
    '"dbt data" news this week',
    '"agentic data engineering" OR "AI data pipelines"',
]

NOTION_BRIEFS_PAGE_ID = "32ebb38e-bda7-8120-8362-dbbba6349d53"
NOTION_PIPELINE_DATASOURCE_ID = "3e757691-8564-403f-bab4-4ad466f98683"

WEIGHT_STRATEGIC = 0.5
WEIGHT_FRESHNESS = 0.3
WEIGHT_ENGAGEMENT = 0.2
MAX_DB_ENTRIES = 10
TOP_BRIEF_COUNT = 3


@dataclass
class Signal:
    title: str
    url: str
    summary: str
    source_platform: str
    published: str
    engagement: int = 0
    pillars: list[str] = field(default_factory=list)
    score: float = 0.0
    content_angle: str = ""
    engagement_level: str = "Low"
    content_types: list[str] = field(default_factory=list)
```

### src/collectors/rss.py

```python
import feedparser
from src.config import RSS_FEEDS, Signal


def collect_rss() -> list[Signal]:
    signals: list[Signal] = []
    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                published = getattr(entry, "published", "") or getattr(entry, "updated", "")
                summary = (getattr(entry, "summary", "") or getattr(entry, "description", ""))[:300]
                signals.append(Signal(
                    title=entry.get("title", "Untitled"), url=entry.get("link", ""),
                    summary=summary, source_platform=source_name, published=published,
                ))
        except Exception as e:
            print(f"[WARN] Failed to fetch {source_name}: {e}")
    return signals
```

### src/collectors/hn.py

```python
import time
import httpx
from src.config import HN_API_URL, HN_QUERIES, Signal


def collect_hn() -> list[Signal]:
    signals: list[Signal] = []
    cutoff = int(time.time()) - 86400
    for query in HN_QUERIES:
        try:
            resp = httpx.get(HN_API_URL, params={
                "query": query, "tags": "story",
                "numericFilters": f"created_at_i>{cutoff}", "hitsPerPage": 10,
            }, timeout=15)
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
                signals.append(Signal(
                    title=hit.get("title", "Untitled"), url=url,
                    summary=f"HN: {hit.get('points', 0)} pts, {hit.get('num_comments', 0)} comments",
                    source_platform="HN", published=hit.get("created_at", ""),
                    engagement=hit.get("points", 0),
                ))
        except Exception as e:
            print(f"[WARN] HN query '{query}' failed: {e}")
    seen: set[str] = set()
    return [s for s in signals if not (s.url in seen or seen.add(s.url))]
```

### src/collectors/reddit.py

```python
import httpx
from src.config import REDDIT_JSON_URL, REDDIT_USER_AGENT, Signal


def collect_reddit() -> list[Signal]:
    signals: list[Signal] = []
    try:
        resp = httpx.get(REDDIT_JSON_URL, params={"limit": 25},
            headers={"User-Agent": REDDIT_USER_AGENT}, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        for post in resp.json().get("data", {}).get("children", []):
            d = post.get("data", {})
            if d.get("stickied"):
                continue
            signals.append(Signal(
                title=d.get("title", "Untitled"),
                url=f"https://www.reddit.com{d.get('permalink', '')}",
                summary=(d.get("selftext", "")[:300] or d.get("title", "")),
                source_platform="Reddit", published=str(d.get("created_utc", "")),
                engagement=d.get("ups", 0),
            ))
    except Exception as e:
        print(f"[WARN] Reddit fetch failed: {e}")
    return signals
```

### src/scoring/pillars.py

```python
from src.config import PILLARS, Signal


def match_pillars(signal: Signal) -> list[str]:
    text = f"{signal.title} {signal.summary}".lower()
    return [name for name, kws in PILLARS.items() if any(kw in text for kw in kws)]


def filter_by_pillars(signals: list[Signal]) -> list[Signal]:
    filtered = []
    for s in signals:
        pillars = match_pillars(s)
        if pillars:
            s.pillars = pillars
            filtered.append(s)
    return filtered
```

### src/scoring/relevance.py

```python
from datetime import datetime, timezone
import anthropic
from src.config import WEIGHT_ENGAGEMENT, WEIGHT_FRESHNESS, WEIGHT_STRATEGIC, Signal

SCORING_PROMPT = """You are a content strategist for dbt Labs. Score each signal's strategic fit
on a scale of 1-10 based on alignment with dbt Labs' content pillars and ICP
(data teams at mid-to-large companies).

10 = directly about dbt or analytics engineering
7 = adjacent topic with clear content angle
4 = tangentially related, 1 = barely relevant

Also suggest: a 1-2 sentence content angle, and recommended content types from:
Blog post, Social post, Newsletter, Video, Webinar, Short-form, Podcast, Case Study.

Respond as JSON array: [{{"title": str, "strategic_score": int, "content_angle": str, "content_types": [str]}}]

Signals:
{signals_json}"""


def _freshness_score(published: str) -> float:
    if not published:
        return 4.0
    try:
        pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
    except ValueError:
        try:
            from email.utils import parsedate_to_datetime
            pub_date = parsedate_to_datetime(published)
        except Exception:
            return 4.0
    age_hours = (datetime.now(timezone.utc) - pub_date).total_seconds() / 3600
    if age_hours < 24: return 10.0
    elif age_hours < 48: return 7.0
    elif age_hours < 72: return 4.0
    else: return 1.0


def _engagement_score(engagement: int) -> float:
    if engagement >= 100: return 10.0
    elif engagement >= 50: return 7.0
    elif engagement >= 10: return 4.0
    else: return 1.0


def _engagement_level(engagement: int) -> str:
    if engagement >= 50: return "High"
    elif engagement >= 10: return "Medium"
    return "Low"


def score_signals_with_api(signals: list[Signal]) -> list[Signal]:
    import json
    signals_json = json.dumps(
        [{{"title": s.title, "summary": s.summary, "pillars": s.pillars}} for s in signals], indent=2)
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=4096,
        messages=[{{"role": "user", "content": SCORING_PROMPT.format(signals_json=signals_json)}}])
    response_text = response.content[0].text
    if "```" in response_text:
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"): response_text = response_text[4:]
    scored_by_title = {{s["title"]: s for s in json.loads(response_text)}}
    for signal in signals:
        api = scored_by_title.get(signal.title, {{}})
        signal.score = round(
            api.get("strategic_score", 5) * WEIGHT_STRATEGIC
            + _freshness_score(signal.published) * WEIGHT_FRESHNESS
            + _engagement_score(signal.engagement) * WEIGHT_ENGAGEMENT, 1)
        signal.content_angle = api.get("content_angle", "")
        signal.content_types = api.get("content_types", ["Blog post"])
        signal.engagement_level = _engagement_level(signal.engagement)
    return sorted(signals, key=lambda s: s.score, reverse=True)


def score_signals_keyword_only(signals: list[Signal]) -> list[Signal]:
    for signal in signals:
        strategic = min(10, len(signal.pillars) * 4 + 2)
        signal.score = round(
            strategic * WEIGHT_STRATEGIC
            + _freshness_score(signal.published) * WEIGHT_FRESHNESS
            + _engagement_score(signal.engagement) * WEIGHT_ENGAGEMENT, 1)
        signal.engagement_level = _engagement_level(signal.engagement)
        signal.content_types = ["Blog post"]
    return sorted(signals, key=lambda s: s.score, reverse=True)
```

### src/outputs/notion.py

```python
from datetime import date
from notion_client import Client
from src.config import (MAX_DB_ENTRIES, NOTION_BRIEFS_PAGE_ID,
    NOTION_PIPELINE_DATASOURCE_ID, TOP_BRIEF_COUNT, Signal)


def _current_quarter() -> str:
    today = date.today()
    fy_month = (today.month - 2) % 12 + 1
    fy_year = today.year if today.month >= 2 else today.year - 1
    quarter = (fy_month - 1) // 3 + 1
    return f"FY{fy_year - 2000 + 1} Q{quarter}"


def publish_brief(notion: Client, signals: list[Signal]) -> str:
    today = date.today().isoformat()
    top = signals[:TOP_BRIEF_COUNT]
    sections = ["## Top 3 Opportunities\n"]
    for i, s in enumerate(top, 1):
        sections.append(
            f"### {i}. {s.title}\n"
            f"**Pillar:** {', '.join(s.pillars)} | **Score:** {s.score}/10 | **Source:** {s.source_platform}\n\n"
            f"{s.content_angle}\n\n**Suggested format:** {', '.join(s.content_types)}\n\n---\n")
    page = notion.pages.create(
        parent={{"page_id": NOTION_BRIEFS_PAGE_ID}},
        icon={{"type": "emoji", "emoji": "📊"}},
        properties={{"title": {{"title": [{{"text": {{"content": f"Content Brief -- {{today}}"}}}]}}}}},
        children=[])
    notion.blocks.children.append(block_id=page["id"], children=[
        {{"object": "block", "type": "paragraph",
         "paragraph": {{"rich_text": [{{"type": "text", "text": {{"content": "\n".join(sections)[:2000]}}}}]}}}}])
    return page["url"]


def create_pipeline_entries(notion: Client, signals: list[Signal]) -> int:
    today, quarter, count = date.today().isoformat(), _current_quarter(), 0
    for signal in signals[:MAX_DB_ENTRIES]:
        try:
            notion.pages.create(
                parent={{"database_id": NOTION_PIPELINE_DATASOURCE_ID}},
                properties={{
                    "Title": {{"title": [{{"text": {{"content": signal.title}}}}]}},
                    "Stage": {{"select": {{"name": "Backlog"}}}},
                    "Pillar": {{"multi_select": [{{"name": p}} for p in signal.pillars]}},
                    "Content Type": {{"multi_select": [{{"name": ct}} for ct in signal.content_types]}},
                    "Content Angle": {{"rich_text": [{{"text": {{"content": signal.content_angle[:2000]}}}}]}},
                    "Score": {{"number": signal.score}},
                    "Engagement Signal": {{"select": {{"name": signal.engagement_level}}}},
                    "Source URL": {{"url": signal.url}},
                    "Source Platform": {{"select": {{"name": signal.source_platform}}}},
                    "Brief Date": {{"date": {{"start": today}}}},
                    "Quarter": {{"multi_select": [{{"name": quarter}}]}},
                }})
            count += 1
        except Exception as e:
            print(f"[WARN] Failed to create entry for '{signal.title}': {{e}}")
    return count
```

### src/agent.py

```python
import hashlib, json, os
from pathlib import Path
from src.collectors.hn import collect_hn
from src.collectors.reddit import collect_reddit
from src.collectors.rss import collect_rss
from src.config import Signal

CACHE_DIR = Path.home() / ".content-agent"
SEEN_FILE = CACHE_DIR / "seen.json"


def _load_seen() -> set[str]:
    if not SEEN_FILE.exists(): return set()
    return set(json.loads(SEEN_FILE.read_text()).get("hashes", []))

def _save_seen(hashes: set[str]) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    SEEN_FILE.write_text(json.dumps({{"hashes": list(hashes)}}))

def _signal_hash(s: Signal) -> str:
    return hashlib.sha256(f"{{s.title}}|{{s.url}}".encode()).hexdigest()[:16]


def main(use_api: bool = True) -> None:
    from src.scoring.pillars import filter_by_pillars

    # 1. Collect
    signals = collect_rss() + collect_hn() + collect_reddit()
    print(f"[1/6] Gathered {{len(signals)}} signals")

    # 2. Deduplicate
    seen = _load_seen()
    signals = [s for s in signals if _signal_hash(s) not in seen]
    print(f"[2/6] {{len(signals)}} new signals")

    # 3. Filter + Score
    signals = filter_by_pillars(signals)
    print(f"[3/6] {{len(signals)}} match pillars")
    if not signals: return

    if use_api:
        from src.scoring.relevance import score_signals_with_api
        signals = score_signals_with_api(signals)
    else:
        from src.scoring.relevance import score_signals_keyword_only
        signals = score_signals_keyword_only(signals)

    # 4-5. Publish
    notion_token = os.environ.get("NOTION_TOKEN")
    if notion_token:
        from notion_client import Client
        from src.outputs.notion import create_pipeline_entries, publish_brief
        notion = Client(auth=notion_token)
        url = publish_brief(notion, signals)
        count = create_pipeline_entries(notion, signals)
        print(f"[4-5] Brief: {{url}}, {{count}} entries")

    # 6. Archive
    for s in signals: seen.add(_signal_hash(s))
    _save_seen(seen)
    print(f"Top: {{signals[0].title}} ({{signals[0].score}}/10)")


if __name__ == "__main__":
    import sys
    main(use_api="--no-api" not in sys.argv)
```

**Run:** `uv sync && uv run python -m src.agent --no-api` (keyword scoring) or without `--no-api` (Claude API scoring, needs `ANTHROPIC_API_KEY`).

---

## Common Issues

| Issue | Fix |
|-------|-----|
| Snowflake RSS 404 | Use `https://www.snowflake.com/feed/` (redirects to Adobe AEM) |
| Reddit RSS blocked | Use `.json` endpoint with `User-Agent` header |
| HN returns 0 results | Make 3 separate API calls; Algolia doesn't support `OR` with quoted phrases |
| Notion create fails | Check that data_source_id `3e757691-8564-403f-bab4-4ad466f98683` still exists |
| Quarter calculation | dbt Labs FY starts Feb 1. March 2026 = FY26 Q3 |
