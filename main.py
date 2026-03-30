"""
StatScout — FastAPI entry point (main.py)
Thin HTTP layer at the project root. Delegates all logic to agent.py.
"""

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from adk_agent.mcp_bakery_app.agent import run_agent

app = FastAPI(
    title="StatScout",
    description="Academic Dataset Intelligence Agent powered by Gemini 2.5 Flash + MCP",
    version="1.0.0",
)


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    query: str
    report: str


@app.get("/")
async def root():
    return {
        "agent": "StatScout",
        "tagline": "Turning Uncertainty Into Insight — one dataset at a time.",
        "usage": "POST /analyze with JSON body: {\"query\": \"your dataset topic\"}",
        "health": "ok",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=QueryResponse)
async def analyze(request: QueryRequest):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    query = request.query.strip()
    if len(query) > 500:
        raise HTTPException(status_code=400, detail="Query too long (max 500 characters).")

    try:
        report = run_agent(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    return QueryResponse(query=query, report=report)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
