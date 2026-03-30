# StatScout 📊

**Academic Dataset Intelligence Agent** — Gen AI Academy APAC Track 2 Submission

> *Turning Uncertainty Into Insight — one dataset at a time.*

StatScout is an AI agent that discovers and analyzes public research datasets from [OSF (Open Science Framework)](https://osf.io). Built with Google ADK, Gemini 2.5 Flash, and a custom Python MCP server.

---

## Architecture

```
User → FastAPI (Cloud Run)
         └→ StatScout Agent (gemini-2.5-flash)
               └→ MCPToolset (stdio transport)
                     └→ statscout_server.py (custom MCP server)
                           ├→ OSF REST API v2        [search_osf_projects]
                           ├→ OSF File Storage API   [get_dataset_files]
                           └→ OSF CSV Downloads      [fetch_csv_preview]
                                  └→ pandas (descriptive stats)
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `search_osf_projects` | Search OSF by keyword, returns matching project IDs + titles |
| `get_dataset_files` | List CSV files in a given OSF project |
| `fetch_csv_preview` | Download CSV (≤5 MB), compute descriptive stats via pandas |

---

## Local Setup

### 1. Clone and create virtual environment

```bash
git clone <your-repo-url>
cd statscout

python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set environment variables

```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

### 4. Authenticate with Google Cloud

```bash
gcloud auth application-default login
```

### 5. Run locally

```bash
python main.py
```

Server starts at `http://localhost:8080`

### 6. Test

```bash
# Health check
curl http://localhost:8080/health

# Analyze a dataset
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "anxiety coping mechanisms"}'
```

---

## Cloud Run Deployment

### 1. Set variables

```bash
PROJECT_ID="your-gcp-project-id"
REGION="us-central1"
SERVICE_NAME="statscout"
```

### 2. Enable required APIs

```bash
gcloud services enable run.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  --project=$PROJECT_ID
```

### 3. Create a service account

```bash
gcloud iam service-accounts create statscout-sa \
  --display-name="StatScout Service Account" \
  --project=$PROJECT_ID

# Grant Vertex AI access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:statscout-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### 4. Build and deploy

```bash
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --service-account statscout-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 120 \
  --project $PROJECT_ID
```

> **Note:** `--memory 1Gi` is recommended because pandas loads CSVs in-memory. `--timeout 120` accommodates OSF network latency.

### 5. Test deployment

```bash
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region $REGION --format 'value(status.url)')

curl -X POST $SERVICE_URL/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "reading comprehension children"}'
```

---

## Example Output

```
📊 StatScout Report — Anxiety & Coping Mechanisms Study (OSF: abc12)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Variables: 14 | Observations: 623 | Format: CSV

🔑 Key Variables:
• age (int) — participant age
• GAD7_total (float) — Generalized Anxiety Disorder 7-item scale score
• coping_strategy (str) — self-reported primary coping approach
• stress_level (float) — perceived stress score

📈 Summary Statistics:
• GAD7_total: mean = 8.4, SD = 3.1, range = 0–21
  → Average score falls in the mild anxiety range (≥5 threshold)
• stress_level: mean = 18.7, SD = 4.9, range = 4–40
  → Moderate stress levels; high variance suggests heterogeneous sample

🔬 Potential Research Uses:
1. IRT calibration of GAD7 items to evaluate differential item functioning
2. Regression/moderation analysis: does coping strategy moderate stress→anxiety?
3. Latent profile analysis to identify anxiety–coping subgroups

⚠️ Limitations:
• 8.3% missing data on coping_strategy — may bias group comparisons
• Cross-sectional design limits causal inference
• Sample skews younger (mean age 23); generalizability to older adults is limited

🔗 OSF Link: https://osf.io/abc12/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Project Structure

```
statscout/
├── main.py                          # FastAPI entry point
├── statscout/
│   ├── __init__.py
│   ├── agent.py                     # ADK agent + manual agentic loop
│   └── mcp_server/
│       ├── __init__.py
│       └── statscout_server.py      # Custom Python MCP server (3 tools)
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Model | Gemini 2.5 Flash (Vertex AI) |
| Agent Framework | Google ADK + google-genai |
| MCP Server | Python `mcp` SDK (stdio transport) |
| External Data | OSF REST API v2 |
| Data Processing | pandas |
| HTTP Client | httpx |
| Web Framework | FastAPI + Uvicorn |
| Deployment | Google Cloud Run |

---

## Track 2 Compliance Checklist

- [x] AI agent built with ADK
- [x] Uses MCP to connect to an external tool/data source (OSF REST API)
- [x] Retrieves structured data (CSV stats via pandas)
- [x] Uses retrieved data to generate a final response (StatScout Report)
- [x] Deployed on Cloud Run
- [x] GitHub repo included in submission

---

*Built by Rafi Fernanda Aldin — Gen AI Academy APAC Track 2*
