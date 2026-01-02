"""
Kairos Agent - Cloud Run FastAPI Service
=========================================
Stateless REST API for productivity reasoning powered by Vertex AI.

Deployed to Google Cloud Run for scalability and cost-efficiency.

Endpoints:
- /health  - Service health & Vertex AI status
- /analyze - Main reasoning endpoint
- /status  - Detailed service status for debugging

Author: Kairos Team - AgentX Hackathon 2026
"""

import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from models import (
    AnalyzeRequest,
    AgentDecision,
    HealthResponse,
    ErrorResponse,
    IntentType,
    ActionType
)
from agent import get_agent, ReasoningAgent
from vertex_client import VertexClient


# ============================================================
# Configuration from Environment
# ============================================================

# CLOUD_MODE: When false, uses deterministic simulated responses
CLOUD_MODE = os.getenv("CLOUD_MODE", "true").lower() == "true"
PROJECT_ID = os.getenv("PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("LOCATION") or os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("kairos-cloud")


# ============================================================
# Application Lifecycle
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle handler.
    - Startup: Initialize Vertex AI client
    - Shutdown: Clean up resources
    """
    # Startup
    logger.info("="*60)
    logger.info("🚀 Kairos Cloud Service Starting")
    logger.info("="*60)
    
    # Initialize the agent (creates Vertex AI client)
    agent = get_agent()
    
    # Log configuration clearly for judges/debugging
    logger.info(f"☁️  CLOUD RUN SERVICE INITIALIZED")
    logger.info(f"    Project ID: {PROJECT_ID or 'not-set'}")
    logger.info(f"    Location: {LOCATION}")
    logger.info(f"    Cloud Mode: {CLOUD_MODE}")
    logger.info(f"    Vertex AI Available: {agent.vertex_client.is_available()}")
    
    if CLOUD_MODE and agent.vertex_client.is_available():
        logger.info(f"🧠 VERTEX AI (Gemini) CONNECTED")
    elif not CLOUD_MODE:
        logger.info(f"🔧 Running in LOCAL/DEMO mode (deterministic responses)")
    else:
        logger.warning(f"⚠️  Vertex AI unavailable - using fallback responses")
    
    logger.info("="*60)
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Kairos Cloud Service shutting down")


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="Kairos Agent Cloud Service",
    description="""
    🕐 **Kairos Agent** - Autonomous Productivity AI
    
    This service receives activity summaries from local agents and uses
    Google Vertex AI (Gemini) to make intelligent decisions about when
    to nudge users back to their productivity goals.
    
    ## Features
    - 🧠 Gemini-powered reasoning
    - 🔒 Privacy-first (summaries only, no raw data)
    - ⚡ Fast, stateless processing
    - 🎯 Goal-aware nudging
    
    ## Endpoints
    - `POST /analyze` - Analyze activity and get decision
    - `GET /health` - Service health check
    - `GET /stats` - Agent statistics
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Exception Handlers
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if os.getenv("DEBUG") else None
        ).model_dump()
    )


# ============================================================
# API Endpoints
# ============================================================

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "service": "Kairos Agent Cloud Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint.
    
    Returns service status and Vertex AI availability.
    Used by Cloud Run for health monitoring.
    """
    agent = get_agent()
    
    return HealthResponse(
        status="healthy",
        service="kairos-cloud-agent",
        version="1.0.0",
        vertex_ai_available=agent.vertex_client.is_available(),
        timestamp=datetime.now().isoformat()
    )


class ServiceStatus(BaseModel):
    """Detailed service status for debugging."""
    service: str
    version: str
    cloud_mode: bool
    project_id: Optional[str]
    location: str
    vertex_ai_available: bool
    vertex_ai_model: str
    total_requests: int
    total_nudges: int
    nudge_rate: float
    uptime_seconds: float
    timestamp: str


# Track service start time for uptime
_service_start_time = datetime.now()


@app.get("/status", response_model=ServiceStatus, tags=["System"])
async def service_status():
    """
    Detailed service status endpoint.
    
    Returns comprehensive status including:
    - Cloud configuration
    - Vertex AI status
    - Request/nudge statistics
    - Service uptime
    
    Useful for debugging and demo verification.
    """
    agent = get_agent()
    stats = agent.get_stats()
    uptime = (datetime.now() - _service_start_time).total_seconds()
    
    logger.info(f"📊 Status requested | Requests: {stats['total_requests']} | Nudges: {stats['total_nudges']}")
    
    return ServiceStatus(
        service="kairos-cloud-agent",
        version="1.0.0",
        cloud_mode=CLOUD_MODE,
        project_id=PROJECT_ID,
        location=LOCATION,
        vertex_ai_available=stats["vertex_available"],
        vertex_ai_model="gemini-1.5-flash-002",
        total_requests=stats["total_requests"],
        total_nudges=stats["total_nudges"],
        nudge_rate=stats["nudge_rate"],
        uptime_seconds=uptime,
        timestamp=datetime.now().isoformat()
    )


@app.get("/stats", tags=["System"])
async def get_stats():
    """
    Get agent statistics.
    
    Returns request counts, nudge rates, and other metrics.
    """
    agent = get_agent()
    return agent.get_stats()


@app.post("/analyze", response_model=AgentDecision, tags=["Analysis"])
async def analyze_activity(request: AnalyzeRequest):
    """
    🧠 **Analyze Activity and Decide Action**
    
    Main endpoint for activity analysis. Receives a summary of user activity
    from the local agent and returns a decision about whether to nudge.
    
    **Privacy Note**: Only aggregated summaries are processed, never raw data.
    
    **Request Body**:
    - `activity_summary`: Aggregated activity data (apps, durations)
    - `user_goals`: What the user is trying to accomplish
    - `local_classification`: Optional local classifier result
    - `context`: Optional additional context
    
    **Response**:
    - `intent`: productive, neutral, or unproductive
    - `confidence`: How confident the agent is (0-1)
    - `reasoning`: Human-readable explanation
    - `action`: none or nudge
    - `nudge_message`: Message for user (only if action is nudge)
    """
    logger.info(f"🔍 ANALYZE REQUEST | Apps: {list(request.activity_summary.app_breakdown.keys())}")
    logger.info(f"    User Goals: {request.user_goals}")
    logger.info(f"    Cloud Mode: {CLOUD_MODE}")
    
    try:
        agent = get_agent()
        decision = await agent.analyze(request)
        
        # Clear logging for demo/judge visibility
        logger.info(f"🧠 VERTEX AI DECISION:")
        logger.info(f"    Intent: {decision.intent.value}")
        logger.info(f"    Confidence: {decision.confidence:.0%}")
        logger.info(f"    Action: {decision.action.value}")
        logger.info(f"    Reasoning: {decision.reasoning[:100]}...")
        
        return decision
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}", exc_info=True)
        
        # Return a safe fallback instead of erroring
        return AgentDecision(
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            reasoning=f"Analysis error: {str(e)}. Using safe default.",
            action=ActionType.NONE,
            nudge_message=None
        )


@app.post("/analyze/batch", tags=["Analysis"])
async def analyze_batch(requests: list[AnalyzeRequest]):
    """
    Analyze multiple activity summaries in batch.
    
    Useful for processing historical data or multiple users.
    Limited to 10 requests per batch.
    """
    if len(requests) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 requests per batch"
        )
    
    agent = get_agent()
    results = []
    
    for req in requests:
        try:
            decision = await agent.analyze(req)
            results.append(decision.model_dump())
        except Exception as e:
            results.append({
                "error": str(e),
                "request_summary": req.activity_summary.period_start
            })
    
    return {"results": results, "processed": len(results)}


# ============================================================
# Local Development Server
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8080))
    
    logger.info(f"Starting development server on port {port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
