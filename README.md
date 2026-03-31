# 📊 StatScout — Academic Dataset Intelligence Agent

> *Turning Uncertainty Into Insight — one dataset at a time.*

StatScout is an AI-powered dataset intelligence agent built for the **Gen AI Academy APAC** competition (Track 2). It lets researchers query and explore public BigQuery datasets using natural language, powered by Google ADK and Gemini.

---

## ✨ What It Does

Ask StatScout questions in plain English and it responds with a structured statistical report, including key findings, interpretation, and caveats — all grounded in real query results from BigQuery.

**Example queries:**
- `"What is the average annual income by region?"`
- `"Show me the top 5 products by weekly revenue"`
- `"What is the gender distribution in the demographics table?"`
- `"Which hour of the day has the highest foot traffic?"`

**Example response:**
```
📊 StatScout Report — Average Annual Income by Region
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Source: BigQuery — my-project.statscout_data.demographics

📈 Key Findings:
• West: $72,400 avg (highest)
• Northeast: $68,100 avg
• Midwest: $61,300 avg
• South: $58,900 avg (lowest)

🔬 Statistical Interpretation:
Regional income disparity of ~$13,500 between highest and lowest.
Western regions show consistently higher earners across all education levels.

⚠️ Caveats:
• n = 5,000 participants
• Data reflects survey responses, not verified income records
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🏗️ Architecture

```
User (Browser)
     │
     ▼
FastAPI on Cloud Run
     │  POST /analyze
     ▼
ThreadPoolExecutor (isolates ADK's async from FastAPI's event loop)
     │
     ▼
asyncio.run() — fresh event loop per request
     │
     ▼
Google ADK — LlmAgent (gemini-2.5-flash-preview-04-17)
     │
     ▼
BigQueryToolset (google.adk.tools.bigquery)
     │  Direct Python SDK — no MCP, no HTTP intermediary
     ▼
BigQuery — statscout_data dataset
```

**Key design decision:** Uses ADK's native `BigQueryToolset` (direct Python SDK) instead of the `bigquery.googleapis.com/mcp` remote MCP endpoint. This avoids `anyio` cancel scope bugs, 403 permission complexity, and MCP session management issues on Cloud Run.

---

## 📁 Project Structure

```
statscout/
├── main.py                          # FastAPI app + thread-isolated ADK runner
├── Dockerfile
├── .dockerignore                      # Container build
├── requirements.txt                 # Python dependencies
├── templates/
│   └── index.html                   # Frontend UI
├── adk_agent/
├── __init__.py
│   └── mcp_statscout/
│       ├── __init__.py
│       ├── agent.py                 # LlmAgent with BigQueryToolset
│       └── tools.py
└── data/                            # CSV source files for BigQuery setup
    ├── demographics.csv
    ├── bakery_prices.csv
    ├── sales_history_weekly.csv
    └── foot_traffic.csv
```

---

## 🗃️ Dataset

The `statscout_data` BigQuery dataset contains four tables:

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `demographics` | Participant survey data | age, gender, education, annual_income, region |
| `bakery_prices` | Product pricing & competition | product, price, margin, competitor_price |
| `sales_history_weekly` | 52-week sales records | product, week, units_sold, revenue, promotion |
| `foot_traffic` | Hourly visitor analytics | hour, visitors, dwell_time_min, conversion_rate |

---

## 🚀 Setup & Deployment

### Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI installed and authenticated
- Python 3.11+

### 1. Clone and configure environment

```bash
git clone <your-repo>
cd statscout

# Create .env file
cat > .env << EOF
GOOGLE_CLOUD_PROJECT=<<YOUR-PROJECT-ID>>
BQ_DATASET=statscout_data
STATSCOUT_MODEL=gemini-2.5-flash
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_LOCATION=<<YOUR-LOCATION>>
EOF
```

### 2. Load BigQuery data

```bash
chmod +x setup/setup_bigquery.sh
./setup/setup_bigquery.sh
```

This script creates the `statscout_data` dataset and loads all four CSV files as BigQuery tables.

### 3. Create and configure the service account

```bash
PROJECT=<<YOUR-PROJECT-ID>>
SA=statscout-sa@${PROJECT}.iam.gserviceaccount.com

# Create SA
gcloud iam service-accounts create statscout-sa \
  --project=$PROJECT \
  --display-name="StatScout Service Account"

# Grant required BigQuery roles
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:$SA" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:$SA" \
  --role="roles/bigquery.jobUser"

# Grant Vertex AI access (for Gemini)
gcloud projects add-iam-policy-binding $PROJECT \
  --member="serviceAccount:$SA" \
  --role="roles/aiplatform.user"
```

### 4. Deploy to Cloud Run

```bash
gcloud run deploy statscout \
  --source . \
  --region us-central1 \
  --project my-project-31-491314 \
  --service-account statscout-sa@my-project-31-491314.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --timeout 300 \
  --memory 1Gi \
  --concurrency 1
```

### 5. Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Authenticate locally
gcloud auth application-default login

cd ~/statscout
python main.py
```

Open `http://localhost:8080` in your browser.

---

## 🔌 API Reference

### `POST /analyze`

Submit a natural language query to StatScout.

**Request:**
```json
{
  "query": "What is the average age in the demographics table?"
}
```

**Response:**
```json
{
  "query": "What is the average age in the demographics table?",
  "report": "📊 StatScout Report — Average Age\n..."
}
```

**Constraints:**
- Query must be non-empty
- Maximum 500 characters

### `GET /health`

Health check endpoint. Returns `{"status": "ok"}`.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | [Google ADK](https://google.github.io/adk-docs/) 1.28.0 |
| LLM | Gemini 2.5 Flash (Vertex AI) |
| BigQuery Integration | `google.adk.tools.bigquery.BigQueryToolset` |
| Web Framework | FastAPI 0.115 |
| Runtime | Cloud Run (Python 3.11) |
| Data Warehouse | Google BigQuery |

---

## ⚙️ Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | *(required)* |
| `BQ_DATASET` | BigQuery dataset name | `statscout_data` |
| `STATSCOUT_MODEL` | Gemini model to use | `gemini-2.5-flash-preview-04-17` |
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI instead of AI Studio | `true` |
| `GOOGLE_CLOUD_LOCATION` | GCP region | `us-central1` |

---

## 🔒 IAM Roles Required

| Role | Purpose |
|------|---------|
| `roles/bigquery.dataViewer` | Read table data |
| `roles/bigquery.jobUser` | Run query jobs |
| `roles/aiplatform.user` | Call Gemini via Vertex AI |

---
*"Turning Uncertainty Into Insight"*

Built for **Gen AI Academy APAC — Track 2**
