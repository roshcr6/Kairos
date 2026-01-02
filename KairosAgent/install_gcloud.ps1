# Google Cloud SDK Installation Helper for Windows
# =================================================
# This script helps you install and configure Google Cloud SDK

param(
    [Parameter(Mandatory=$false)]
    [switch]$SkipInstall = $false
)

# Color output functions
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "║   Google Cloud SDK Installation Helper                       ║" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if gcloud is already installed
Write-Info "🔍 Checking if Google Cloud SDK is already installed..."
try {
    $gcloudPath = Get-Command gcloud -ErrorAction Stop
    $gcloudVersion = gcloud version --format="value(version)" 2>$null
    Write-Success "✅ Google Cloud SDK is already installed!"
    Write-Success "   Version: $gcloudVersion"
    Write-Success "   Path: $($gcloudPath.Source)"
    
    $reconfigure = Read-Host "`nWould you like to reconfigure it anyway? (y/n)"
    if ($reconfigure -ne 'y') {
        Write-Info "Skipping to configuration..."
        $SkipInstall = $true
    }
} catch {
    Write-Warning "⚠️  Google Cloud SDK not found in PATH"
    Write-Info "Let's install it now..."
}

if (-not $SkipInstall) {
    Write-Host ""
    Write-Info "📥 Installation Options:"
    Write-Host ""
    Write-Host "1. Download installer manually (Recommended)" -ForegroundColor Yellow
    Write-Host "2. Install via Chocolatey (if you have it installed)" -ForegroundColor Yellow
    Write-Host "3. Exit and install later" -ForegroundColor Yellow
    Write-Host ""
    
    $choice = Read-Host "Select an option (1-3)"
    
    switch ($choice) {
        "1" {
            Write-Info "`n📥 Opening Google Cloud SDK download page..."
            Start-Process "https://cloud.google.com/sdk/docs/install-sdk#windows"
            
            Write-Host ""
            Write-Info "Manual Installation Steps:"
            Write-Info "1. Download the installer from the opened webpage"
            Write-Info "2. Run the GoogleCloudSDKInstaller.exe"
            Write-Info "3. Follow the installation wizard"
            Write-Info "4. Make sure to check 'Add gcloud to PATH'"
            Write-Info "5. Restart your PowerShell terminal after installation"
            Write-Host ""
            Write-Warning "⚠️  After installation, close this terminal and open a NEW PowerShell window"
            Write-Warning "⚠️  Then run this script again to continue configuration"
            Write-Host ""
            Read-Host "Press Enter to exit..."
            exit 0
        }
        "2" {
            Write-Info "`n📦 Checking for Chocolatey..."
            try {
                $chocoVersion = choco --version 2>$null
                Write-Success "✅ Chocolatey found: $chocoVersion"
                
                Write-Info "`nInstalling Google Cloud SDK via Chocolatey..."
                Write-Warning "This requires administrator privileges"
                
                $confirm = Read-Host "Continue with Chocolatey installation? (y/n)"
                if ($confirm -eq 'y') {
                    # Check if running as admin
                    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
                    
                    if (-not $isAdmin) {
                        Write-Error "❌ This terminal is not running as Administrator"
                        Write-Info "Please run PowerShell as Administrator and try again"
                        Read-Host "Press Enter to exit..."
                        exit 1
                    }
                    
                    choco install gcloudsdk -y
                    
                    if ($LASTEXITCODE -eq 0) {
                        Write-Success "`n✅ Google Cloud SDK installed successfully!"
                        Write-Warning "⚠️  Please close this terminal and open a NEW PowerShell window"
                        Write-Warning "⚠️  Then run this script again to continue configuration"
                        Read-Host "Press Enter to exit..."
                        exit 0
                    } else {
                        Write-Error "❌ Installation failed"
                        Read-Host "Press Enter to exit..."
                        exit 1
                    }
                }
            } catch {
                Write-Error "❌ Chocolatey is not installed"
                Write-Info "Install Chocolatey from: https://chocolatey.org/install"
                Read-Host "Press Enter to exit..."
                exit 1
            }
        }
        "3" {
            Write-Info "Installation cancelled. You can install Google Cloud SDK manually from:"
            Write-Info "https://cloud.google.com/sdk/docs/install-sdk#windows"
            exit 0
        }
        default {
            Write-Error "Invalid option selected"
            exit 1
        }
    }
}

# Configuration section (runs if gcloud is already installed)
Write-Host ""
Write-Info "⚙️  Configuring Google Cloud SDK..."
Write-Host ""

# Step 1: Authenticate
Write-Info "Step 1: Authentication"
Write-Info "This will open a browser window for you to sign in to your Google account"
Write-Host ""
$auth = Read-Host "Would you like to authenticate now? (y/n)"

if ($auth -eq 'y') {
    Write-Info "Opening browser for authentication..."
    gcloud auth login
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✅ Authentication successful!"
    } else {
        Write-Error "❌ Authentication failed"
        exit 1
    }
    
    # Application default credentials (needed for Vertex AI)
    Write-Info "`nSetting up application default credentials..."
    gcloud auth application-default login
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "✅ Application default credentials configured!"
    } else {
        Write-Warning "⚠️  Application default credentials setup had issues"
    }
}

# Step 2: Project setup
Write-Host ""
Write-Info "Step 2: Project Configuration"
Write-Host ""

# List projects
Write-Info "Fetching your Google Cloud projects..."
$projects = gcloud projects list --format="value(projectId,name)" 2>$null

if ($projects) {
    Write-Success "Your Google Cloud Projects:"
    Write-Host ""
    $projectArray = $projects -split "`n"
    for ($i = 0; $i -lt $projectArray.Count; $i++) {
        if ($projectArray[$i]) {
            Write-Host "  $($i + 1). $($projectArray[$i])" -ForegroundColor Yellow
        }
    }
    Write-Host ""
    
    $useExisting = Read-Host "Would you like to use an existing project? (y/n)"
    
    if ($useExisting -eq 'y') {
        $projectNum = Read-Host "Enter project number (1-$($projectArray.Count))"
        $projectIndex = [int]$projectNum - 1
        
        if ($projectIndex -ge 0 -and $projectIndex -lt $projectArray.Count) {
            $selectedProject = ($projectArray[$projectIndex] -split "`t")[0]
            gcloud config set project $selectedProject
            Write-Success "✅ Project set to: $selectedProject"
        }
    } else {
        $createNew = Read-Host "Would you like to create a new project? (y/n)"
        if ($createNew -eq 'y') {
            $projectId = Read-Host "Enter a project ID (lowercase, numbers, hyphens only)"
            $projectName = Read-Host "Enter a project name"
            
            Write-Info "Creating project..."
            gcloud projects create $projectId --name="$projectName"
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "✅ Project created!"
                gcloud config set project $projectId
                
                Write-Warning "`n⚠️  IMPORTANT: You need to enable billing for this project"
                Write-Info "Opening billing page..."
                Start-Process "https://console.cloud.google.com/billing/linkedaccount?project=$projectId"
                Write-Host ""
                Read-Host "Press Enter after you've enabled billing..."
            }
        }
    }
} else {
    Write-Info "No projects found or unable to fetch projects"
    Write-Info "You can create a project in the Google Cloud Console:"
    Start-Process "https://console.cloud.google.com/projectcreate"
}

# Step 3: Verify configuration
Write-Host ""
Write-Info "📋 Current Configuration:"
Write-Host ""

$currentProject = gcloud config get-value project 2>$null
$currentAccount = gcloud config get-value account 2>$null

if ($currentAccount) {
    Write-Success "  Account: $currentAccount"
}
if ($currentProject) {
    Write-Success "  Project: $currentProject"
}

# Final summary
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                                                               ║" -ForegroundColor Green
Write-Host "║   ✅ Google Cloud SDK Setup Complete!                        ║" -ForegroundColor Green
Write-Host "║                                                               ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Info "🎯 Next Steps:"
Write-Info "1. Run the deployment script: .\deploy.ps1"
Write-Info "2. Or manually enable APIs: gcloud services enable run.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com"
Write-Host ""

$runDeploy = Read-Host "Would you like to run the deployment script now? (y/n)"
if ($runDeploy -eq 'y') {
    Write-Host ""
    .\deploy.ps1
}
