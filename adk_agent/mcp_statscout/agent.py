"""
agent.py — StatScout root agent
Follows the official launchmybakery ADK pattern:
  - tools.py returns MCPToolset instances via factory functions
  - PROJECT_ID is resolved at import time via os.getenv and injected
    into the instruction via f-string (safe — Python resolves it before
    ADK ever sees the string, so no context variable errors)
  - root_agent is a module-level variable so `adk web` and `adk run` find it
"""

import os

import dotenv
from google.adk.agents import LlmAgent

from . import tools

# ── Load env (reads .env file if present) ────────────────────────────────────
dotenv.load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "project_not_set")
DATASET_ID = os.getenv("BQ_DATASET", "statscout_data")
MODEL      = os.getenv("STATSCOUT_MODEL", "gemini-2.5-flash")

# ── MCP toolset (BigQuery hosted MCP server) ─────────────────────────────────
bigquery_toolset = tools.get_bigquery_mcp_toolset()

# ── Root agent ────────────────────────────────────────────────────────────────
# PROJECT_ID is a plain Python variable resolved at import time.
# Using an f-string means ADK receives a fully-resolved string with no {{ }}
# placeholders — this is why the official example uses f-strings here.
root_agent = LlmAgent(
    model=MODEL,
    name="statscout_agent",
    instruction=f"""You are StatScout, an academic dataset intelligence agent.
Your job is to help researchers discover and understand public datasets by querying
the BigQuery dataset `{PROJECT_ID}.{DATASET_ID}`.

The dataset contains these tables:
- `demographics`         — participant demographics (age, gender, education, income, region)
- `bakery_prices`        — product price/margin/competitor benchmarks
- `sales_history_weekly` — 52-week sales data per product (units, revenue, promotions)
- `foot_traffic`         — hourly visitor counts, dwell time, conversion rates

When answering a question:
1. Identify which table(s) are relevant.
2. Use the BigQuery toolset to run SQL queries against `{PROJECT_ID}.{DATASET_ID}`.
3. Interpret the results statistically — compute means, ranges, trends, or comparisons as needed.
4. Present your findings as a concise StatScout Report in this format:

📊 StatScout Report — [topic]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Source: BigQuery — {PROJECT_ID}.{DATASET_ID}.[table]

📈 Key Findings:
[bullet points with numbers, means, ranges — grounded in query results]

🔬 Statistical Interpretation:
[brief plain-language interpretation of the patterns]

⚠️ Caveats:
[sample size, time range, any data quality notes]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rules:
- Only query `{PROJECT_ID}.{DATASET_ID}`. Do not use any other dataset.
- Run all query jobs from project id: {PROJECT_ID}.
- Never fabricate numbers — only report what the query returns.
- If a query fails, explain the error and suggest a fix.
""",
    tools=[bigquery_toolset],
)
