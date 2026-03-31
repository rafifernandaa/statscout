"""
main.py — StatScout FastAPI (Cloud Run)

Uses ADK's native BigQueryToolset — no MCPToolset, no cancel scope issues.
ADK Runner still runs in a dedicated thread (asyncio.run) to keep it
isolated from FastAPI's event loop, which is best practice regardless.
"""

import asyncio
import concurrent.futures
import os
import uuid

import dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

dotenv.load_dotenv()

APP_NAME = "statscout"
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

app = FastAPI(title="StatScout", description="Academic Dataset Intelligence Agent", version="4.0.0")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def root_html(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}


class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    query: str
    report: str


def _run_adk_in_thread(user_query: str) -> str:
    return asyncio.run(_adk_query(user_query))


async def _adk_query(user_query: str) -> str:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from adk_agent.mcp_statscout.agent import build_agent

    agent = build_agent()
    session_service = InMemorySessionService()
    session_id = str(uuid.uuid4())

    await session_service.create_session(
        app_name=APP_NAME,
        user_id="statscout-user",
        session_id=session_id,
    )

    runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)
    message = types.Content(role="user", parts=[types.Part(text=user_query)])
    final_response = ""

    async for event in runner.run_async(
        user_id="statscout-user",
        session_id=session_id,
        new_message=message,
    ):
        if event.is_final_response() and event.content:
            parts = getattr(event.content, "parts", [])
            final_response = "".join(p.text for p in parts if hasattr(p, "text") and p.text)
            if final_response:
                break

    return final_response


@app.post("/analyze", response_model=QueryResponse)
async def analyze(request: QueryRequest):
    query = (request.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    if len(query) > 500:
        raise HTTPException(status_code=400, detail="Query too long (max 500 chars).")

    loop = asyncio.get_event_loop()
    try:
        report = await loop.run_in_executor(_executor, _run_adk_in_thread, query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    if not report:
        raise HTTPException(status_code=500, detail="Agent returned an empty response.")

    return QueryResponse(query=query, report=report)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
