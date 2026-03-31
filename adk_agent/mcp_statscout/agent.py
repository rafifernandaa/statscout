import os
import google.auth
import dotenv

from google.adk.agents import LlmAgent
from google.adk.tools.bigquery import BigQueryToolset, BigQueryCredentialsConfig
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode

dotenv.load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "project_not_set")
DATASET_ID = os.getenv("BQ_DATASET", "statscout_data")
MODEL      = os.getenv("STATSCOUT_MODEL", "gemini-2.5-flash")


def build_agent() -> LlmAgent:
    credentials, _ = google.auth.default()

    toolset = BigQueryToolset(
        credentials_config=BigQueryCredentialsConfig(credentials=credentials),
        bigquery_tool_config=BigQueryToolConfig(write_mode=WriteMode.BLOCKED),
    )

    return LlmAgent(
        model=MODEL,
        name="statscout_agent",
        instruction=f"""You are StatScout, an academic dataset intelligence agent.
Query the BigQuery dataset `{PROJECT_ID}.{DATASET_ID}`.

Tables:
- `demographics`         — age, gender, education, income, region
- `bakery_prices`        — product price, margin, competitor benchmarks
- `sales_history_weekly` — 52-week sales: units, revenue, promotions
- `foot_traffic`         — hourly visitors, dwell time, conversion rates

Steps:
1. Use list_dataset_ids or get_table_info to explore schema if needed.
2. Use execute_sql to run queries against `{PROJECT_ID}.{DATASET_ID}`.
3. Present results as:

📊 StatScout Report — [topic]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Source: {PROJECT_ID}.{DATASET_ID}.[table]
📈 Key Findings: [numbers from query]
🔬 Interpretation: [plain-language summary]
⚠️ Caveats: [sample size, time range, data notes]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rules:
- Only query `{PROJECT_ID}.{DATASET_ID}`.
- Never fabricate numbers.
- Project for billing: {PROJECT_ID}.
""",
        tools=[toolset],
    )
