# Kairos Agent - Google Cloud Deployment Guide

Complete guide to deploying Kairos Agent to Google Cloud Run with Vertex AI.

## 🚀 Quick Deploy (Recommended)

### Option 1: Automated PowerShell Script

```powershell
# Run the automated deployment script
.\deploy.ps1

# Or specify custom parameters
.\deploy.ps1 -ProjectId "your-project-id" -Region "us-central1"
```

This script will:
- ✅ Check prerequisites
- ✅ Enable required APIs
- ✅ Deploy to Cloud Run
- ✅ Configure environment variables
- ✅ Test the deployment
- ✅ Create local .env file

---

## 📋 Manual Deployment

### Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and authenticated
3. **Project with Owner/Editor permissions**

### Step 1: Install Google Cloud SDK

**Windows:**
```powershell
# Download and install from:
# https://cloud.google.com/sdk/docs/install

# Or use chocolatey:
choco install gcloudsdk

# Authenticate
gcloud auth login
gcloud auth application-default login
```

**Verify installation:**
```powershell
gcloud --version
```

### Step 2: Set Up Google Cloud Project

```powershell
# List your projects
gcloud projects list

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Verify current configuration
gcloud config list
```

### Step 3: Enable Required APIs

```powershell
# Enable all required APIs
gcloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    aiplatform.googleapis.com `
    artifactregistry.googleapis.com
```

Wait 1-2 minutes for APIs to be fully enabled.

### Step 4: Deploy Cloud Service

```powershell
# Navigate to cloud service directory
cd cloud_service

# Deploy to Cloud Run (this will build and deploy)
gcloud run deploy kairos-agent `
    --source . `
    --region us-central1 `
    --platform managed `
    --allow-unauthenticated `
    --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID `
    --set-env-vars GOOGLE_CLOUD_REGION=us-central1 `
    --set-env-vars CLOUD_MODE=true `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 3 `
    --timeout 60

# This will take 5-10 minutes
```

### Step 5: Get Service URL

```powershell
# Get the deployed service URL
gcloud run services describe kairos-agent `
    --region us-central1 `
    --format "value(status.url)"

# Save this URL - you'll need it for the local agent
```

### Step 6: Test the Deployment

```powershell
# Test health endpoint (replace URL with your service URL)
$serviceUrl = "https://kairos-agent-xxxxx.run.app"

Invoke-RestMethod -Uri "$serviceUrl/health" -Method Get

# Expected response:
# {
#   "status": "healthy",
#   "service": "kairos-cloud-agent",
#   "version": "1.0.0",
#   "vertex_ai_available": true
# }
```

### Step 7: Test Analysis Endpoint

```powershell
# Create test request
$testRequest = @{
    activity_summary = @{
        period_start = "2026-01-02T10:00:00"
        period_end = "2026-01-02T10:05:00"
        total_duration_seconds = 300
        app_breakdown = @{
            "Visual Studio Code" = 200
            "YouTube" = 100
        }
        top_windows = @("main.py")
        activity_switches = 3
    }
    user_goals = @("coding")
} | ConvertTo-Json -Depth 10

# Test analysis endpoint
Invoke-RestMethod `
    -Uri "$serviceUrl/analyze" `
    -Method Post `
    -ContentType "application/json" `
    -Body $testRequest
```

---

## 🔧 Configure Local Agent

### Step 1: Create .env File

Copy `.env.example` to `.env` and update:

```bash
# .env file
CLOUD_MODE=true
PROJECT_ID=your-project-id
LOCATION=us-central1

# Your Cloud Run service URL
CLOUD_SERVICE_URL=https://kairos-agent-xxxxx.run.app

# Your goals
USER_GOALS=coding,learning,writing

# Production mode
DEMO_MODE=false
```

### Step 2: Install Local Dependencies

```powershell
cd local_agent
pip install -r requirements.txt
```

### Step 3: Run Local Agent

```powershell
# Run the local agent
python main.py

# The agent will:
# 1. Track Windows activity
# 2. Send summaries to Cloud Run
# 3. Receive Gemini-powered decisions
# 4. Nudge you when needed
```

---

## 🎨 Run the UI (Optional)

```powershell
cd ui

# Install dependencies
npm install

# Update vite.config.js proxy if needed
# (should point to local agent at http://localhost:5000)

# Start dev server
npm run dev

# Open http://localhost:3000
```

---

## 📊 Monitor and Manage

### View Logs

```powershell
# Stream real-time logs
gcloud run logs tail kairos-agent --region us-central1

# View recent logs
gcloud run logs read kairos-agent --region us-central1 --limit 50
```

### View Metrics

```powershell
# Open Cloud Run console
Start-Process "https://console.cloud.google.com/run"

# Navigate to: kairos-agent → Metrics
```

### Update Service

```powershell
# After making code changes, redeploy:
cd cloud_service
gcloud run deploy kairos-agent --source . --region us-central1
```

### Delete Service

```powershell
# Delete Cloud Run service
gcloud run services delete kairos-agent --region us-central1

# Delete container images (optional)
gcloud artifacts repositories list
```

---

## 💰 Cost Management

### Current Configuration
- **Memory**: 512Mi
- **CPU**: 1
- **Min instances**: 0 (scales to zero when not in use)
- **Max instances**: 3

### Expected Costs (Solo Developer, 8hrs/day)

| Component | Usage | Est. Cost/Month |
|-----------|-------|-----------------|
| Cloud Run | ~50 requests/day | $0-2 |
| Vertex AI | ~50 Gemini calls/day | $5-15 |
| **Total** | | **~$5-17** |

### Cost Optimization Tips

1. **Scale to Zero**: Default min-instances=0 means no cost when idle
2. **Request Batching**: Local agent batches 5-minute summaries
3. **Local Classification**: Reduces cloud calls by ~30%
4. **Set Budgets**: Set up billing alerts in GCP console

```powershell
# Set up budget alert (optional)
gcloud billing budgets create `
    --billing-account=YOUR_BILLING_ACCOUNT `
    --display-name="Kairos Agent Budget" `
    --budget-amount=20USD `
    --threshold-rule=percent=50 `
    --threshold-rule=percent=90
```

---

## 🔒 Security Best Practices

### 1. Restrict Access (Production)

```powershell
# Remove public access
gcloud run services update kairos-agent `
    --region us-central1 `
    --no-allow-unauthenticated

# Use service account for local agent authentication
```

### 2. Use Secret Manager (for sensitive data)

```powershell
# Create secret
echo -n "your-api-key" | gcloud secrets create api-key --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding api-key `
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" `
    --role="roles/secretmanager.secretAccessor"
```

### 3. Enable Cloud Armor (DDoS protection)

```powershell
# Enable Cloud Armor for production
# See: https://cloud.google.com/armor/docs
```

---

## 🐛 Troubleshooting

### Issue: "Vertex AI not available"

**Check:**
```powershell
# Verify API is enabled
gcloud services list --enabled | Select-String "aiplatform"

# Check service account permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID
```

**Solution:**
- Ensure `aiplatform.googleapis.com` is enabled
- Grant "Vertex AI User" role to Cloud Run service account

### Issue: "Permission denied"

**Solution:**
```powershell
# Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID `
    --member="user:YOUR_EMAIL" `
    --role="roles/run.admin"
```

### Issue: "Build failed"

**Check:**
```powershell
# View build logs
gcloud builds list --limit=5
gcloud builds log BUILD_ID
```

**Common causes:**
- Missing dependencies in requirements.txt
- Syntax errors in code
- Cloud Build API not enabled

### Issue: "Service returns 500 errors"

**Debug:**
```powershell
# Check logs
gcloud run logs read kairos-agent --region us-central1 --limit 50

# Look for stack traces and error messages
```

---

## 🎯 Next Steps After Deployment

1. ✅ **Test end-to-end**: Run local agent → verify cloud calls → check UI
2. ✅ **Set up monitoring**: Configure Cloud Monitoring alerts
3. ✅ **Customize goals**: Update USER_GOALS in .env
4. ✅ **Fine-tune nudging**: Adjust NudgeManager settings in local_agent/main.py
5. ✅ **Share feedback**: Report issues on GitHub

---

## 📚 Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vertex AI Gemini Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Kairos Agent GitHub](https://github.com/roshcr6/Kairos)

---

## 🆘 Need Help?

- **Documentation**: Check README.md and DEPLOYMENT.md
- **Logs**: Use `gcloud run logs` for debugging
- **Support**: Open GitHub issue with logs and error messages

---

**Happy deploying! 🚀**
