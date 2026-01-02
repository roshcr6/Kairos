# Kairos Agent - Google Cloud Deployment Script
# ==============================================
# This script automates the deployment of Kairos Agent to Google Cloud Run
# 
# Prerequisites:
# 1. Google Cloud SDK (gcloud) installed
# 2. Active GCP project with billing enabled
# 3. Owner/Editor permissions on the project

param(
    [Parameter(Mandatory=$false)]
    [string]$ProjectId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-central1",
    
    [Parameter(Mandatory=$false)]
    [string]$ServiceName = "kairos-agent"
)

# Color output functions
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

# Banner
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "║   🕐 KAIROS AGENT - Google Cloud Deployment                  ║" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check prerequisites
Write-Info "📋 Step 1: Checking prerequisites..."

# Check if gcloud is installed
try {
    $gcloudVersion = gcloud version --format="value(version)" 2>$null
    Write-Success "✅ Google Cloud SDK installed: $gcloudVersion"
} catch {
    Write-Error "❌ Google Cloud SDK not found!"
    Write-Info "Please install from: https://cloud.google.com/sdk/docs/install"
    exit 1
}

# Get or prompt for project ID
if ([string]::IsNullOrEmpty($ProjectId)) {
    $currentProject = gcloud config get-value project 2>$null
    if ($currentProject) {
        Write-Info "Current GCP project: $currentProject"
        $useCurrentProject = Read-Host "Use this project? (y/n)"
        if ($useCurrentProject -eq 'y') {
            $ProjectId = $currentProject
        } else {
            $ProjectId = Read-Host "Enter your GCP Project ID"
        }
    } else {
        $ProjectId = Read-Host "Enter your GCP Project ID"
    }
}

Write-Info "🎯 Using Project ID: $ProjectId"
Write-Info "🌎 Using Region: $Region"

# Step 2: Set project
Write-Info "`n📦 Step 2: Setting up project..."
gcloud config set project $ProjectId
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Failed to set project. Please verify project ID and permissions."
    exit 1
}
Write-Success "✅ Project configured"

# Step 3: Enable required APIs
Write-Info "`n🔧 Step 3: Enabling required Google Cloud APIs..."
Write-Info "This may take a few minutes..."

$apis = @(
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com"
)

foreach ($api in $apis) {
    Write-Info "  Enabling $api..."
    gcloud services enable $api --project=$ProjectId 2>$null
}

Write-Success "✅ APIs enabled"

# Step 4: Deploy to Cloud Run
Write-Info "`n🚀 Step 4: Deploying to Cloud Run..."
Write-Info "This will build and deploy your service. It may take 5-10 minutes..."

Push-Location cloud_service

try {
    gcloud run deploy $ServiceName `
        --source . `
        --region $Region `
        --platform managed `
        --allow-unauthenticated `
        --set-env-vars "GOOGLE_CLOUD_PROJECT=$ProjectId" `
        --set-env-vars "GOOGLE_CLOUD_REGION=$Region" `
        --set-env-vars "CLOUD_MODE=true" `
        --memory 512Mi `
        --cpu 1 `
        --min-instances 0 `
        --max-instances 3 `
        --timeout 60
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Deployment failed!"
        Pop-Location
        exit 1
    }
    
    Write-Success "✅ Cloud Run service deployed!"
    
} finally {
    Pop-Location
}

# Step 5: Get service URL
Write-Info "`n🔗 Step 5: Getting service URL..."
$serviceUrl = gcloud run services describe $ServiceName `
    --region $Region `
    --format "value(status.url)" 2>$null

if ([string]::IsNullOrEmpty($serviceUrl)) {
    Write-Error "❌ Could not retrieve service URL"
    exit 1
}

Write-Success "✅ Service URL: $serviceUrl"

# Step 6: Test the deployment
Write-Info "`n🧪 Step 6: Testing deployment..."

try {
    $healthCheck = Invoke-RestMethod -Uri "$serviceUrl/health" -Method Get -TimeoutSec 10
    if ($healthCheck.status -eq "healthy") {
        Write-Success "✅ Service is healthy!"
        Write-Success "   Vertex AI Available: $($healthCheck.vertex_ai_available)"
    } else {
        Write-Warning "⚠️  Service responded but may not be fully healthy"
    }
} catch {
    Write-Warning "⚠️  Health check failed: $_"
    Write-Info "The service may still be initializing. Try the health check manually:"
    Write-Info "   curl $serviceUrl/health"
}

# Step 7: Create local .env file
Write-Info "`n📝 Step 7: Creating local configuration..."

$envContent = @"
# Kairos Agent - Environment Configuration
# Generated on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# ============================================================
# CLOUD MODE CONFIGURATION
# ============================================================
CLOUD_MODE=true

# ============================================================
# GOOGLE CLOUD CONFIGURATION
# ============================================================
PROJECT_ID=$ProjectId
LOCATION=$Region

# ============================================================
# LOCAL AGENT CONFIGURATION
# ============================================================

# Cloud Run service URL
CLOUD_SERVICE_URL=$serviceUrl

# Your productivity goals (customize as needed)
USER_GOALS=coding,learning,writing

# Demo mode (set to false for production)
DEMO_MODE=false

# ============================================================
# OPTIONAL CONFIGURATION
# ============================================================
DEBUG=false
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8
Write-Success "✅ Created .env file with deployment configuration"

# Summary
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                                                               ║" -ForegroundColor Green
Write-Host "║   ✅ DEPLOYMENT SUCCESSFUL!                                   ║" -ForegroundColor Green
Write-Host "║                                                               ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Info "📋 Deployment Summary:"
Write-Info "  • Project: $ProjectId"
Write-Info "  • Region: $Region"
Write-Info "  • Service: $ServiceName"
Write-Info "  • URL: $serviceUrl"
Write-Host ""

Write-Info "🎯 Next Steps:"
Write-Info ""
Write-Info "1. Test the cloud service:"
Write-Info "   Invoke-RestMethod -Uri '$serviceUrl/health' -Method Get"
Write-Host ""

Write-Info "2. Run the local agent:"
Write-Info "   cd local_agent"
Write-Info "   python main.py"
Write-Host ""

Write-Info "3. Start the UI (optional):"
Write-Info "   cd ui"
Write-Info "   npm install"
Write-Info "   npm run dev"
Write-Host ""

Write-Info "4. View Cloud Run logs:"
Write-Info "   gcloud run logs read $ServiceName --region $Region --limit 50"
Write-Host ""

Write-Success "🎉 Your Kairos Agent is now running in the cloud!"
Write-Host ""

# Offer to open Cloud Run console
$openConsole = Read-Host "Open Cloud Run console in browser? (y/n)"
if ($openConsole -eq 'y') {
    Start-Process "https://console.cloud.google.com/run/detail/$Region/$ServiceName/metrics?project=$ProjectId"
}
