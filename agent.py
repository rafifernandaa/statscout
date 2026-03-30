"""
StatScout Agent
Uses google.genai direct client with a manual agentic loop.
MCP tools are declared as FunctionDeclarations matching the MCP server's schema,
and tool calls are dispatched to the MCP server subprocess via mcp SDK client.
"""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

MODEL = "gemini-2.5-flash-preview-04-17"
MCP_SERVER_PATH = Path(__file__).parent / "mcp_server" / "statscout_server.py"

SYSTEM_PROMPT = """You are StatScout, an academic dataset intelligence agent.
Your job is to help researchers discover and understand datasets from OSF (Open Science Framework).

When a user asks you to find or analyze a dataset, follow these steps:
1. Use search_osf_projects to find relevant projects.
2. Pick the most relevant project and use get_dataset_files to list its CSV files.
3. Use fetch_csv_preview on the most suitable CSV file (prefer smaller files if multiple exist).
4. Generate a structured StatScout Report using the data.

Your report must follow this format exactly:

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

If a file is too large or not a CSV, note it gracefully and try another file.
If no datasets are found, suggest refining the search query.
Always be concise, statistician-friendly, and grounded only in the actual data returned by the tools.
"""

# ─────────────────────────────────────────────
# Tool declarations (mirrors MCP server schema)
# ─────────────────────────────────────────────

TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="search_osf_projects",
                description=(
                    "Search OSF (Open Science Framework) for public research projects/datasets "
                    "matching a query. Returns project id, title, and description."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING,
                            description="Search term, e.g. 'anxiety coping', 'reading comprehension children'",
                        ),
                        "limit": types.Schema(
                            type=types.Type.INTEGER,
                            description="Max number of results to return (default 5, max 10)",
                        ),
                    },
                    required=["query"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_dataset_files",
                description=(
                    "List downloadable CSV files inside an OSF project. "
                    "Returns file names, sizes, and download URLs."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "project_id": types.Schema(
                            type=types.Type.STRING,
                            description="OSF project GUID, e.g. 'abc12'",
                        ),
                    },
                    required=["project_id"],
                ),
            ),
            types.FunctionDeclaration(
                name="fetch_csv_preview",
                description=(
                    "Download a CSV file from OSF and return its shape, column names, dtypes, "
                    "and descriptive statistics (mean, std, min, max, quartiles). "
                    "Skips files larger than 5 MB."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "file_url": types.Schema(
                            type=types.Type.STRING,
                            description="Direct download URL for the CSV file",
                        ),
                        "rows": types.Schema(
                            type=types.Type.INTEGER,
                            description="Number of preview rows to include (default 20)",
                        ),
                    },
                    required=["file_url"],
                ),
            ),
        ]
    )
]


# ─────────────────────────────────────────────
# MCP dispatcher
# ─────────────────────────────────────────────

@asynccontextmanager
async def get_mcp_session():
    """Spin up the MCP server subprocess and yield a connected ClientSession."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(MCP_SERVER_PATH)],
        env=None,
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def dispatch_tool(tool_name: str, tool_args: dict) -> str:
    """Call a tool on the MCP server and return the result as a JSON string."""
    async with get_mcp_session() as session:
        result = await session.call_tool(tool_name, tool_args)
        # result.content is a list of TextContent
        texts = [block.text for block in result.content if hasattr(block, "text")]
        return "\n".join(texts)


# ─────────────────────────────────────────────
# Main agentic loop
# ─────────────────────────────────────────────

async def run_statscout(user_query: str) -> str:
    """
    Run the StatScout agent for a given user query.
    Uses a manual agentic loop: send message → check for tool calls →
    dispatch to MCP → feed result back → repeat until final text response.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
    )

    messages: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part(text=user_query)],
        )
    ]

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=TOOLS,
        temperature=0.2,
    )

    MAX_ITERATIONS = 10  # safety cap on the agentic loop

    for iteration in range(MAX_ITERATIONS):
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=messages,
            config=config,
        )

        candidate = response.candidates[0]
        content = candidate.content

        # Collect all parts from the response
        tool_calls = []
        text_parts = []

        for part in content.parts:
            if part.function_call:
                tool_calls.append(part.function_call)
            elif part.text:
                text_parts.append(part.text)

        # If no tool calls — we have the final answer
        if not tool_calls:
            return "\n".join(text_parts) if text_parts else "No response generated."

        # Append assistant's message (with tool calls) to history
        messages.append(content)

        # Execute each tool call and collect results
        tool_results = []
        for fc in tool_calls:
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}

            try:
                result_text = await dispatch_tool(tool_name, tool_args)
            except Exception as e:
                result_text = json.dumps({"error": f"Tool dispatch failed: {str(e)}"})

            tool_results.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=tool_name,
                        response={"result": result_text},
                    )
                )
            )

        # Append tool results as a user-role message (Gemini convention)
        messages.append(
            types.Content(role="user", parts=tool_results)
        )

    return "StatScout reached the maximum number of iterations without a final response. Please try a more specific query."


# ─────────────────────────────────────────────
# Sync wrapper for FastAPI
# ─────────────────────────────────────────────

def run_agent(user_query: str) -> str:
    """Synchronous wrapper — called from FastAPI endpoint."""
    return asyncio.run(run_statscout(user_query))
