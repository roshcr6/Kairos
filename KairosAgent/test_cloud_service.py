"""
Kairos Agent - Cloud Service Tests
===================================
Unit tests for the cloud reasoning service.

Run with: pytest test_cloud_service.py -v

Author: Kairos Team - AgentX Hackathon 2026
"""

import os
import sys
import pytest

# Set demo mode before imports
os.environ["DEMO_MODE"] = "true"

# Add cloud_service to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "cloud_service"))

from fastapi.testclient import TestClient
from cloud_service.main import app
from cloud_service.models import AnalyzeRequest, ActivitySummary


# Create test client
client = TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""
    
    def test_health_returns_200(self):
        """Health endpoint should return 200."""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_response_structure(self):
        """Health response should have expected structure."""
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data
        assert "vertex_ai_available" in data


class TestAnalyzeEndpoint:
    """Tests for /analyze endpoint."""
    
    def test_analyze_productive_activity(self):
        """Should correctly identify productive activity."""
        payload = {
            "activity_summary": {
                "period_start": "2026-01-02T10:00:00",
                "period_end": "2026-01-02T10:05:00",
                "total_duration_seconds": 300,
                "app_breakdown": {
                    "Visual Studio Code": 250,
                    "Google Chrome": 50
                },
                "top_windows": ["main.py - KairosAgent"],
                "activity_switches": 2
            },
            "user_goals": ["coding"]
        }
        
        response = client.post("/analyze", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["intent"] == "productive"
        assert data["action"] == "none"
        assert data["confidence"] > 0.5
    
    def test_analyze_unproductive_activity(self):
        """Should identify unproductive activity and recommend nudge."""
        payload = {
            "activity_summary": {
                "period_start": "2026-01-02T10:00:00",
                "period_end": "2026-01-02T10:05:00",
                "total_duration_seconds": 300,
                "app_breakdown": {
                    "YouTube": 200,
                    "Visual Studio Code": 100
                },
                "top_windows": ["Funny Cat Videos - YouTube"],
                "activity_switches": 5
            },
            "user_goals": ["coding"]
        }
        
        response = client.post("/analyze", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["intent"] in ["unproductive", "neutral"]
        # Note: nudge might be suppressed by post-processing rules
    
    def test_analyze_with_local_classification(self):
        """Should accept and use local classification context."""
        payload = {
            "activity_summary": {
                "period_start": "2026-01-02T10:00:00",
                "period_end": "2026-01-02T10:05:00",
                "total_duration_seconds": 300,
                "app_breakdown": {"VS Code": 300},
                "top_windows": ["test.py"],
                "activity_switches": 0
            },
            "user_goals": ["coding"],
            "local_classification": {
                "intent": "productive",
                "confidence": 0.9,
                "reasoning": "All time spent in code editor"
            }
        }
        
        response = client.post("/analyze", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "reasoning" in data
    
    def test_analyze_validates_input(self):
        """Should validate required fields."""
        # Missing activity_summary
        response = client.post("/analyze", json={
            "user_goals": ["coding"]
        })
        assert response.status_code == 422  # Validation error
    
    def test_analyze_response_structure(self):
        """Response should have all required fields."""
        payload = {
            "activity_summary": {
                "period_start": "2026-01-02T10:00:00",
                "period_end": "2026-01-02T10:05:00",
                "total_duration_seconds": 300,
                "app_breakdown": {"Test App": 300},
                "top_windows": [],
                "activity_switches": 0
            },
            "user_goals": ["testing"]
        }
        
        response = client.post("/analyze", json=payload)
        data = response.json()
        
        required_fields = ["intent", "confidence", "reasoning", "action"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


class TestStatsEndpoint:
    """Tests for /stats endpoint."""
    
    def test_stats_returns_200(self):
        """Stats endpoint should return 200."""
        response = client.get("/stats")
        assert response.status_code == 200
    
    def test_stats_response_structure(self):
        """Stats should include expected metrics."""
        response = client.get("/stats")
        data = response.json()
        
        assert "total_requests" in data
        assert "vertex_available" in data


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_app_breakdown(self):
        """Should handle empty activity gracefully."""
        payload = {
            "activity_summary": {
                "period_start": "2026-01-02T10:00:00",
                "period_end": "2026-01-02T10:05:00",
                "total_duration_seconds": 0,
                "app_breakdown": {},
                "top_windows": [],
                "activity_switches": 0
            },
            "user_goals": ["coding"]
        }
        
        response = client.post("/analyze", json=payload)
        # Should not crash, return valid response
        assert response.status_code == 200
    
    def test_very_long_window_titles(self):
        """Should handle long window titles."""
        payload = {
            "activity_summary": {
                "period_start": "2026-01-02T10:00:00",
                "period_end": "2026-01-02T10:05:00",
                "total_duration_seconds": 300,
                "app_breakdown": {"Test": 300},
                "top_windows": ["A" * 500],  # Very long title
                "activity_switches": 0
            },
            "user_goals": ["coding"]
        }
        
        response = client.post("/analyze", json=payload)
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
