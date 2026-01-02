"""
Kairos Agent - Local Activity Tracker
=====================================
Monitors foreground windows on Windows to track user activity.
Privacy-first: Only captures app names and window titles, not content.

Author: Kairos Team - AgentX Hackathon 2026
"""

import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from collections import defaultdict
import os

# Windows-specific imports - always try to import
try:
    import win32gui
    import win32process
    import psutil
    WINDOWS_AVAILABLE = True
except ImportError:
    logging.warning("Windows APIs not available (win32gui, win32process, psutil). Install with: pip install pywin32 psutil")
    WINDOWS_AVAILABLE = False


def is_demo_mode() -> bool:
    """Check if demo mode is enabled (checked dynamically each call)."""
    return os.getenv("DEMO_MODE", "false").lower() == "true"


logger = logging.getLogger(__name__)

# Mapping of process names to friendly app names
APP_NAME_MAP = {
    "Taskmgr": "Task Manager",
    "explorer": "File Explorer",
    "ApplicationFrameHost": "Windows App",
    "SystemSettings": "Windows Settings",
    "ShellExperienceHost": "Windows Shell",
    "SearchHost": "Windows Search",
    "StartMenuExperienceHost": "Start Menu",
    "TextInputHost": "Windows Input",
    "WindowsTerminal": "Windows Terminal",
    "cmd": "Command Prompt",
    "powershell": "PowerShell",
    "pwsh": "PowerShell",
    "Code": "Visual Studio Code",
    "devenv": "Visual Studio",
    "chrome": "Google Chrome",
    "msedge": "Microsoft Edge",
    "firefox": "Firefox",
    "OUTLOOK": "Outlook",
    "WINWORD": "Microsoft Word",
    "EXCEL": "Microsoft Excel",
    "POWERPNT": "PowerPoint",
    "notepad": "Notepad",
    "mspaint": "Paint",
    "SnippingTool": "Snipping Tool",
    "Spotify": "Spotify",
    "Discord": "Discord",
    "Slack": "Slack",
    "Teams": "Microsoft Teams",
    "ms-teams": "Microsoft Teams",
}


@dataclass
class ActivityWindow:
    """Represents a single window activity observation."""
    app_name: str
    window_title: str
    timestamp: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0


@dataclass
class ActivitySummary:
    """
    Aggregated activity summary for a time period.
    This is what gets sent to the cloud - NOT raw window data.
    """
    period_start: datetime
    period_end: datetime
    total_duration_seconds: float
    app_breakdown: Dict[str, float]  # app_name -> seconds
    top_windows: List[str]  # Top 5 window titles (for context, anonymized)
    activity_switches: int  # How often user switched apps
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for cloud transmission."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_duration_seconds": self.total_duration_seconds,
            "app_breakdown": self.app_breakdown,
            "top_windows": self.top_windows,
            "activity_switches": self.activity_switches
        }


class ActivityTracker:
    """
    Tracks foreground window activity on Windows.
    
    Design Decisions:
    - Polls every 2 seconds (balance between accuracy and resource usage)
    - Aggregates into 5-minute summaries before sending anywhere
    - Never captures actual screen content, only metadata
    """
    
    POLL_INTERVAL = 2.0  # seconds
    SUMMARY_INTERVAL = 300  # 5 minutes
    
    def __init__(self):
        self.current_activity: Optional[ActivityWindow] = None
        self.activity_history: List[ActivityWindow] = []
        self.app_durations: Dict[str, float] = defaultdict(float)
        self.window_titles: List[str] = []
        self.switch_count = 0
        self.period_start = datetime.now()
        
        # Demo mode data for testing without Windows APIs
        self._demo_apps = [
            ("Visual Studio Code", "main.py - KairosAgent"),
            ("Google Chrome", "Stack Overflow - Python async"),
            ("Slack", "team-engineering"),
            ("Visual Studio Code", "agent.py - KairosAgent"),
            ("Spotify", "Focus Flow Playlist"),
            ("Google Chrome", "YouTube - Cat Videos"),  # Distraction!
            ("Visual Studio Code", "README.md - KairosAgent"),
            ("Microsoft Teams", "Standup Meeting"),
        ]
        self._demo_index = 0
    
    def get_foreground_window(self) -> Optional[ActivityWindow]:
        """
        Get the current foreground window info.
        Returns None if unable to detect (e.g., locked screen).
        """
        # Check dynamically if we should use demo mode
        if is_demo_mode() or not WINDOWS_AVAILABLE:
            return self._get_demo_window()
        
        try:
            # Get foreground window handle
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
            
            # Get window title
            window_title = win32gui.GetWindowText(hwnd)
            if not window_title:
                return None
            
            # Get process name
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                raw_name = process.name().replace('.exe', '')
                
                # Map to friendly name if available
                app_name = APP_NAME_MAP.get(raw_name, raw_name)
                
                # For UWP apps (ApplicationFrameHost), try to get real app from window title
                if raw_name == "ApplicationFrameHost" and window_title:
                    # Common UWP apps detection from title
                    title_lower = window_title.lower()
                    if "calculator" in title_lower:
                        app_name = "Calculator"
                    elif "settings" in title_lower:
                        app_name = "Windows Settings"
                    elif "store" in title_lower:
                        app_name = "Microsoft Store"
                    elif "photos" in title_lower:
                        app_name = "Photos"
                    elif "mail" in title_lower:
                        app_name = "Mail"
                    elif "calendar" in title_lower:
                        app_name = "Calendar"
                    else:
                        # Use first word of title as app name
                        app_name = window_title.split(' - ')[0].split(' ')[0] or "Windows App"
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app_name = "Unknown"
            
            return ActivityWindow(
                app_name=app_name,
                window_title=self._sanitize_title(window_title)
            )
            
        except Exception as e:
            logger.warning(f"Failed to get foreground window: {e}")
            return None
    
    def _get_demo_window(self) -> ActivityWindow:
        """Generate demo data for testing without Windows APIs."""
        app_name, title = self._demo_apps[self._demo_index % len(self._demo_apps)]
        # Rotate through demo apps, simulating real usage
        if time.time() % 10 < 2:  # Change app every ~10 seconds in demo
            self._demo_index += 1
        return ActivityWindow(app_name=app_name, window_title=title)
    
    def _sanitize_title(self, title: str) -> str:
        """
        Remove potentially sensitive info from window titles.
        E.g., email addresses, file paths with usernames.
        """
        # Basic sanitization - in production, would be more thorough
        import re
        # Remove email-like patterns
        title = re.sub(r'[\w\.-]+@[\w\.-]+', '[email]', title)
        # Remove file paths (keep just filename)
        title = re.sub(r'[A-Za-z]:\\(?:[^\\]+\\)*', '', title)
        return title[:100]  # Truncate long titles
    
    def record_activity(self) -> bool:
        """
        Record current foreground window.
        Returns True if activity changed (app switch detected).
        """
        new_activity = self.get_foreground_window()
        if not new_activity:
            return False
        
        activity_changed = False
        
        if self.current_activity:
            # Calculate duration for previous activity
            duration = (new_activity.timestamp - self.current_activity.timestamp).total_seconds()
            self.current_activity.duration_seconds = duration
            self.app_durations[self.current_activity.app_name] += duration
            
            # Check if app changed
            if self.current_activity.app_name != new_activity.app_name:
                activity_changed = True
                self.switch_count += 1
                self.activity_history.append(self.current_activity)
                
                # Keep track of unique window titles (for context)
                if self.current_activity.window_title not in self.window_titles:
                    self.window_titles.append(self.current_activity.window_title)
        
        self.current_activity = new_activity
        return activity_changed
    
    def should_generate_summary(self) -> bool:
        """Check if enough time has passed to generate a summary."""
        elapsed = (datetime.now() - self.period_start).total_seconds()
        return elapsed >= self.SUMMARY_INTERVAL
    
    def generate_summary(self) -> ActivitySummary:
        """
        Generate an aggregated summary of recent activity.
        This summary is what gets sent to the cloud - privacy preserved.
        """
        now = datetime.now()
        
        # Finalize current activity duration
        if self.current_activity:
            duration = (now - self.current_activity.timestamp).total_seconds()
            self.app_durations[self.current_activity.app_name] += duration
        
        summary = ActivitySummary(
            period_start=self.period_start,
            period_end=now,
            total_duration_seconds=(now - self.period_start).total_seconds(),
            app_breakdown=dict(self.app_durations),
            top_windows=self.window_titles[:5],  # Only top 5 for privacy
            activity_switches=self.switch_count
        )
        
        # Reset for next period
        self._reset_period()
        
        logger.info(f"Generated summary: {len(summary.app_breakdown)} apps, "
                   f"{summary.activity_switches} switches")
        
        return summary
    
    def _reset_period(self):
        """Reset tracking for a new summary period."""
        self.period_start = datetime.now()
        self.app_durations = defaultdict(float)
        self.window_titles = []
        self.switch_count = 0
        self.activity_history = []


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tracker = ActivityTracker()
    
    print("Tracking activity for 30 seconds...")
    for _ in range(15):
        changed = tracker.record_activity()
        if changed:
            print(f"  Switched to: {tracker.current_activity.app_name}")
        time.sleep(2)
    
    summary = tracker.generate_summary()
    print(f"\nSummary: {summary.to_dict()}")
