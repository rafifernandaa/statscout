"""
StatScout Agent — agent.py
ADK-native MCPToolset (stdio → tools.py) wired into
LlmAgent + Runner + InMemorySessionService.
Exposed via FastAPI in main.py at the project root.
"""

import asyncio
import sys
import uuid
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.genai import types
from mcp import StdioServerParameters

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

MODEL = "gemini-2.5-flash-preview-04-17"
APP_NAME = "statscout"

# tools.py lives alongside agent.py in mcp_bakery_app/
TOOLS_PATH = Path(__file__).parent / "tools.py"

SYSTEM_PROMPT = """You are StatScout, an academic dataset intelligence agent.
Your job is to help researchers discover and understand datasets from OSF (Open Science Framework).

When a user asks you to find or analyze a dataset, follow these steps:
1. Use search_osf_projects to find relevant projects.
2. Pick the most relevant project and use get_dataset_files to list its CSV files.
3. Use fetch_csv_preview on the most suitable CSV file (prefer smaller files if multiple exist).
4. Generate a structured StatScout Report using the data returned.

Your report must follow this exact format:

📊 StatScout Report — {Dataset Title} (OSF: {project_id})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Variables: {n_cols} | Observations: {n_rows} | Format: CSV

🔑 Key Variables:
{list the most interesting columns with their types}

📈 Summary Statistics:
{for each numeric variable: mean, SD, min, max — interpreted in plain language}

🔬 Potential Research Uses:
{2-3 concrete research questions or analysis approaches this dataset supports}

⚠️ Limitations:
{missing data, sample size concerns, measurement notes}

🔗 OSF Link: https://osf.io/{project_id}/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rules:
- If a file is too large or not a CSV, note it and try another file.
- If no datasets are found, suggest refining the search query.
- Always be concise, statistician-friendly, and grounded only in the actual data the tools return.
- Never fabricate variable names or statistics.
"""


# ─────────────────────────────────────────────
# Agent factory
# ─────────────────────────────────────────────

def build_agent() -> tuple[LlmAgent, MCPToolset]:
    """
    Spin up MCPToolset pointing at tools.py (stdio transport),
    wire it into an LlmAgent, and return both so the caller
    can call toolset.close() after the request completes.
    """
    toolset = MCPToolset(
        connection_params=StdioServerParameters(
            command=sys.executable,
            args=[str(TOOLS_PATH)],
        ),
    )

    agent = LlmAgent(
        name="statscout_agent",
        model=MODEL,
        instruction=SYSTEM_PROMPT,
        tools=[toolset],
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,
        ),
    )

    return agent, toolset


# ─────────────────────────────────────────────
# Async runner (one fresh session per request)
# ─────────────────────────────────────────────

async def run_statscout(user_query: str) -> str:
    """
    Execute the StatScout agent for a single user query.
    Stateless — creates a new session per call, safe for Cloud Run.
    """
    agent, toolset = build_agent()
    session_service = InMemorySessionService()

    user_id = "statscout-user"
    session_id = str(uuid.uuid4())

    # Session must exist before Runner.run_async (avoids SessionNotFoundError)
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        session_service=session_service,
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=user_query)],
    )

    final_response = ""

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = "".join(
                        part.text
                        for part in event.content.parts
                        if hasattr(part, "text") and part.text
                    )
                break
    finally:
        await toolset.close()

    return final_response or "StatScout could not generate a report. Please try a more specific query."


# ─────────────────────────────────────────────
# Sync wrapper for FastAPI
# ─────────────────────────────────────────────

def run_agent(user_query: str) -> str:
    """Synchronous entry point called from main.py FastAPI handler."""
    return asyncio.run(run_statscout(user_query))
