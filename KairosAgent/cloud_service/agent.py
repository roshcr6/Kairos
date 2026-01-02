"""
Kairos Agent - Cloud Agent Logic
=================================
Implements the reasoning agent that processes activity summaries
and makes decisions using Vertex AI (Gemini).

This is the "brain" of the cloud service.

Author: Kairos Team - AgentX Hackathon 2026
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from models import (
    AnalyzeRequest, 
    AgentDecision, 
    IntentType, 
    ActionType,
    GeminiPromptContext
)
from vertex_client import VertexClient

logger = logging.getLogger(__name__)


class ReasoningAgent:
    """
    The core reasoning agent for Kairos.
    
    Implements intelligent decision-making:
    1. Receives activity summaries from local agents
    2. Enriches with context (time of day, history)
    3. Calls Vertex AI Gemini for reasoning
    4. Post-processes to ensure safe, helpful responses
    """
    
    def __init__(self, vertex_client: Optional[VertexClient] = None):
        """
        Initialize the reasoning agent.
        
        Args:
            vertex_client: Optional pre-configured Vertex client
        """
        self.vertex_client = vertex_client or VertexClient()
        
        # Agent state (in production, this would be persisted)
        self.request_count = 0
        self.nudge_count = 0
    
    async def analyze(self, request: AnalyzeRequest) -> AgentDecision:
        """
        Main entry point for analyzing activity.
        
        This method orchestrates the full reasoning pipeline:
        1. Extract and enrich context
        2. Call Gemini for analysis
        3. Post-process and validate decision
        4. Return structured response
        
        Args:
            request: The analysis request from local agent
        
        Returns:
            AgentDecision with intent, confidence, reasoning, and action
        """
        self.request_count += 1
        logger.info(f"Processing analysis request #{self.request_count}")
        
        # Step 1: Extract and enrich context
        context = self._build_context(request)
        
        # Step 2: Call Vertex AI Gemini
        raw_decision = self.vertex_client.analyze_activity(
            activity_summary=request.activity_summary.model_dump(),
            user_goals=request.user_goals,
            local_classification=request.local_classification.model_dump() if request.local_classification else None,
            context=context
        )
        
        # Step 3: Post-process decision
        decision = self._post_process_decision(raw_decision, request)
        
        # Step 4: Track metrics
        if decision.action == ActionType.NUDGE:
            self.nudge_count += 1
            logger.info(f"Nudge recommended (total: {self.nudge_count})")
        
        return decision
    
    def _build_context(self, request: AnalyzeRequest) -> Dict[str, Any]:
        """
        Build rich context for Gemini reasoning.
        
        Includes:
        - Time of day context (morning productivity vs late-night browsing)
        - Request context from local agent
        - Historical patterns (future enhancement)
        """
        context = {}
        
        # Add time context
        now = datetime.now()
        hour = now.hour
        
        if 6 <= hour < 12:
            context["time_period"] = "morning"
            context["time_note"] = "Morning hours - typically high productivity time"
        elif 12 <= hour < 14:
            context["time_period"] = "lunch"
            context["time_note"] = "Lunch hours - breaks are expected"
        elif 14 <= hour < 18:
            context["time_period"] = "afternoon"
            context["time_note"] = "Afternoon - sustained work period"
        elif 18 <= hour < 22:
            context["time_period"] = "evening"
            context["time_note"] = "Evening - work-life balance matters"
        else:
            context["time_period"] = "late_night"
            context["time_note"] = "Late night - entertainment is acceptable"
        
        # Add request context if provided
        if request.context:
            context["timestamp"] = request.context.timestamp
            context["consecutive_nudges"] = request.context.consecutive_nudges
            
            # If we've nudged recently, be more lenient
            if request.context.consecutive_nudges >= 2:
                context["nudge_fatigue"] = True
                context["nudge_note"] = "User has received multiple nudges - be more lenient"
        
        return context
    
    def _post_process_decision(self, 
                                raw_decision: Dict[str, Any],
                                request: AnalyzeRequest) -> AgentDecision:
        """
        Post-process Gemini's decision for safety and consistency.
        
        Applies business rules:
        - Never nudge with very low confidence
        - Respect nudge fatigue
        - Ensure nudge messages are appropriate
        - Handle edge cases gracefully
        """
        intent_str = raw_decision.get("intent", "unknown").lower()
        action_str = raw_decision.get("action", "none").lower()
        confidence = float(raw_decision.get("confidence", 0.0))
        reasoning = raw_decision.get("reasoning", "No reasoning provided")
        nudge_message = raw_decision.get("nudge_message")
        
        # Validate and convert intent
        try:
            intent = IntentType(intent_str)
        except ValueError:
            intent = IntentType.UNKNOWN
            confidence = min(confidence, 0.5)
        
        # Apply business rules for nudging
        should_nudge = action_str == "nudge"
        
        # Rule 1: Don't nudge with low confidence
        if confidence < 0.6:
            should_nudge = False
            if action_str == "nudge":
                reasoning += " [Note: Nudge suppressed due to low confidence]"
        
        # Rule 2: Respect nudge fatigue
        if request.context and request.context.consecutive_nudges >= 2:
            should_nudge = False
            if action_str == "nudge":
                reasoning += " [Note: Nudge suppressed to avoid fatigue]"
        
        # Rule 3: Time-based leniency (late night)
        hour = datetime.now().hour
        if hour >= 22 or hour < 6:
            if intent == IntentType.UNPRODUCTIVE:
                should_nudge = False
                reasoning += " [Note: Late hours - leisure time respected]"
        
        # Determine final action
        action = ActionType.NUDGE if should_nudge else ActionType.NONE
        
        # Clean up nudge message if not nudging
        if action != ActionType.NUDGE:
            nudge_message = None
        elif nudge_message is None and action == ActionType.NUDGE:
            # Generate a default nudge message
            nudge_message = self._generate_default_nudge(request.user_goals)
        
        return AgentDecision(
            intent=intent,
            confidence=confidence,
            reasoning=reasoning,
            action=action,
            nudge_message=nudge_message
        )
    
    def _generate_default_nudge(self, user_goals: list) -> str:
        """Generate a default, friendly nudge message."""
        goal = user_goals[0] if user_goals else "your goals"
        
        nudges = [
            f"🎯 Hey! Ready to get back to {goal}? You've got this!",
            f"💡 Quick check-in: How's your progress on {goal} going?",
            f"🌟 Taking a break is great! When you're ready, {goal} awaits.",
            f"⏰ Gentle reminder: You mentioned wanting to focus on {goal} today.",
        ]
        
        # Rotate through nudges based on count
        return nudges[self.nudge_count % len(nudges)]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "total_requests": self.request_count,
            "total_nudges": self.nudge_count,
            "nudge_rate": self.nudge_count / self.request_count if self.request_count > 0 else 0,
            "vertex_available": self.vertex_client.is_available()
        }


# Singleton instance for the service
_agent_instance: Optional[ReasoningAgent] = None


def get_agent() -> ReasoningAgent:
    """Get or create the reasoning agent singleton."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ReasoningAgent()
    return _agent_instance


# Quick test
if __name__ == "__main__":
    import asyncio
    import os
    
    logging.basicConfig(level=logging.INFO)
    os.environ["DEMO_MODE"] = "true"
    
    async def test():
        agent = get_agent()
        
        # Test request
        from models import ActivitySummary, LocalClassification, RequestContext
        
        request = AnalyzeRequest(
            activity_summary=ActivitySummary(
                period_start="2026-01-02T10:00:00",
                period_end="2026-01-02T10:05:00",
                total_duration_seconds=300,
                app_breakdown={
                    "Visual Studio Code": 100,
                    "YouTube": 200
                },
                top_windows=["main.py", "Funny Videos"],
                activity_switches=5
            ),
            user_goals=["coding", "learning"],
            local_classification=LocalClassification(
                intent="unproductive",
                confidence=0.7,
                reasoning="More time on YouTube than coding"
            ),
            context=RequestContext(
                consecutive_nudges=0,
                timestamp="2026-01-02T10:05:00"
            )
        )
        
        decision = await agent.analyze(request)
        print(f"\nDecision:")
        print(f"  Intent: {decision.intent}")
        print(f"  Confidence: {decision.confidence}")
        print(f"  Reasoning: {decision.reasoning}")
        print(f"  Action: {decision.action}")
        print(f"  Nudge: {decision.nudge_message}")
        
        print(f"\nStats: {agent.get_stats()}")
    
    asyncio.run(test())
