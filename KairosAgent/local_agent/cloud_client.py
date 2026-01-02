"""
Kairos Agent - Cloud Client
============================
Sends activity summaries to the Cloud Run service for Gemini-powered reasoning.
Implements retry logic and graceful fallback for offline operation.

Author: Kairos Team - AgentX Hackathon 2026
"""

import os
import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
import json

# Use httpx for async support and better error handling
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    import urllib.request
    import urllib.error
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class AgentDecision:
    """
    Decision returned by the cloud reasoning service.
    Maps to the Vertex AI structured output.
    """
    intent: str  # productive, neutral, unproductive
    confidence: float
    reasoning: str
    action: str  # none, nudge
    nudge_message: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentDecision":
        return cls(
            intent=data.get("intent", "unknown"),
            confidence=data.get("confidence", 0.0),
            reasoning=data.get("reasoning", "No reasoning provided"),
            action=data.get("action", "none"),
            nudge_message=data.get("nudge_message")
        )
    
    @classmethod
    def default_fallback(cls) -> "AgentDecision":
        """Return a safe fallback decision when cloud is unavailable."""
        return cls(
            intent="unknown",
            confidence=0.0,
            reasoning="Cloud service unavailable - using local classification only",
            action="none",
            nudge_message=None
        )


class CloudClient:
    """
    Client for communicating with the Kairos Cloud Run service.
    
    Design Decisions:
    - Sends only summarized data, never raw activity
    - Implements exponential backoff for retries
    - Falls back gracefully if cloud is unreachable
    - Caches last known decision for resilience
    """
    
    DEFAULT_TIMEOUT = 30.0  # seconds
    MAX_RETRIES = 3
    
    def __init__(self, 
                 service_url: Optional[str] = None,
                 user_goals: Optional[list] = None,
                 timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize the cloud client.
        
        Args:
            service_url: Cloud Run service URL (or set CLOUD_SERVICE_URL env var)
            user_goals: List of user's productivity goals
            timeout: Request timeout in seconds
        """
        self.service_url = service_url or os.getenv(
            "CLOUD_SERVICE_URL", 
            "http://localhost:8080"  # Default for local testing
        )
        self.user_goals = user_goals or self._load_user_goals()
        self.timeout = timeout
        self.last_decision: Optional[AgentDecision] = None
        self._consecutive_failures = 0
        
        # Demo mode for testing without actual cloud service
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        
        logger.info(f"CloudClient initialized: {self.service_url}")
        if self.demo_mode:
            logger.info("Running in DEMO MODE - cloud calls will be simulated")
    
    def _load_user_goals(self) -> list:
        """Load user goals from environment variable."""
        goals_str = os.getenv("USER_GOALS", "coding,learning,writing")
        return [g.strip() for g in goals_str.split(",")]
    
    def analyze_activity(self, 
                         activity_summary: dict,
                         local_classification: Optional[dict] = None) -> AgentDecision:
        """
        Send activity summary to cloud for Gemini-powered analysis.
        
        Args:
            activity_summary: Dict from ActivitySummary.to_dict()
            local_classification: Optional local classifier result for context
        
        Returns:
            AgentDecision with Gemini's reasoning and recommended action
        """
        if self.demo_mode:
            return self._demo_response(activity_summary)
        
        # Build request payload
        payload = {
            "activity_summary": activity_summary,
            "user_goals": self.user_goals,
            "local_classification": local_classification,
            "context": {
                "consecutive_nudges": self._consecutive_failures,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        }
        
        # Attempt request with retries
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self._make_request(payload)
                self._consecutive_failures = 0  # Reset on success
                self.last_decision = response
                return response
                
            except Exception as e:
                logger.warning(f"Cloud request failed (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    # Exponential backoff
                    sleep_time = (2 ** attempt) + (time.time() % 1)
                    time.sleep(sleep_time)
        
        # All retries failed - use fallback
        self._consecutive_failures += 1
        logger.error(f"Cloud service unreachable after {self.MAX_RETRIES} attempts")
        
        # Return cached decision or default fallback
        if self.last_decision:
            logger.info("Using cached last decision")
            return self.last_decision
        
        return AgentDecision.default_fallback()
    
    def _make_request(self, payload: dict) -> AgentDecision:
        """Make HTTP request to cloud service."""
        url = f"{self.service_url}/analyze"
        
        if HTTPX_AVAILABLE:
            return self._make_httpx_request(url, payload)
        else:
            return self._make_urllib_request(url, payload)
    
    def _make_httpx_request(self, url: str, payload: dict) -> AgentDecision:
        """Make request using httpx (preferred)."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return AgentDecision.from_dict(response.json())
    
    def _make_urllib_request(self, url: str, payload: dict) -> AgentDecision:
        """Fallback request using urllib (no external deps)."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            return AgentDecision.from_dict(response_data)
    
    def _demo_response(self, activity_summary: dict) -> AgentDecision:
        """Generate a realistic demo response without calling cloud."""
        app_breakdown = activity_summary.get("app_breakdown", {})
        
        # Simple demo logic
        productive_apps = ["code", "vscode", "visual studio code", "pycharm", "terminal"]
        distraction_apps = ["youtube", "spotify", "discord", "reddit"]
        
        productive_time = sum(
            dur for app, dur in app_breakdown.items() 
            if any(p in app.lower() for p in productive_apps)
        )
        distraction_time = sum(
            dur for app, dur in app_breakdown.items()
            if any(d in app.lower() for d in distraction_apps)
        )
        total_time = sum(app_breakdown.values()) or 1
        
        productive_ratio = productive_time / total_time
        distraction_ratio = distraction_time / total_time
        
        # Simulate Gemini's reasoning
        if productive_ratio > 0.7:
            return AgentDecision(
                intent="productive",
                confidence=0.88,
                reasoning=f"[DEMO] Great focus! {productive_ratio*100:.0f}% of time on development tools.",
                action="none"
            )
        elif distraction_ratio > 0.4:
            return AgentDecision(
                intent="unproductive",
                confidence=0.75,
                reasoning=f"[DEMO] Noticed {distraction_ratio*100:.0f}% time on entertainment apps.",
                action="nudge",
                nudge_message="🎯 You mentioned wanting to focus on coding. Ready to get back to it?"
            )
        else:
            return AgentDecision(
                intent="neutral",
                confidence=0.65,
                reasoning="[DEMO] Mixed activity - could be productive research or taking a break.",
                action="none"
            )
    
    def health_check(self) -> bool:
        """Check if cloud service is reachable."""
        if self.demo_mode:
            return True
        
        try:
            url = f"{self.service_url}/health"
            if HTTPX_AVAILABLE:
                with httpx.Client(timeout=5.0) as client:
                    response = client.get(url)
                    return response.status_code == 200
            else:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=5.0) as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test with demo mode
    os.environ["DEMO_MODE"] = "true"
    client = CloudClient()
    
    # Simulate activity summary
    test_summary = {
        "period_start": "2026-01-02T10:00:00",
        "period_end": "2026-01-02T10:05:00",
        "total_duration_seconds": 300,
        "app_breakdown": {
            "Visual Studio Code": 180,
            "Google Chrome": 60,
            "Spotify": 60
        },
        "top_windows": [
            "main.py - KairosAgent",
            "Stack Overflow - Python async"
        ],
        "activity_switches": 4
    }
    
    decision = client.analyze_activity(test_summary)
    print(f"Decision: {decision}")
    print(f"Intent: {decision.intent}")
    print(f"Action: {decision.action}")
    print(f"Reasoning: {decision.reasoning}")
    if decision.nudge_message:
        print(f"Nudge: {decision.nudge_message}")
