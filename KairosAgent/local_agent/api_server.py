"""
Kairos Agent - Local API Server
================================
Exposes the local agent state to the UI via a read-only REST API.

This API is STRICTLY READ-ONLY. The UI cannot control the agent.
The UI only explains what the agent is doing and why.

Endpoints:
- GET /state     - Current agent state (intent, confidence, focus)
- GET /decision  - Last decision made by the agent
- GET /timeline  - Chronological reasoning history
- GET /health    - Local agent health check

Author: Kairos Team - AgentX Hackathon 2026
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from threading import Lock
import json

logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """
    Current state of the autonomous agent.
    This is what the UI displays to build user trust.
    """
    # Current inferred intent
    intent: str = "unknown"  # productive, neutral, unproductive, unknown
    confidence: float = 0.0
    
    # Current focus context (what the agent thinks you're doing)
    focus_context: str = "Initializing..."
    
    # Agent status
    status: str = "initializing"  # initializing, observing, analyzing, idle
    
    # Is the agent actively watching?
    is_active: bool = False
    
    # Last update timestamp
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass 
class AgentDecisionRecord:
    """
    Record of a single agent decision.
    Stored in timeline for transparency.
    """
    timestamp: str
    intent: str
    confidence: float
    reasoning: str  # Human-readable explanation
    action: str  # none or nudge
    nudge_message: Optional[str] = None
    
    # Context at time of decision
    focus_context: str = ""
    apps_observed: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


class AgentStateManager:
    """
    Manages agent state for UI consumption.
    
    Design Philosophy:
    - The UI READS state, it never WRITES
    - State updates come ONLY from the agent loop
    - All data is designed to build trust, not surveillance
    """
    
    MAX_TIMELINE_ENTRIES = 50  # Keep last 50 decisions
    
    def __init__(self):
        self._lock = Lock()
        self._state = AgentState()
        self._last_decision: Optional[AgentDecisionRecord] = None
        self._timeline: List[AgentDecisionRecord] = []
        self._loop_count = 0
        
    def update_state(self, 
                     intent: str,
                     confidence: float,
                     focus_context: str,
                     status: str = "observing"):
        """
        Update current agent state.
        Called by the agent loop, NOT by UI.
        """
        with self._lock:
            self._state = AgentState(
                intent=intent,
                confidence=confidence,
                focus_context=focus_context,
                status=status,
                is_active=True,
                last_updated=datetime.now().isoformat()
            )
            logger.debug(f"State updated: {intent} ({confidence:.0%})")
    
    def record_decision(self,
                        intent: str,
                        confidence: float,
                        reasoning: str,
                        action: str,
                        nudge_message: Optional[str] = None,
                        focus_context: str = "",
                        apps_observed: Optional[List[str]] = None):
        """
        Record a decision in the timeline.
        This creates the transparency trail the UI displays.
        """
        with self._lock:
            decision = AgentDecisionRecord(
                timestamp=datetime.now().isoformat(),
                intent=intent,
                confidence=confidence,
                reasoning=reasoning,
                action=action,
                nudge_message=nudge_message,
                focus_context=focus_context,
                apps_observed=apps_observed or []
            )
            
            self._last_decision = decision
            self._timeline.append(decision)
            
            # Trim timeline if too long
            if len(self._timeline) > self.MAX_TIMELINE_ENTRIES:
                self._timeline = self._timeline[-self.MAX_TIMELINE_ENTRIES:]
            
            self._loop_count += 1
            logger.info(f"Decision recorded: {action} | {reasoning[:50]}...")
    
    def set_status(self, status: str):
        """Update agent status (observing, analyzing, idle)."""
        with self._lock:
            self._state.status = status
            self._state.last_updated = datetime.now().isoformat()
    
    def get_state(self) -> dict:
        """Get current agent state for UI."""
        with self._lock:
            return self._state.to_dict()
    
    def get_last_decision(self) -> Optional[dict]:
        """Get the most recent decision for UI."""
        with self._lock:
            if self._last_decision:
                return self._last_decision.to_dict()
            return None
    
    def get_timeline(self, limit: int = 20) -> List[dict]:
        """Get recent decision timeline for UI."""
        with self._lock:
            recent = self._timeline[-limit:] if self._timeline else []
            # Return in reverse chronological order (newest first)
            return [d.to_dict() for d in reversed(recent)]
    
    def get_stats(self) -> dict:
        """Get agent statistics."""
        with self._lock:
            nudge_count = sum(1 for d in self._timeline if d.action == "nudge")
            return {
                "total_decisions": len(self._timeline),
                "total_nudges": nudge_count,
                "loop_count": self._loop_count,
                "is_active": self._state.is_active
            }


# Global state manager instance
_state_manager: Optional[AgentStateManager] = None


def get_state_manager() -> AgentStateManager:
    """Get or create the global state manager."""
    global _state_manager
    if _state_manager is None:
        _state_manager = AgentStateManager()
    return _state_manager


# ============================================================
# FastAPI Server for UI Communication
# ============================================================

def create_local_api():
    """
    Create the local FastAPI app for UI communication.
    
    This is intentionally separate from the cloud service.
    The UI talks ONLY to this local API.
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    api = FastAPI(
        title="Kairos Local Agent API",
        description="Read-only API for the Kairos UI. The UI observes, never controls.",
        version="1.0.0"
    )
    
    # Allow CORS for local UI development
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Local development
        allow_credentials=True,
        allow_methods=["GET"],  # READ-ONLY
        allow_headers=["*"],
    )
    
    @api.get("/")
    async def root():
        """API information."""
        return {
            "service": "Kairos Local Agent API",
            "purpose": "Read-only state exposure for UI",
            "note": "This API does NOT control the agent"
        }
    
    @api.get("/health")
    async def health():
        """Local agent health check."""
        manager = get_state_manager()
        stats = manager.get_stats()
        return {
            "status": "healthy",
            "agent_active": stats["is_active"],
            "decisions_made": stats["total_decisions"],
            "timestamp": datetime.now().isoformat()
        }
    
    @api.get("/state")
    async def get_state():
        """
        Get current agent state.
        
        Returns:
        - intent: What the agent thinks you're doing
        - confidence: How sure the agent is
        - focus_context: Human-readable context
        - status: Current agent status
        """
        manager = get_state_manager()
        return manager.get_state()
    
    @api.get("/decision")
    async def get_decision():
        """
        Get the last decision made by the agent.
        
        Returns the most recent decision including:
        - reasoning: Why the agent made this decision
        - action: What the agent did (or didn't do)
        """
        manager = get_state_manager()
        decision = manager.get_last_decision()
        if decision:
            return decision
        return {
            "message": "No decisions yet - agent is still initializing",
            "timestamp": datetime.now().isoformat()
        }
    
    @api.get("/timeline")
    async def get_timeline(limit: int = 20):
        """
        Get the reasoning timeline.
        
        Returns a chronological list of agent decisions,
        newest first. This builds transparency and trust.
        """
        manager = get_state_manager()
        return {
            "timeline": manager.get_timeline(limit=min(limit, 50)),
            "total_decisions": manager.get_stats()["total_decisions"]
        }
    
    @api.get("/stats")
    async def get_stats():
        """Get agent statistics."""
        manager = get_state_manager()
        return manager.get_stats()
    
    return api


# Create the API instance
local_api = create_local_api()


def run_local_api(port: int = 5000):
    """Run the local API server."""
    import uvicorn
    logger.info(f"Starting local agent API on http://localhost:{port}")
    uvicorn.run(local_api, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_local_api()
