"""
StatScout MCP Server — tools.py
Custom MCP server exposing 3 tools for OSF dataset discovery and analysis.
Transport: stdio (runs as subprocess from the ADK agent via MCPToolset)
"""

import asyncio
import io
import json
import sys

import httpx
import pandas as pd
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

MAX_FILE_SIZE_MB = 5
OSF_API_BASE = "https://api.osf.io/v2"

app = Server("statscout-mcp")


# ─────────────────────────────────────────────
# Tool definitions
# ─────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_osf_projects",
            description=(
                "Search OSF (Open Science Framework) for public research projects/datasets "
                "matching a query. Returns project id, title, and description."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term, e.g. 'anxiety coping', 'reading comprehension children'",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of results to return (default 5, max 10)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_dataset_files",
            description=(
                "List downloadable files inside an OSF project. "
                "Filters to CSV files only and returns name + download URL."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "OSF project GUID, e.g. 'abc12'",
                    }
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="fetch_csv_preview",
            description=(
                "Download a CSV file from OSF and return its shape, column names, dtypes, "
                "and descriptive statistics (mean, std, min, max, quartiles). "
                "Skips files larger than 5 MB."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_url": {
                        "type": "string",
                        "description": "Direct download URL for the CSV file",
                    },
                    "rows": {
                        "type": "integer",
                        "description": "Number of preview rows to include (default 20)",
                        "default": 20,
                    },
                },
                "required": ["file_url"],
            },
        ),
    ]


# ─────────────────────────────────────────────
# Tool dispatcher
# ─────────────────────────────────────────────

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_osf_projects":
        result = await _search_osf_projects(
            query=arguments["query"],
            limit=min(int(arguments.get("limit", 5)), 10),
        )
    elif name == "get_dataset_files":
        result = await _get_dataset_files(project_id=arguments["project_id"])
    elif name == "fetch_csv_preview":
        result = await _fetch_csv_preview(
            file_url=arguments["file_url"],
            rows=int(arguments.get("rows", 20)),
        )
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ─────────────────────────────────────────────
# Tool implementations
# ─────────────────────────────────────────────

async def _search_osf_projects(query: str, limit: int) -> dict:
    """Search OSF nodes (projects) by title keyword, with fallback to search API."""
    url = f"{OSF_API_BASE}/nodes/"
    params = {
        "filter[public]": "true",
        "filter[title]": query,
        "page[size]": limit,
        "fields[nodes]": "id,title,description,tags,date_modified",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"OSF API error: {e.response.status_code}"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {str(e)}"}

    projects = []
    for node in data.get("data", []):
        attrs = node.get("attributes", {})
        projects.append({
            "id": node.get("id"),
            "title": attrs.get("title", ""),
            "description": (attrs.get("description") or "")[:300],
            "tags": attrs.get("tags", []),
            "date_modified": attrs.get("date_modified", ""),
            "osf_url": f"https://osf.io/{node.get('id')}/",
        })

    # Fallback: broader OSF search API if title filter returned nothing
    if not projects:
        search_url = f"{OSF_API_BASE}/search/projects/"
        params2 = {"q": query, "page[size]": limit}
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp2 = await client.get(search_url, params=params2)
                resp2.raise_for_status()
                data2 = resp2.json()
                for node in data2.get("data", []):
                    attrs = node.get("attributes", {})
                    projects.append({
                        "id": node.get("id"),
                        "title": attrs.get("title", ""),
                        "description": (attrs.get("description") or "")[:300],
                        "tags": attrs.get("tags", []),
                        "date_modified": attrs.get("date_modified", ""),
                        "osf_url": f"https://osf.io/{node.get('id')}/",
                    })
            except Exception:
                pass

    return {
        "query": query,
        "count": len(projects),
        "results": projects,
    }


async def _get_dataset_files(project_id: str) -> dict:
    """List CSV files available in an OSF project's OSF Storage."""
    url = f"{OSF_API_BASE}/nodes/{project_id}/files/osfstorage/"
    params = {"page[size]": 50}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"OSF API error: {e.response.status_code} for project '{project_id}'"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {str(e)}"}

    all_files = []
    csv_files = []

    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        kind = attrs.get("kind", "")
        name = attrs.get("name", "")
        size_bytes = attrs.get("size") or 0

        file_info = {
            "name": name,
            "kind": kind,
            "size_mb": round(size_bytes / (1024 * 1024), 2) if size_bytes else None,
            "download_url": item.get("links", {}).get("download"),
        }
        all_files.append(file_info)

        if kind == "file" and name.lower().endswith(".csv"):
            csv_files.append(file_info)

    return {
        "project_id": project_id,
        "osf_url": f"https://osf.io/{project_id}/",
        "total_files": len(all_files),
        "csv_files": csv_files,
        "all_file_names": [f["name"] for f in all_files],
    }


async def _fetch_csv_preview(file_url: str, rows: int) -> dict:
    """Download CSV (≤5 MB), compute descriptive stats, return structured preview."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            head = await client.head(file_url)
            content_length = int(head.headers.get("content-length", 0))
            size_mb = content_length / (1024 * 1024)

            if size_mb > MAX_FILE_SIZE_MB:
                return {
                    "error": (
                        f"File too large ({size_mb:.1f} MB). "
                        f"StatScout skips files over {MAX_FILE_SIZE_MB} MB to avoid timeouts."
                    )
                }

            resp = await client.get(file_url)
            resp.raise_for_status()
            raw_bytes = resp.content

        except httpx.HTTPStatusError as e:
            return {"error": f"Download error: {e.response.status_code}"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {str(e)}"}

    try:
        df = pd.read_csv(io.BytesIO(raw_bytes), low_memory=False)
    except Exception as e:
        return {"error": f"Failed to parse CSV: {str(e)}"}

    n_rows, n_cols = df.shape

    columns_info = []
    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        columns_info.append({
            "name": col,
            "dtype": str(df[col].dtype),
            "null_count": null_count,
            "null_pct": round(null_count / n_rows * 100, 1) if n_rows > 0 else 0,
        })

    numeric_df = df.select_dtypes(include="number")
    describe_dict = {}
    if not numeric_df.empty:
        describe_dict = numeric_df.describe().round(4).to_dict()

    cat_df = df.select_dtypes(include=["object", "category"])
    categorical_summary = {}
    for col in cat_df.columns[:5]:
        vc = df[col].value_counts().head(5).to_dict()
        categorical_summary[col] = {str(k): int(v) for k, v in vc.items()}

    cleaned_head = []
    for record in df.head(rows).to_dict(orient="records"):
        cleaned = {}
        for k, v in record.items():
            if isinstance(v, str) and len(v) > 80:
                cleaned[k] = v[:80] + "..."
            elif pd.isna(v) if not isinstance(v, (list, dict)) else False:
                cleaned[k] = None
            else:
                cleaned[k] = v
        cleaned_head.append(cleaned)

    return {
        "shape": {"rows": n_rows, "columns": n_cols},
        "columns": columns_info,
        "numeric_stats": describe_dict,
        "categorical_summary": categorical_summary,
        "head_preview": cleaned_head,
        "file_url": file_url,
    }


# ─────────────────────────────────────────────
# Entry point (called by MCPToolset via stdio)
# ─────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
