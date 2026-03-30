# StatScout 📊

**Academic Dataset Intelligence Agent** — Gen AI Academy APAC Track 2

> *Turning Uncertainty Into Insight — one dataset at a time.*

StatScout discovers and analyzes public research datasets from [OSF (Open Science Framework)](https://osf.io) using Google ADK, Gemini 2.5 Flash, and a custom Python MCP server.

---

## Project Structure

```
launchmybakery/
├── data/                            # Pre-generated reference CSVs (loaded into BigQuery)
│   ├── demographics.csv             # 500 participant records
│   ├── bakery_prices.csv            # 15 product price/margin records
│   ├── sales_history_weekly.csv     # 52-week × 15 product sales history
│   └── foot_traffic.csv             # 365-day × 6 hourly slot foot traffic
├── adk_agent/
│   └── mcp_bakery_app/
│       ├── agent.py                 # LlmAgent + MCPToolset + Runner
│       └── tools.py                 # Custom MCP server (3 OSF tools)
├── setup/
│   ├── setup_env.sh                 # Export GCP environment variables
│   └── setup_bigquery.sh            # Provision BQ dataset + upload CSVs
├── cleanup/
│   └── cleanup_env.sh               # Tear down all GCP resources
├── main.py                          # FastAPI entry point
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Architecture

```
User → POST /analyze (FastAPI · Cloud Run)
         └→ agent.py  (LlmAgent · gemini-2.5-flash)
               └→ MCPToolset (stdio transport)
                     └→ tools.py (custom MCP server)
                           ├→ search_osf_projects  → OSF REST API v2
                           ├→ get_dataset_files    → OSF File Storage API
                           └→ fetch_csv_preview    → OSF CSV download + pandas stats
```

### MCP Tools (tools.py)

| Tool | Input | What it does |
|------|-------|-------------|
| `search_osf_projects` | `query`, `limit` | Searches OSF by keyword, returns project IDs + titles |
| `get_dataset_files` | `project_id` | Lists CSV files in an OSF project |
| `fetch_csv_preview` | `file_url`, `rows` | Downloads CSV (≤5 MB), computes descriptive stats via pandas |

---

## Local Setup

### 1. Clone and create venv

```bash
git clone <your-repo-url>
cd launchmybakery

python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set environment variables

```bash
# Edit PROJECT_ID in setup/setup_env.sh first, then:
source setup/setup_env.sh
```

### 4. Authenticate

```bash
gcloud auth application-default login
```

### 5. (Optional) Load data into BigQuery

```bash
bash setup/setup_bigquery.sh
```

### 6. Run locally

```bash
python main.py
# → http://localhost:8080
```

### 7. Test

```bash
curl http://localhost:8080/health

curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "anxiety coping mechanisms"}'
```

---

## Cloud Run Deployment

```bash
source setup/setup_env.sh

# Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com \
  --project="${PROJECT_ID}"

# Create service account
gcloud iam service-accounts create statscout-sa \
  --display-name="StatScout SA" --project="${PROJECT_ID}"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:statscout-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Deploy
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --service-account "statscout-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION}" \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 120 \
  --project "${PROJECT_ID}"
```

---

## Cleanup

```bash
bash cleanup/cleanup_env.sh
```

---

## Example Output

```
📊 StatScout Report — Anxiety & Coping Mechanisms Study (OSF: abc12)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Variables: 14 | Observations: 623 | Format: CSV

🔑 Key Variables:
• age (int) — participant age
• GAD7_total (float) — GAD-7 scale total score
• coping_strategy (str) — self-reported coping approach

📈 Summary Statistics:
• GAD7_total: mean = 8.4, SD = 3.1, range = 0–21
• stress_level: mean = 18.7, SD = 4.9

🔬 Potential Research Uses:
1. IRT calibration of GAD-7 items
2. Moderation analysis: coping strategy × stress → anxiety
3. Latent profile analysis for anxiety subgroups

⚠️ Limitations:
• 8.3% missing on coping_strategy
• Cross-sectional — no causal inference

🔗 OSF Link: https://osf.io/abc12/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Tech Stack

| Layer | Tech |
|-------|------|
| AI Model | Gemini 2.5 Flash (Vertex AI) |
| Agent Framework | Google ADK — `LlmAgent` + `MCPToolset` + `Runner` |
| MCP Transport | stdio (`StdioServerParameters`) |
| External Data | OSF REST API v2 |
| CSV Analysis | pandas |
| HTTP Client | httpx |
| Web Framework | FastAPI + Uvicorn |
| Deployment | Google Cloud Run |

---

*Built by Rafi Fernanda Aldin · Gen AI Academy APAC Track 2*
