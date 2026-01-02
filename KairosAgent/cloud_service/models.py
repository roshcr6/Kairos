"""
Kairos Agent - Cloud Service Data Models
=========================================
Pydantic models for request/response validation.
These ensure type safety and clear API contracts.

Author: Kairos Team - AgentX Hackathon 2026
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


class IntentType(str, Enum):
    """Activity intent classification."""
    PRODUCTIVE = "productive"
    NEUTRAL = "neutral"
    UNPRODUCTIVE = "unproductive"
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    """Possible agent actions."""
    NONE = "none"
    NUDGE = "nudge"


# ============================================================
# Request Models
# ============================================================

class ActivitySummary(BaseModel):
    """
    Summarized activity data from local agent.
    Note: This is aggregated data, NOT raw surveillance data.
    """
    period_start: str = Field(..., description="ISO timestamp of period start")
    period_end: str = Field(..., description="ISO timestamp of period end")
    total_duration_seconds: float = Field(..., ge=0, description="Total duration tracked")
    app_breakdown: Dict[str, float] = Field(
        ..., 
        description="Map of app names to seconds spent"
    )
    top_windows: List[str] = Field(
        default=[],
        max_length=10,
        description="Top window titles (sanitized)"
    )
    activity_switches: int = Field(
        default=0,
        ge=0,
        description="Number of app switches in period"
    )


class LocalClassification(BaseModel):
    """Local classifier's assessment (for context)."""
    intent: str = Field(..., description="Local intent classification")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score 0-1")
    reasoning: str = Field(..., description="Local reasoning")


class RequestContext(BaseModel):
    """Additional context for decision-making."""
    consecutive_nudges: int = Field(default=0, ge=0)
    timestamp: str = Field(default="")
    user_timezone: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """
    Request to analyze activity and decide on action.
    This is what the local agent sends to Cloud Run.
    """
    activity_summary: ActivitySummary
    user_goals: List[str] = Field(
        default=["productivity"],
        description="User's stated productivity goals"
    )
    local_classification: Optional[LocalClassification] = None
    context: Optional[RequestContext] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "activity_summary": {
                    "period_start": "2026-01-02T10:00:00",
                    "period_end": "2026-01-02T10:05:00",
                    "total_duration_seconds": 300,
                    "app_breakdown": {
                        "Visual Studio Code": 180,
                        "Google Chrome": 120
                    },
                    "top_windows": ["main.py - project"],
                    "activity_switches": 3
                },
                "user_goals": ["coding", "learning"],
                "local_classification": {
                    "intent": "productive",
                    "confidence": 0.85,
                    "reasoning": "Mostly coding activity"
                }
            }
        }


# ============================================================
# Response Models
# ============================================================

class AgentDecision(BaseModel):
    """
    The agent's decision after Gemini reasoning.
    This is what Cloud Run returns to the local agent.
    """
    intent: IntentType = Field(
        ..., 
        description="Classified intent of user activity"
    )
    confidence: float = Field(
        ..., 
        ge=0, 
        le=1, 
        description="Confidence in classification (0-1)"
    )
    reasoning: str = Field(
        ..., 
        description="Human-readable explanation of decision"
    )
    action: ActionType = Field(
        ..., 
        description="Recommended action"
    )
    nudge_message: Optional[str] = Field(
        None,
        description="Message to show user if action is 'nudge'"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "intent": "productive",
                "confidence": 0.88,
                "reasoning": "User spent 60% of time in VS Code working on code files",
                "action": "none",
                "nudge_message": None
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    service: str = "kairos-cloud-agent"
    version: str = "1.0.0"
    vertex_ai_available: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================
# Vertex AI Prompt Models
# ============================================================

class GeminiPromptContext(BaseModel):
    """
    Context to be sent to Gemini for reasoning.
    Structured for optimal prompt engineering.
    """
    user_goals: List[str]
    activity_summary: Dict
    local_assessment: Optional[Dict] = None
    time_context: str = ""  # e.g., "morning", "late night"
    historical_context: str = ""  # e.g., "productive streak of 3 periods"


class GeminiResponse(BaseModel):
    """
    Expected JSON response format from Gemini.
    We instruct Gemini to return exactly this structure.
    """
    intent: str = Field(..., pattern="^(productive|neutral|unproductive)$")
    confidence: float = Field(..., ge=0, le=1)
    reasoning: str = Field(..., min_length=10, max_length=500)
    action: str = Field(..., pattern="^(none|nudge)$")
    nudge_message: Optional[str] = Field(None, max_length=200)
