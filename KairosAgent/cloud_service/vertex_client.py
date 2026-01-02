"""
Kairos Agent - Vertex AI Client
================================
Handles communication with Google Vertex AI (Gemini) for intelligent reasoning.
This is where the LLM magic happens!

Environment Variables:
- CLOUD_MODE: When "true", uses real Vertex AI. When "false", uses deterministic responses.
- PROJECT_ID or GOOGLE_CLOUD_PROJECT: GCP project ID
- LOCATION or GOOGLE_CLOUD_REGION: GCP region (default: us-central1)

Author: Kairos Team - AgentX Hackathon 2026
"""

import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Configuration from environment
CLOUD_MODE = os.getenv("CLOUD_MODE", "true").lower() == "true"
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Vertex AI imports (with graceful fallback)
VERTEX_AVAILABLE = False
if CLOUD_MODE and not DEMO_MODE:
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel, GenerationConfig
        VERTEX_AVAILABLE = True
        logger.info("✅ Vertex AI SDK loaded successfully")
    except ImportError:
        logger.warning("⚠️ Vertex AI SDK not available. Install with: pip install google-cloud-aiplatform")
else:
    logger.info(f"🔧 Running in {'DEMO' if DEMO_MODE else 'LOCAL'} mode - Vertex AI disabled")


class VertexClient:
    """
    Client for Google Vertex AI Gemini API.
    
    Design Decisions:
    - Uses Gemini 1.5 Flash for speed (good enough for this use case)
    - Structured JSON output via response schema
    - Role-based prompting for consistent behavior
    - Graceful fallback when Vertex AI is unavailable
    """
    
    # Model configuration
    MODEL_NAME = "gemini-1.5-flash-002"  # Fast, capable, cost-effective
    
    # System prompt that defines the agent's behavior
    SYSTEM_PROMPT = """You are Kairos, an autonomous productivity AI agent.

Your role is to analyze user activity summaries and make intelligent decisions about whether to nudge them back to their goals.

CRITICAL RULES:
1. Be SUPPORTIVE, not judgmental. Users are humans who need breaks.
2. Only recommend a "nudge" if activity CLEARLY contradicts stated goals.
3. Short breaks (< 10 min) on entertainment apps are NORMAL and healthy.
4. Consider time of day - late night YouTube is different from 10 AM YouTube.
5. When in doubt, choose "none" for action. False positives are worse than false negatives.
6. Your nudge messages should be ENCOURAGING, not guilt-inducing.

You will receive:
- User's stated goals (e.g., "coding", "learning")
- Activity summary (apps used, time spent)
- Local classifier's assessment (for reference)

You must respond with JSON containing:
- intent: "productive" | "neutral" | "unproductive"
- confidence: 0.0 to 1.0
- reasoning: Brief explanation (1-2 sentences)
- action: "none" | "nudge"
- nudge_message: Only if action is "nudge" - a kind, helpful message"""

    def __init__(self, 
                 project_id: Optional[str] = None,
                 location: Optional[str] = None):
        """
        Initialize Vertex AI client.
        
        Args:
            project_id: GCP project ID (or PROJECT_ID/GOOGLE_CLOUD_PROJECT env var)
            location: GCP region (or LOCATION/GOOGLE_CLOUD_REGION env var, default: us-central1)
        """
        self.project_id = project_id or os.getenv("PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("LOCATION") or os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        self.demo_mode = DEMO_MODE
        self.cloud_mode = CLOUD_MODE
        self.model = None
        self.initialized = False
        
        # Log configuration clearly
        logger.info(f"VertexClient Configuration:")
        logger.info(f"  - CLOUD_MODE: {self.cloud_mode}")
        logger.info(f"  - DEMO_MODE: {self.demo_mode}")
        logger.info(f"  - Project ID: {self.project_id or 'not-set'}")
        logger.info(f"  - Location: {self.location}")
        
        if self.demo_mode:
            logger.info("🔧 VertexClient running in DEMO mode (deterministic responses)")
            return
        
        if not self.cloud_mode:
            logger.info("🔧 VertexClient running in LOCAL mode (deterministic responses)")
            return
        
        if not VERTEX_AVAILABLE:
            logger.warning("⚠️ Vertex AI SDK not available - running in fallback mode")
            return
        
        if not self.project_id:
            logger.warning("⚠️ PROJECT_ID not set - running in fallback mode")
            return
        
        try:
            self._initialize_vertex()
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vertex AI: {e}")
    
    def _initialize_vertex(self):
        """Initialize Vertex AI and the Gemini model."""
        logger.info(f"🚀 Initializing Vertex AI: project={self.project_id}, location={self.location}")
        
        vertexai.init(project=self.project_id, location=self.location)
        
        self.model = GenerativeModel(
            self.MODEL_NAME,
            system_instruction=self.SYSTEM_PROMPT
        )
        
        self.initialized = True
        logger.info(f"✅ VERTEX AI INITIALIZED")
        logger.info(f"   Model: {self.MODEL_NAME}")
        logger.info(f"   Project: {self.project_id}")
        logger.info(f"   Location: {self.location}")
    
    def is_available(self) -> bool:
        """Check if Vertex AI is available for use."""
        return self.initialized or self.demo_mode or not self.cloud_mode
    
    def analyze_activity(self, 
                         activity_summary: Dict,
                         user_goals: list,
                         local_classification: Optional[Dict] = None,
                         context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyze activity using Gemini and return a decision.
        
        Args:
            activity_summary: Summarized activity data
            user_goals: User's stated productivity goals
            local_classification: Local classifier's assessment (for context)
            context: Additional context (time, history, etc.)
        
        Returns:
            Decision dict with intent, confidence, reasoning, action, nudge_message
        """
        # Use demo/deterministic responses when not in cloud mode
        if self.demo_mode or not self.cloud_mode:
            logger.info("🔧 Using deterministic response (CLOUD_MODE=false or DEMO_MODE=true)")
            return self._demo_response(activity_summary, user_goals)
        
        if not self.initialized:
            logger.warning("⚠️ Vertex AI not initialized - using fallback")
            return self._fallback_response(activity_summary, local_classification)
        
        # Build the prompt
        prompt = self._build_prompt(activity_summary, user_goals, local_classification, context)
        
        try:
            # Call Gemini
            logger.info("🧠 Calling Vertex AI (Gemini) for reasoning...")
            response = self._call_gemini(prompt)
            
            # Parse and validate response
            decision = self._parse_response(response)
            logger.info(f"✅ Gemini response: intent={decision.get('intent')}, action={decision.get('action')}")
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ Gemini call failed: {e}")
            return self._fallback_response(activity_summary, local_classification)
    
    def _build_prompt(self,
                      activity_summary: Dict,
                      user_goals: list,
                      local_classification: Optional[Dict],
                      context: Optional[Dict]) -> str:
        """Build the prompt for Gemini."""
        
        # Format app breakdown nicely
        app_breakdown = activity_summary.get("app_breakdown", {})
        total_time = activity_summary.get("total_duration_seconds", 0)
        
        apps_formatted = []
        for app, duration in sorted(app_breakdown.items(), key=lambda x: x[1], reverse=True):
            percentage = (duration / total_time * 100) if total_time > 0 else 0
            apps_formatted.append(f"- {app}: {duration/60:.1f} minutes ({percentage:.0f}%)")
        
        apps_str = "\n".join(apps_formatted) if apps_formatted else "No activity data"
        
        # Build context section
        context_str = ""
        if context:
            if context.get("timestamp"):
                context_str += f"\nCurrent time: {context.get('timestamp')}"
        
        # Build local assessment section
        local_str = ""
        if local_classification:
            local_str = f"""
Local Classifier Assessment:
- Intent: {local_classification.get('intent', 'unknown')}
- Confidence: {local_classification.get('confidence', 0):.0%}
- Reasoning: {local_classification.get('reasoning', 'N/A')}"""
        
        prompt = f"""Analyze this activity and decide whether to nudge the user.

USER'S GOALS: {', '.join(user_goals)}

ACTIVITY SUMMARY (last {total_time/60:.1f} minutes):
{apps_str}

Window titles observed: {', '.join(activity_summary.get('top_windows', [])[:3])}
App switches: {activity_summary.get('activity_switches', 0)}
{context_str}
{local_str}

Based on this information, provide your analysis in JSON format:
{{
    "intent": "productive|neutral|unproductive",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "action": "none|nudge",
    "nudge_message": "only if action is nudge"
}}"""
        
        return prompt
    
    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini and get response."""
        # Configure for JSON output
        generation_config = GenerationConfig(
            temperature=0.3,  # Lower temperature for more consistent decisions
            max_output_tokens=500,
            response_mime_type="application/json"
        )
        
        response = self.model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return response.text
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini's JSON response."""
        try:
            # Clean up response (sometimes has markdown code blocks)
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            decision = json.loads(text.strip())
            
            # Validate required fields
            required = ["intent", "confidence", "reasoning", "action"]
            for field in required:
                if field not in decision:
                    raise ValueError(f"Missing required field: {field}")
            
            # Normalize values
            decision["intent"] = decision["intent"].lower()
            decision["action"] = decision["action"].lower()
            decision["confidence"] = float(decision["confidence"])
            
            # Ensure nudge_message exists
            if "nudge_message" not in decision:
                decision["nudge_message"] = None
            
            return decision
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}\nResponse: {response_text}")
            return self._default_decision()
    
    def _demo_response(self, activity_summary: Dict, user_goals: list) -> Dict[str, Any]:
        """Generate realistic demo response without calling Vertex AI."""
        app_breakdown = activity_summary.get("app_breakdown", {})
        total_time = sum(app_breakdown.values()) or 1
        
        # Simple heuristic for demo
        productive_apps = ["code", "vscode", "visual studio code", "pycharm", 
                          "terminal", "powershell", "notion", "obsidian"]
        distraction_apps = ["youtube", "spotify", "discord", "netflix", 
                           "reddit", "twitter", "instagram"]
        
        productive_time = sum(
            dur for app, dur in app_breakdown.items()
            if any(p in app.lower() for p in productive_apps)
        )
        distraction_time = sum(
            dur for app, dur in app_breakdown.items()
            if any(d in app.lower() for d in distraction_apps)
        )
        
        productive_ratio = productive_time / total_time
        distraction_ratio = distraction_time / total_time
        
        # Generate contextual response
        if productive_ratio > 0.6:
            return {
                "intent": "productive",
                "confidence": round(0.75 + productive_ratio * 0.2, 2),
                "reasoning": f"[DEMO] Excellent focus! {productive_ratio*100:.0f}% of time spent on development tools. Your '{user_goals[0] if user_goals else 'work'}' goal is on track.",
                "action": "none",
                "nudge_message": None
            }
        elif distraction_ratio > 0.4:
            goals_str = user_goals[0] if user_goals else "your goals"
            return {
                "intent": "unproductive",
                "confidence": round(0.65 + distraction_ratio * 0.2, 2),
                "reasoning": f"[DEMO] Noticed {distraction_ratio*100:.0f}% of time on entertainment apps, which doesn't align with your stated goal of '{goals_str}'.",
                "action": "nudge",
                "nudge_message": f"🎯 Hey! Ready to get back to {goals_str}? You've got this!"
            }
        else:
            return {
                "intent": "neutral",
                "confidence": 0.60,
                "reasoning": "[DEMO] Mixed activity pattern - could be research, planning, or a healthy break. No intervention needed.",
                "action": "none",
                "nudge_message": None
            }
    
    def _fallback_response(self, 
                           activity_summary: Dict,
                           local_classification: Optional[Dict]) -> Dict[str, Any]:
        """Fallback when Vertex AI is unavailable."""
        if local_classification:
            # Trust local classifier when cloud is down
            return {
                "intent": local_classification.get("intent", "unknown"),
                "confidence": local_classification.get("confidence", 0.5) * 0.8,  # Reduce confidence
                "reasoning": f"[Fallback] Based on local classification: {local_classification.get('reasoning', 'N/A')}",
                "action": "none",  # Don't nudge when uncertain
                "nudge_message": None
            }
        
        return self._default_decision()
    
    def _default_decision(self) -> Dict[str, Any]:
        """Return safe default decision."""
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "reasoning": "Unable to determine - Vertex AI unavailable",
            "action": "none",
            "nudge_message": None
        }


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test in demo mode
    os.environ["DEMO_MODE"] = "true"
    
    client = VertexClient()
    print(f"Vertex available: {client.is_available()}")
    
    # Test analysis
    result = client.analyze_activity(
        activity_summary={
            "period_start": "2026-01-02T10:00:00",
            "period_end": "2026-01-02T10:05:00",
            "total_duration_seconds": 300,
            "app_breakdown": {
                "Visual Studio Code": 120,
                "YouTube": 180
            },
            "top_windows": ["main.py", "Funny Cat Videos"],
            "activity_switches": 5
        },
        user_goals=["coding", "learning"]
    )
    
    print(f"\nResult: {json.dumps(result, indent=2)}")
