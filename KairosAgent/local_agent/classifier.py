"""
Kairos Agent - Local Classifier
================================
Performs local classification of activity when confidence is high.
Reduces unnecessary cloud calls and improves privacy.

Author: Kairos Team - AgentX Hackathon 2026
"""

import logging
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class ActivityIntent(Enum):
    """Possible activity intents."""
    PRODUCTIVE = "productive"
    NEUTRAL = "neutral"
    UNPRODUCTIVE = "unproductive"
    UNKNOWN = "unknown"


@dataclass
class LocalClassification:
    """Result of local classification attempt."""
    intent: ActivityIntent
    confidence: float  # 0.0 to 1.0
    reasoning: str
    needs_cloud_verification: bool  # Should we ask the cloud for a second opinion?


class LocalClassifier:
    """
    Rule-based local classifier for common activity patterns.
    
    Design Philosophy:
    - Fast, deterministic classification for obvious cases
    - High confidence threshold (0.85+) to avoid false positives
    - Unknown/ambiguous cases go to cloud for Gemini reasoning
    - User can customize productive/unproductive app lists
    """
    
    # Default productive apps (can be overridden by user config)
    PRODUCTIVE_APPS = {
        "code", "vscode", "visual studio code", "pycharm", "intellij",
        "sublime_text", "atom", "vim", "neovim", "emacs",
        "terminal", "powershell", "cmd", "windowsterminal",
        "word", "excel", "powerpoint", "notion", "obsidian",
        "figma", "sketch", "photoshop", "illustrator",
        "slack", "teams", "zoom",  # Communication (context-dependent)
        "postman", "insomnia", "datagrip", "dbeaver",
    }
    
    # Default unproductive apps
    UNPRODUCTIVE_APPS = {
        "spotify", "netflix", "youtube",  # Entertainment
        "discord",  # Often leisure (but context-dependent)
        "steam", "epicgameslauncher", "battle.net",
        "twitter", "facebook", "instagram", "tiktok",
        "reddit",  # Could be productive (programming subreddits) - low confidence
    }
    
    # Neutral apps (not inherently productive or unproductive)
    NEUTRAL_APPS = {
        "explorer", "finder", "settings", "systempreferences",
        "chrome", "firefox", "edge", "safari", "brave",  # Depends on what they're viewing
    }
    
    # Window title keywords that suggest productivity
    PRODUCTIVE_KEYWORDS = [
        "github", "gitlab", "stackoverflow", "documentation",
        "api", "docs", "tutorial", "learning", "course",
        "jira", "trello", "asana", "linear", "notion",
        "pull request", "merge", "commit", "branch",
        ".py", ".js", ".ts", ".java", ".go", ".rs",  # Code file extensions
    ]
    
    # Window title keywords that suggest distraction
    DISTRACTION_KEYWORDS = [
        "youtube", "netflix", "twitch", "reddit",
        "twitter", "facebook", "instagram", "tiktok",
        "game", "play", "watch", "stream",
        "meme", "funny", "viral", "trending",
    ]
    
    def __init__(self, user_goals: Optional[List[str]] = None):
        """
        Initialize classifier with optional user goals.
        
        Args:
            user_goals: List of user's stated goals (e.g., ["coding", "learning", "writing"])
        """
        self.user_goals = user_goals or []
        self.custom_productive: set = set()
        self.custom_unproductive: set = set()
    
    def add_productive_app(self, app_name: str):
        """Add an app to the user's productive list."""
        self.custom_productive.add(app_name.lower())
    
    def add_unproductive_app(self, app_name: str):
        """Add an app to the user's unproductive list."""
        self.custom_unproductive.add(app_name.lower())
    
    def classify(self, app_name: str, window_title: str, 
                 app_duration_seconds: float) -> LocalClassification:
        """
        Attempt to classify activity locally.
        
        Args:
            app_name: Name of the application
            window_title: Title of the window
            app_duration_seconds: How long spent on this app in current period
        
        Returns:
            LocalClassification with intent, confidence, and cloud verification flag
        """
        app_lower = app_name.lower()
        title_lower = window_title.lower()
        
        # Check custom user lists first (highest priority)
        if app_lower in self.custom_productive:
            return LocalClassification(
                intent=ActivityIntent.PRODUCTIVE,
                confidence=0.95,
                reasoning=f"'{app_name}' is in your custom productive apps list",
                needs_cloud_verification=False
            )
        
        if app_lower in self.custom_unproductive:
            return LocalClassification(
                intent=ActivityIntent.UNPRODUCTIVE,
                confidence=0.95,
                reasoning=f"'{app_name}' is in your custom unproductive apps list",
                needs_cloud_verification=False
            )
        
        # Check default productive apps
        if app_lower in self.PRODUCTIVE_APPS:
            # High confidence for code editors
            if any(kw in app_lower for kw in ["code", "studio", "pycharm", "intellij"]):
                return LocalClassification(
                    intent=ActivityIntent.PRODUCTIVE,
                    confidence=0.92,
                    reasoning=f"'{app_name}' is a development tool",
                    needs_cloud_verification=False
                )
            # Medium-high confidence for other productive apps
            return LocalClassification(
                intent=ActivityIntent.PRODUCTIVE,
                confidence=0.85,
                reasoning=f"'{app_name}' is typically used for work",
                needs_cloud_verification=False
            )
        
        # Check default unproductive apps
        if app_lower in self.UNPRODUCTIVE_APPS:
            # Check if it might be work-related based on duration
            # Short breaks are okay; long sessions might be problematic
            if app_duration_seconds < 300:  # Less than 5 minutes
                return LocalClassification(
                    intent=ActivityIntent.NEUTRAL,
                    confidence=0.70,
                    reasoning=f"Short break on '{app_name}' - seems like a normal pause",
                    needs_cloud_verification=True  # Let cloud verify if this is okay
                )
            return LocalClassification(
                intent=ActivityIntent.UNPRODUCTIVE,
                confidence=0.80,
                reasoning=f"Extended time ({app_duration_seconds/60:.1f} min) on '{app_name}'",
                needs_cloud_verification=True  # Cloud should confirm before nudging
            )
        
        # Browser - depends heavily on what they're viewing
        if app_lower in self.NEUTRAL_APPS or "chrome" in app_lower or "firefox" in app_lower:
            return self._classify_by_window_title(app_name, title_lower)
        
        # Unknown app - send to cloud
        return LocalClassification(
            intent=ActivityIntent.UNKNOWN,
            confidence=0.0,
            reasoning=f"Unknown app '{app_name}' - needs cloud analysis",
            needs_cloud_verification=True
        )
    
    def _classify_by_window_title(self, app_name: str, 
                                   title_lower: str) -> LocalClassification:
        """
        Classify based on window title keywords.
        Used primarily for browsers and neutral apps.
        """
        # Count productive vs distraction keywords
        productive_matches = sum(1 for kw in self.PRODUCTIVE_KEYWORDS if kw in title_lower)
        distraction_matches = sum(1 for kw in self.DISTRACTION_KEYWORDS if kw in title_lower)
        
        if productive_matches > distraction_matches and productive_matches > 0:
            confidence = min(0.75 + (productive_matches * 0.05), 0.90)
            return LocalClassification(
                intent=ActivityIntent.PRODUCTIVE,
                confidence=confidence,
                reasoning=f"Window title suggests productive work (found {productive_matches} work-related keywords)",
                needs_cloud_verification=confidence < 0.85
            )
        
        if distraction_matches > productive_matches and distraction_matches > 0:
            confidence = min(0.70 + (distraction_matches * 0.05), 0.85)
            return LocalClassification(
                intent=ActivityIntent.UNPRODUCTIVE,
                confidence=confidence,
                reasoning=f"Window title suggests distraction (found {distraction_matches} distraction keywords)",
                needs_cloud_verification=True  # Always verify before labeling unproductive
            )
        
        # Can't determine from title
        return LocalClassification(
            intent=ActivityIntent.NEUTRAL,
            confidence=0.50,
            reasoning=f"Cannot determine intent from '{app_name}' - title ambiguous",
            needs_cloud_verification=True
        )
    
    def classify_summary(self, app_breakdown: Dict[str, float], 
                         top_windows: List[str]) -> LocalClassification:
        """
        Classify an entire activity summary.
        
        Args:
            app_breakdown: Dict of app_name -> seconds spent
            top_windows: List of window titles for context
        
        Returns:
            Overall classification for the period
        """
        if not app_breakdown:
            return LocalClassification(
                intent=ActivityIntent.UNKNOWN,
                confidence=0.0,
                reasoning="No activity data to classify",
                needs_cloud_verification=True
            )
        
        total_time = sum(app_breakdown.values())
        productive_time = 0.0
        unproductive_time = 0.0
        
        # Classify each app
        for app_name, duration in app_breakdown.items():
            classification = self.classify(
                app_name, 
                top_windows[0] if top_windows else "",
                duration
            )
            
            if classification.intent == ActivityIntent.PRODUCTIVE:
                productive_time += duration
            elif classification.intent == ActivityIntent.UNPRODUCTIVE:
                unproductive_time += duration
        
        # Calculate ratios
        productive_ratio = productive_time / total_time if total_time > 0 else 0
        unproductive_ratio = unproductive_time / total_time if total_time > 0 else 0
        
        # Determine overall intent
        if productive_ratio > 0.7:
            return LocalClassification(
                intent=ActivityIntent.PRODUCTIVE,
                confidence=min(productive_ratio, 0.90),
                reasoning=f"{productive_ratio*100:.0f}% of time on productive apps",
                needs_cloud_verification=False
            )
        
        if unproductive_ratio > 0.5:
            return LocalClassification(
                intent=ActivityIntent.UNPRODUCTIVE,
                confidence=min(unproductive_ratio, 0.85),
                reasoning=f"{unproductive_ratio*100:.0f}% of time on potentially distracting apps",
                needs_cloud_verification=True  # Verify before nudging
            )
        
        return LocalClassification(
            intent=ActivityIntent.NEUTRAL,
            confidence=0.60,
            reasoning=f"Mixed activity: {productive_ratio*100:.0f}% productive, {unproductive_ratio*100:.0f}% distraction",
            needs_cloud_verification=True
        )


# Quick test
if __name__ == "__main__":
    classifier = LocalClassifier(user_goals=["coding", "learning"])
    
    test_cases = [
        ("Visual Studio Code", "main.py - KairosAgent", 600),
        ("Google Chrome", "YouTube - Funny Cat Videos", 300),
        ("Google Chrome", "Stack Overflow - Python async", 180),
        ("Slack", "team-engineering", 120),
        ("Spotify", "Focus Playlist", 1800),
    ]
    
    print("Local Classification Tests:")
    print("-" * 60)
    for app, title, duration in test_cases:
        result = classifier.classify(app, title, duration)
        print(f"App: {app}")
        print(f"  Intent: {result.intent.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Reasoning: {result.reasoning}")
        print(f"  Needs Cloud: {result.needs_cloud_verification}")
        print()
