"""
Kairos Agent - Local Agent Main Entry Point
=============================================
Implements the core agent loop: Observe → Summarize → Decide → Act → Reflect

This is the main orchestrator that ties together activity tracking,
local classification, cloud reasoning, and user nudging.

The agent runs AUTONOMOUSLY - the UI only observes, never controls.

Author: Kairos Team - AgentX Hackathon 2026
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Optional
import threading

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("kairos")

# Local imports
from activity_tracker import ActivityTracker, ActivitySummary
from classifier import LocalClassifier, ActivityIntent
from cloud_client import CloudClient, AgentDecision
from api_server import get_state_manager, AgentStateManager


def run_local_api(port: int = 5000):
    """Run the local API server for UI communication."""
    import uvicorn
    from api_server import local_api
    logger.info(f"Starting local agent API on http://localhost:{port}")
    uvicorn.run(local_api, host="127.0.0.1", port=port, log_level="warning")


class NudgeManager:
    """
    Manages user nudges to avoid being annoying.
    
    Rules:
    - Minimum 10 minutes between nudges
    - Maximum 3 nudges per hour
    - Back off if user dismisses multiple nudges
    """
    
    MIN_NUDGE_INTERVAL = 600  # 10 minutes
    MAX_NUDGES_PER_HOUR = 3
    
    def __init__(self):
        self.nudge_history: list[datetime] = []
        self.dismissal_count = 0
    
    def can_nudge(self) -> bool:
        """Check if we're allowed to nudge the user."""
        now = datetime.now()
        
        # Remove nudges older than 1 hour
        self.nudge_history = [
            n for n in self.nudge_history 
            if (now - n).total_seconds() < 3600
        ]
        
        # Check rate limits
        if len(self.nudge_history) >= self.MAX_NUDGES_PER_HOUR:
            logger.debug("Nudge blocked: hourly limit reached")
            return False
        
        # Check minimum interval
        if self.nudge_history:
            last_nudge = self.nudge_history[-1]
            if (now - last_nudge).total_seconds() < self.MIN_NUDGE_INTERVAL:
                logger.debug("Nudge blocked: too soon after last nudge")
                return False
        
        # Back off if user keeps dismissing
        if self.dismissal_count >= 2:
            logger.debug("Nudge blocked: user dismissed multiple times")
            return False
        
        return True
    
    def record_nudge(self):
        """Record that we sent a nudge."""
        self.nudge_history.append(datetime.now())
    
    def record_dismissal(self):
        """Record that user dismissed a nudge."""
        self.dismissal_count += 1
    
    def reset_dismissals(self):
        """Reset dismissal count (e.g., when user is productive again)."""
        self.dismissal_count = 0


def display_nudge(message: str, reasoning: str):
    """
    Display a nudge to the user.
    
    In a real implementation, this could be:
    - Windows toast notification
    - System tray popup
    - Desktop widget
    
    For hackathon, we use console output and optional toast.
    """
    print("\n" + "="*60)
    print("🔔 KAIROS NUDGE")
    print("="*60)
    print(f"\n{message}\n")
    print(f"(Why: {reasoning})")
    print("="*60 + "\n")
    
    # Try Windows toast notification (optional)
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(
            "Kairos Agent",
            message,
            duration=5,
            threaded=True
        )
    except ImportError:
        pass  # win10toast not installed, that's fine
    except Exception as e:
        logger.debug(f"Toast notification failed: {e}")


def display_status(summary: ActivitySummary, 
                   local_result, 
                   cloud_decision: Optional[AgentDecision]):
    """Display current status to console."""
    print("\n" + "-"*50)
    print(f"📊 Activity Summary ({summary.period_start.strftime('%H:%M')} - {summary.period_end.strftime('%H:%M')})")
    print("-"*50)
    
    # Show app breakdown
    if summary.app_breakdown:
        print("\nTime by App:")
        sorted_apps = sorted(summary.app_breakdown.items(), key=lambda x: x[1], reverse=True)
        for app, duration in sorted_apps[:5]:
            minutes = duration / 60
            bar = "█" * int(minutes / 2) + "░" * (10 - int(minutes / 2))
            print(f"  {bar} {app}: {minutes:.1f}m")
    
    print(f"\n🔄 App switches: {summary.activity_switches}")
    
    # Local classification
    print(f"\n🏠 Local Analysis:")
    print(f"   Intent: {local_result.intent.value}")
    print(f"   Confidence: {local_result.confidence:.0%}")
    print(f"   Note: {local_result.reasoning}")
    
    # Cloud decision (if available)
    if cloud_decision and cloud_decision.intent != "unknown":
        print(f"\n☁️ Cloud Analysis (Gemini):")
        print(f"   Intent: {cloud_decision.intent}")
        print(f"   Confidence: {cloud_decision.confidence:.0%}")
        print(f"   Reasoning: {cloud_decision.reasoning}")
        print(f"   Action: {cloud_decision.action}")
    
    print("-"*50 + "\n")


class KairosAgent:
    """
    The main Kairos Agent orchestrator.
    
    Implements a true agent loop:
    1. OBSERVE: Track foreground windows
    2. SUMMARIZE: Aggregate into privacy-preserving summaries
    3. DECIDE: Use local classifier + cloud Gemini reasoning
    4. ACT: Nudge user if needed (with rate limiting)
    5. REFLECT: Log outcomes and update state for UI transparency
    
    CRITICAL: This agent runs AUTONOMOUSLY.
    The UI can observe its state but CANNOT control it.
    """
    
    def __init__(self):
        # Load configuration from environment
        self.user_goals = self._load_goals()
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        
        # Initialize components
        self.tracker = ActivityTracker()
        self.classifier = LocalClassifier(user_goals=self.user_goals)
        self.cloud_client = CloudClient(user_goals=self.user_goals)
        self.nudge_manager = NudgeManager()
        
        # State manager for UI transparency
        self.state_manager = get_state_manager()
        
        # Agent state
        self.running = False
        self.loop_count = 0
        self.productive_streak = 0
        self.last_action = "none"
        
        # Current focus context (human-readable)
        self.current_focus = "Initializing..."
        
        logger.info(f"Kairos Agent initialized")
        logger.info(f"User goals: {self.user_goals}")
        logger.info(f"Demo mode: {self.demo_mode}")
    
    def _load_goals(self) -> list:
        """Load user goals from environment."""
        goals_str = os.getenv("USER_GOALS", "coding,learning,writing")
        return [g.strip() for g in goals_str.split(",")]
    
    def observe(self):
        """OBSERVE: Record current activity."""
        self.state_manager.set_status("observing")
        activity_changed = self.tracker.record_activity()
        if activity_changed and self.tracker.current_activity:
            logger.debug(f"Switched to: {self.tracker.current_activity.app_name}")
            # Update focus context for UI
            self.current_focus = f"Working in {self.tracker.current_activity.app_name}"
    
    def summarize(self) -> Optional[ActivitySummary]:
        """SUMMARIZE: Generate activity summary if enough time passed."""
        if self.tracker.should_generate_summary():
            self.state_manager.set_status("summarizing")
            return self.tracker.generate_summary()
        return None
    
    def decide(self, summary: ActivitySummary) -> tuple:
        """
        DECIDE: Determine intent and whether to nudge.
        
        Uses two-stage classification:
        1. Fast local classification for obvious cases
        2. Cloud Gemini reasoning for ambiguous/important cases
        """
        self.state_manager.set_status("analyzing")
        
        # Stage 1: Local classification
        local_result = self.classifier.classify_summary(
            summary.app_breakdown,
            summary.top_windows
        )
        
        logger.info(f"Local classification: {local_result.intent.value} "
                   f"({local_result.confidence:.0%} confidence)")
        
        # Update focus context based on top apps
        if summary.app_breakdown:
            top_app = max(summary.app_breakdown.items(), key=lambda x: x[1])[0]
            self.current_focus = f"Focused on {top_app}"
        
        # Stage 2: Cloud reasoning (if needed or if local is uncertain)
        cloud_decision = None
        
        if local_result.needs_cloud_verification:
            logger.info("🌐 Sending to cloud for Gemini verification...")
            cloud_decision = self.cloud_client.analyze_activity(
                summary.to_dict(),
                {
                    "intent": local_result.intent.value,
                    "confidence": local_result.confidence,
                    "reasoning": local_result.reasoning
                }
            )
            logger.info(f"☁️ Cloud decision: {cloud_decision.intent} "
                       f"({cloud_decision.confidence:.0%}), action={cloud_decision.action}")
        else:
            # Local was confident enough, create a matching decision
            cloud_decision = AgentDecision(
                intent=local_result.intent.value,
                confidence=local_result.confidence,
                reasoning=local_result.reasoning,
                action="none"  # Local doesn't trigger nudges by itself
            )
        
        # Update state for UI
        self.state_manager.update_state(
            intent=cloud_decision.intent,
            confidence=cloud_decision.confidence,
            focus_context=self.current_focus,
            status="decided"
        )
        
        return local_result, cloud_decision
    
    def act(self, cloud_decision: AgentDecision):
        """
        ACT: Execute the decision (nudge or stay quiet).
        
        Important: We only nudge if:
        - Cloud recommends it
        - NudgeManager allows it (rate limiting)
        - We have a meaningful message
        """
        if cloud_decision.action == "nudge":
            if self.nudge_manager.can_nudge():
                message = cloud_decision.nudge_message or \
                    "You seem to have drifted from your goals. Need help refocusing?"
                
                display_nudge(message, cloud_decision.reasoning)
                self.nudge_manager.record_nudge()
                self.last_action = "nudge"
                self.productive_streak = 0
            else:
                logger.info("Nudge suppressed by rate limiting")
                self.last_action = "suppressed"
        else:
            self.last_action = "none"
            if cloud_decision.intent == "productive":
                self.productive_streak += 1
                # Reset dismissals when user is being productive
                if self.productive_streak >= 2:
                    self.nudge_manager.reset_dismissals()
    
    def reflect(self, summary: ActivitySummary, local_result, cloud_decision: AgentDecision):
        """
        REFLECT: Log the outcome, update UI state, and display status.
        
        This is where transparency happens - we record WHY
        the agent made its decision so the UI can explain it.
        """
        self.loop_count += 1
        self.state_manager.set_status("reflecting")
        
        # Record decision in timeline for UI transparency
        apps_observed = list(summary.app_breakdown.keys()) if summary.app_breakdown else []
        self.state_manager.record_decision(
            intent=cloud_decision.intent,
            confidence=cloud_decision.confidence,
            reasoning=cloud_decision.reasoning,
            action=self.last_action,
            nudge_message=cloud_decision.nudge_message if self.last_action == "nudge" else None,
            focus_context=self.current_focus,
            apps_observed=apps_observed
        )
        
        # Display status to console (for debugging)
        display_status(summary, local_result, cloud_decision)
        
        # Update status back to observing
        self.state_manager.set_status("observing")
        
        # Log for debugging/analysis
        logger.info(f"Loop {self.loop_count} complete | "
                   f"Action: {self.last_action} | "
                   f"Productive streak: {self.productive_streak}")
    
    def run_loop_iteration(self):
        """Run a single iteration of the agent loop."""
        # OBSERVE
        self.observe()
        
        # SUMMARIZE (may return None if not enough time)
        summary = self.summarize()
        if not summary:
            return  # Not time for a summary yet
        
        # DECIDE
        local_result, cloud_decision = self.decide(summary)
        
        # ACT
        self.act(cloud_decision)
        
        # REFLECT
        self.reflect(summary, local_result, cloud_decision)
    
    def run(self, duration_seconds: Optional[int] = None, enable_ui_api: bool = True):
        """
        Run the agent main loop.
        
        Args:
            duration_seconds: Optional limit (for demos). None = run forever.
            enable_ui_api: Whether to start the local API for UI communication.
        """
        self.running = True
        start_time = time.time()
        
        # Start UI API server in background thread
        api_thread = None
        if enable_ui_api:
            api_thread = threading.Thread(
                target=run_local_api,
                kwargs={"port": 5000},
                daemon=True
            )
            api_thread.start()
            time.sleep(1)  # Give API time to start
        
        print("\n" + "="*60)
        print("🚀 KAIROS AGENT STARTED")
        print("="*60)
        print(f"Goals: {', '.join(self.user_goals)}")
        print(f"Mode: {'DEMO' if self.demo_mode else 'PRODUCTION'}")
        print(f"Tracking interval: {self.tracker.POLL_INTERVAL}s")
        print(f"Summary interval: {self.tracker.SUMMARY_INTERVAL}s")
        if enable_ui_api:
            print(f"\n🖥️  UI API: http://localhost:5000")
            print(f"    Open the UI to see agent reasoning in real-time")
        print("="*60)
        print("\nThe agent is now running AUTONOMOUSLY.")
        print("Press Ctrl+C to stop.\n")
        
        # Update initial state
        self.state_manager.update_state(
            intent="unknown",
            confidence=0.0,
            focus_context="Starting up...",
            status="observing"
        )
        
        try:
            while self.running:
                self.run_loop_iteration()
                
                # Check duration limit
                if duration_seconds:
                    elapsed = time.time() - start_time
                    if elapsed >= duration_seconds:
                        logger.info(f"Duration limit reached ({duration_seconds}s)")
                        break
                
                # Sleep between observations
                time.sleep(self.tracker.POLL_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Kairos Agent stopped by user.")
        finally:
            self.running = False
            self.state_manager.set_status("stopped")
            self._print_session_summary()
    
    def _print_session_summary(self):
        """Print a summary of the session."""
        print("\n" + "="*60)
        print("📈 SESSION SUMMARY")
        print("="*60)
        print(f"Total loops: {self.loop_count}")
        print(f"Final productive streak: {self.productive_streak}")
        print("="*60 + "\n")


def main():
    """Main entry point."""
    # Check for quick demo mode
    if "--demo" in sys.argv:
        os.environ["DEMO_MODE"] = "true"
        os.environ["USER_GOALS"] = "coding,learning"
    
    # Check for custom duration
    duration = None
    for arg in sys.argv:
        if arg.startswith("--duration="):
            duration = int(arg.split("=")[1])
    
    # Reduce summary interval for demo
    if os.getenv("DEMO_MODE") == "true":
        # Override summary interval for faster demo feedback
        ActivityTracker.SUMMARY_INTERVAL = 30  # 30 seconds instead of 5 minutes
        logger.info("Demo mode: Summary interval reduced to 30 seconds")
    
    # Create and run agent
    agent = KairosAgent()
    agent.run(duration_seconds=duration)


if __name__ == "__main__":
    main()
