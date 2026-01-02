# Kairos Agent - Cloud Run Deployment Guide
# ==========================================
# Step-by-step instructions for deploying to Google Cloud Run

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Vertex AI API** enabled in your project

## Quick Setup (5 minutes)

### Step 1: Enable Required APIs

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com
```

### Step 2: Deploy to Cloud Run

```bash
cd cloud_service

# Deploy directly from source (Cloud Build handles Docker)
gcloud run deploy kairos-agent \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID \
    --set-env-vars GOOGLE_CLOUD_REGION=us-central1 \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 3
```

### Step 3: Get Service URL

```bash
# Get the deployed URL
gcloud run services describe kairos-agent \
    --region us-central1 \
    --format 'value(status.url)'
```

### Step 4: Test the Deployment

```bash
# Health check
curl https://YOUR-SERVICE-URL.run.app/health

# Test analysis
curl -X POST https://YOUR-SERVICE-URL.run.app/analyze \
    -H "Content-Type: application/json" \
    -d '{
        "activity_summary": {
            "period_start": "2026-01-02T10:00:00",
            "period_end": "2026-01-02T10:05:00",
            "total_duration_seconds": 300,
            "app_breakdown": {"Visual Studio Code": 200, "YouTube": 100},
            "top_windows": ["main.py"],
            "activity_switches": 3
        },
        "user_goals": ["coding"]
    }'
```

## Running the Local Agent

### Step 1: Install Dependencies

```bash
cd local_agent
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Windows PowerShell
$env:CLOUD_SERVICE_URL = "https://YOUR-SERVICE-URL.run.app"
$env:USER_GOALS = "coding,learning,writing"

# Or create a .env file in local_agent/
```

### Step 3: Run the Agent

```bash
# Production mode (requires Windows APIs + Cloud Service)
python main.py

# Demo mode (no dependencies required)
python main.py --demo

# Time-limited demo (60 seconds)
python main.py --demo --duration=60
```

## Demo Mode (No Cloud Required)

For testing without GCP:

```bash
# Terminal 1: Run cloud service locally
cd cloud_service
$env:DEMO_MODE = "true"
python main.py

# Terminal 2: Run local agent
cd local_agent
$env:DEMO_MODE = "true"
$env:CLOUD_SERVICE_URL = "http://localhost:8080"
python main.py
```

## Architecture Notes

### Why Cloud Run?
- **Stateless**: Each request is independent (perfect for serverless)
- **Scale to Zero**: No cost when not in use
- **Fast Cold Start**: Gemini calls are the bottleneck, not startup
- **Managed**: No infrastructure to maintain

### Why Vertex AI (Gemini)?
- **Google Native**: Best integration with Cloud Run
- **Powerful Reasoning**: Gemini 1.5 Flash is fast and capable
- **Structured Output**: JSON response mode for reliable parsing
- **Cost Effective**: Pay per token, not per deployment

### Privacy Architecture
```
[Windows PC]                    [Cloud Run]                [Vertex AI]
     |                               |                          |
  Raw Data                      Summaries                   Prompts
     |                               |                          |
  (never leaves)              (aggregated only)          (no PII)
     v                               v                          v
[Activity Tracker] --> [Summary] --> [FastAPI] --> [Gemini] --> [Decision]
```

## Troubleshooting

### "Vertex AI not available"
- Check `GOOGLE_CLOUD_PROJECT` is set correctly
- Ensure Vertex AI API is enabled
- Verify service account has `Vertex AI User` role

### "Cloud service unreachable"
- Check `CLOUD_SERVICE_URL` is correct
- Verify Cloud Run service is deployed and healthy
- Check network/firewall settings

### "Windows APIs not available"
- Ensure running on Windows 10/11
- Install pywin32: `pip install pywin32`
- Run as administrator if needed

## Cost Estimation

For a solo developer using Kairos 8 hours/day:

| Component | Usage | Est. Cost/Month |
|-----------|-------|-----------------|
| Cloud Run | ~50 requests/day | $0-2 |
| Vertex AI | ~50 Gemini calls/day | $5-15 |
| **Total** | | **~$5-17** |

*Actual costs depend on usage patterns and token counts.*
