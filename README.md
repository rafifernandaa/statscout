# StatScout 📊

**Academic Dataset Intelligence Agent** — Gen AI Academy APAC Edition (Track 2)

> Turning Uncertainty Into Insight — one dataset at a time.

StatScout is an intelligent research assistant that discovers and analyzes academic datasets. Built with **Google ADK** and **Gemini 2.5 Flash**, it utilizes the **Model Context Protocol (MCP)** to perform live statistical analysis on data hosted in **Google BigQuery**.

---

## 🏗️ Project Structure

```text
statscout/
├── adk_agent/
├── __init__.py                 # empty                     
│   └── mcp_statscout/          # Core Agent Logic
│       ├── agent.py            # LlmAgent + StatScout Report prompt
│       ├── tools.py            # BigQuery MCP Toolset factory
│       └── __init__.py         # Package entry points
├── templates/
│   └── index.html              # Interactive Web UI
├── data/                       # Reference CSVs (demographics, sales, traffic)
├── main.py                     # FastAPI entry point with Runner logic
├── requirements.txt            # Project dependencies
├── Dockerfile                  # Cloud Run container configuration
└── .env                        # Environment variables
```

---

## 🧬 Architecture

```text
User → Web UI (index.html) → POST /analyze (FastAPI · Cloud Run)
         └→ main.py (Runner · async generator)
               └→ agent.py (LlmAgent · gemini-2.5-flash)
                     └→ tools.py (MCPToolset · Hosted BigQuery MCP)
                           └→ BigQuery API (SQL execution & results)
```

---

## 🛠️ MCP Tools & Dataset

The agent has real-time access to a BigQuery dataset containing these specific tables:

* **demographics**: Participant age, education, and income data
* **sales_history_weekly**: 52-week revenue and unit sales history
* **foot_traffic**: Hourly visitor counts and dwell time conversion rates
* **bakery_prices**: Competitive benchmarks and profit margins

---

## 🚀 Quick Start

### 1. Local Development

Ensure you have Python 3.11+ and the Google Cloud SDK installed.

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables
export GOOGLE_CLOUD_PROJECT="my-project-31-491314"
export BQ_DATASET="statscout_data"

# Run the application locally
python main.py
```

Access the dashboard at:

```
http://localhost:8080
```

---

### 2. Cloud Run Deployment

```bash
gcloud run deploy statscout \
  --source . \
  --region us-central1 \
  --service-account statscout-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --memory 1Gi \
  --timeout 120
```

---

## 📊 Example Output

```text
📊 StatScout Report — Average Annual Income
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Source: BigQuery — my-project.statscout_data.demographics

📈 Key Findings:
• The average annual income for participants is $63,104.00 USD.

🔬 Statistical Interpretation:
Provides a central tendency measure for income across all recorded individuals.

⚠️ Caveats:
• Single query result; does not reflect standard deviation or regional variance.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🛠️ Tech Stack

| Layer           | Technology                    |
| --------------- | ----------------------------- |
| Model           | Gemini 2.5 Flash (Vertex AI)  |
| Agent Framework | Google ADK (LlmAgent, Runner) |
| Tool Protocol   | Model Context Protocol (MCP)  |
| Data Warehouse  | Google BigQuery               |
| Backend         | FastAPI + Jinja2 Templates    |
| Infrastructure  | Google Cloud Run (Docker)     |
