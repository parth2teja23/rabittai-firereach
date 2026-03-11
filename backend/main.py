"""
FireReach – FastAPI Application Entry Point
============================================
Exposes a single primary endpoint:

  POST /api/outreach   →  Runs the full agentic loop (signal → research → send)

Additional utility endpoints:
  GET  /api/health     →  Health check
  GET  /api/config     →  Returns non-secret configuration info

The agent runs in a thread pool (via `run_in_executor`) so the async event
loop is never blocked by synchronous LangChain/LLM calls.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from functools import partial

# PostgreSQL installer sets REQUESTS_CA_BUNDLE / SSL_CERT_FILE to its own
# CA bundle path, which breaks the requests / httpx / Tavily TLS chain.
# Force-reset to certifi's bundle so all outbound HTTPS works correctly.
import certifi
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
os.environ["SSL_CERT_FILE"] = certifi.where()

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from agent import run_outreach_agent
from config import get_settings
from models import OutreachRequest, OutreachResponse

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("firereach")


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown hooks)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    logger.info("FireReach starting up")
    logger.info("   LLM provider : %s", cfg.llm_provider)
    logger.info("   Tavily key   : %s", "set" if cfg.tavily_api_key else "MISSING")
    logger.info("   SMTP user    : %s", cfg.smtp_user or "not configured")
    yield
    logger.info("FireReach shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

cfg = get_settings()

app = FastAPI(
    title="FireReach – Autonomous Outreach Engine",
    description=(
        "An agentic API that harvests live buyer signals, generates "
        "personalised account briefs, and automatically dispatches "
        "hyper-relevant outreach emails."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["Utility"])
async def health():
    """Simple liveness probe."""
    return {"status": "ok", "service": "firereach-backend"}


@app.get("/api/config", tags=["Utility"])
async def config_info():
    """Return non-sensitive runtime configuration."""
    return {
        "llm_provider": cfg.llm_provider,
        "gemini_model": cfg.gemini_model,
        "groq_model": cfg.groq_model,
        "tavily_configured": bool(cfg.tavily_api_key),
        "smtp_configured": bool(cfg.smtp_user and cfg.smtp_password),
    }


@app.post(
    "/api/outreach",
    response_model=OutreachResponse,
    status_code=status.HTTP_200_OK,
    tags=["Outreach"],
    summary="Run the full autonomous outreach pipeline",
    description=(
        "Accepts an ICP, a target company, and a recipient email. "
        "Runs the three-tool agentic loop:\n\n"
        "1. **tool_signal_harvester** – collect live intent signals via Tavily\n"
        "2. **tool_research_analyst** – generate a signal-grounded account brief\n"
        "3. **tool_outreach_automated_sender** – write & dispatch personalised email\n\n"
        "Returns every reasoning step so the frontend can render the agent log."
    ),
)
async def run_outreach(request: OutreachRequest) -> OutreachResponse:
    """
    Execute the FireReach agentic pipeline.

    The heavy LLM work runs in a thread pool so the async event loop stays free.
    """
    logger.info(
        "POST /api/outreach  company='%s'  to='%s'",
        request.company,
        request.to_email,
    )

    loop = asyncio.get_running_loop()
    try:
        response: OutreachResponse = await loop.run_in_executor(
            None,
            partial(run_outreach_agent, request),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled error in outreach pipeline")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent pipeline error: {exc}",
        ) from exc

    return response


# ---------------------------------------------------------------------------
# Dev entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
