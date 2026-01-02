# Kairos Agent 🕐

**Autonomous Productivity AI Agent for Knowledge Workers**

Kairos Agent is an ethical, privacy-preserving productivity assistant that:
- Runs **autonomously** on your machine (no user input required)
- **Observes** activity passively (no keystrokes, no screenshots)
- **Summarizes** only (raw data never leaves your device)
- Uses **Google Cloud Run + Vertex AI (Gemini)** for intelligent reasoning
- **Nudges** users only when activity genuinely deviates from stated goals
- **Explains** every decision through a transparent, read-only UI

> ⚠️ **This is NOT surveillance software.** Kairos respects user autonomy and privacy by design.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          UI (React)                              │
│                    http://localhost:3000                         │
│              READ-ONLY: Explains, never controls                 │
└─────────────────────────────────────────────────────────────────┘
                              ↑ polls
┌─────────────────────────────────────────────────────────────────┐
│                    LOCAL AGENT (Windows)                         │
│                    http://localhost:5000                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Activity   │→ │  Classifier  │→ │    Cloud Client      │  │
│  │   Tracker    │  │   (Local)    │  │  (Sends Summaries)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                              ↓                                   │
│                    State Manager (for UI)                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTPS (Summaries Only)
┌─────────────────────────────────────────────────────────────────┐
│                    CLOUD RUN SERVICE (GCP)                       │
│                    http://localhost:8080                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   FastAPI    │→ │    Agent     │→ │   Vertex AI Client   │  │
│  │  /analyze    │  │    Loop      │  │   (Gemini 1.5)       │  │
│  │  /health     │  └──────────────┘  └──────────────────────┘  │
│  │  /status     │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Option 1: Full Demo (Recommended)

```bash
# Install Python dependencies
pip install httpx fastapi uvicorn pydantic psutil

# Run the demo (starts all services)
python demo.py
```

This will:
1. Start Cloud Service on http://localhost:8080
2. Start Local Agent API on http://localhost:5000
3. Start UI on http://localhost:3000 (if Node.js is available)
4. Open your browser to the UI

### Option 2: Manual Setup

**Terminal 1 - Cloud Service:**
```bash
cd cloud_service
pip install -r requirements.txt
set CLOUD_MODE=false
uvicorn main:app --reload --port 8080
```

**Terminal 2 - Local Agent:**
```bash
cd local_agent
pip install -r requirements.txt
set DEMO_MODE=true
python main.py
```

**Terminal 3 - UI (optional):**
```bash
cd ui
npm install
npm run dev
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLOUD_MODE` | Use real Vertex AI (`true`) or deterministic responses (`false`) | `true` |
| `PROJECT_ID` | Google Cloud Project ID | - |
| `LOCATION` | GCP Region | `us-central1` |
| `DEMO_MODE` | Simulate Windows activity | `false` |
| `USER_GOALS` | Comma-separated goals | `coding,learning` |

### For Production (Real Vertex AI)

```bash
set CLOUD_MODE=true
set PROJECT_ID=your-gcp-project
set LOCATION=us-central1
```

### For Demo (No GCP Required)

```bash
set CLOUD_MODE=false
set DEMO_MODE=true
```

## 🔒 Privacy Principles

1. **Summaries, Not Surveillance**: Only aggregated activity data leaves your machine
2. **No Screenshots by Default**: Visual capture is opt-in and processed locally
3. **Delayed Decisions**: Agent waits before nudging to avoid false positives
4. **User Goals First**: Nudges only happen when activity contradicts stated goals
5. **Transparent Reasoning**: Every decision includes human-readable explanation

## �️ The UI

The UI is **read-only by design**. It cannot control the agent - it only explains what the agent is doing.

### What the UI Shows

- **Agent Status**: Current state (idle, observing, thinking, nudging)
- **Current Intent**: What the agent believes you're trying to do
- **Confidence Level**: How certain the agent is about its inference
- **Last Decision**: The most recent action the agent took
- **Reasoning Timeline**: Scrollable history of agent decisions with explanations

### What the UI Does NOT Show

- ❌ Productivity scores or metrics
- ❌ App-by-app surveillance breakdown
- ❌ Gamification or streaks
- ❌ Any controls to start/stop/configure the agent

### Building for Production

```bash
cd ui
npm run build
# Static files output to ui/dist/
```

## 📁 Project Structure

```
KairosAgent/
├── local_agent/
│   ├── main.py              # Entry point & agent loop
│   ├── activity_tracker.py  # Windows activity monitoring
│   ├── classifier.py        # Local activity classification
│   ├── cloud_client.py      # Cloud service communication
│   ├── api_server.py        # Read-only API for UI
│   └── requirements.txt
├── cloud_service/
│   ├── main.py              # FastAPI endpoints (/analyze, /status, /health)
│   ├── agent.py             # Reasoning agent logic
│   ├── vertex_client.py     # Vertex AI integration (CLOUD_MODE aware)
│   ├── models.py            # Pydantic data models
│   ├── requirements.txt
│   └── Dockerfile
├── ui/
│   ├── src/
│   │   ├── App.jsx          # Main React component
│   │   ├── main.jsx         # Entry point
│   │   └── index.css        # Minimal styling
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── demo.py                   # One-click demo runner
├── .env.example              # Environment variable template
└── README.md
```

## 🚀 Deploy to Cloud Run

```bash
cd cloud_service

# Build and deploy
gcloud run deploy kairos-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=your-project,LOCATION=us-central1,CLOUD_MODE=true
```

## 🧪 Testing

### Quick Test (No dependencies)

```bash
python demo.py --quick
```

### Full Test (With UI)

```bash
python demo.py
```

### Without UI

```bash
python demo.py --no-ui
```

## License

MIT - Built for AgentX Hackathon 2025
