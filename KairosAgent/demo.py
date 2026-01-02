"""
Kairos Agent - Demo Runner
===========================
One-click demo script to showcase the full system with UI.

Usage:
    python demo.py           # Full demo with UI
    python demo.py --quick   # Quick demo (30 seconds)
    python demo.py --no-ui   # Run without UI

Components Started:
1. Cloud Service (FastAPI) - http://localhost:8080
2. Local Agent with API    - http://localhost:5000
3. UI (optional)           - http://localhost:3000

Author: Kairos Team - AgentX Hackathon 2026
"""

import os
import sys
import time
import subprocess
import threading
import signal
import webbrowser
import socket

# Ensure we're in demo mode
os.environ["DEMO_MODE"] = "true"
os.environ["CLOUD_MODE"] = "false"  # Deterministic responses for demo
os.environ["USER_GOALS"] = "coding,learning"


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def kill_port(port: int):
    """Kill process using a specific port (Windows only)."""
    if sys.platform == "win32":
        try:
            # Find and kill process using the port
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True,
                capture_output=True,
                text=True
            )
            for line in result.stdout.strip().split('\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if parts:
                        pid = parts[-1]
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
        except Exception:
            pass


def cleanup_ports():
    """Clean up ports that might be in use from previous runs."""
    ports = [8080, 5000, 3000]
    for port in ports:
        if is_port_in_use(port):
            print(f"⚠️  Port {port} in use, attempting to free...")
            kill_port(port)
            time.sleep(0.5)


def print_banner():
    """Print a nice banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🕐 KAIROS AGENT - Autonomous Productivity AI               ║
║                                                               ║
║   A privacy-first productivity companion that:                ║
║   • Runs autonomously on your machine                         ║
║   • Uses Google Cloud + Vertex AI for reasoning               ║
║   • Explains its decisions transparently                      ║
║   • Never surveils - only summarizes                          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_dependencies():
    """Check if required packages are installed."""
    print("📦 Checking dependencies...")
    
    missing = []
    
    # Check local agent deps
    try:
        import httpx
    except ImportError:
        missing.append("httpx")
    
    # Check cloud service deps
    try:
        import fastapi
        import uvicorn
        import pydantic
    except ImportError:
        missing.extend(["fastapi", "uvicorn", "pydantic"])
    
    if missing:
        print(f"❌ Missing packages: {', '.join(set(missing))}")
        print("\nInstall with:")
        print("  pip install httpx fastapi uvicorn pydantic")
        return False
    
    print("✅ All Python dependencies available")
    return True


def check_ui_dependencies():
    """Check if Node.js is available for UI."""
    try:
        result = subprocess.run(
            "node --version",
            capture_output=True,
            text=True,
            timeout=5,
            shell=True
        )
        if result.returncode == 0:
            print(f"✅ Node.js available: {result.stdout.strip()}")
            return True
    except Exception:
        pass
    
    print("⚠️  Node.js not found - UI will not be available")
    print("   Install from: https://nodejs.org/")
    return False


def start_cloud_service():
    """Start the cloud service in a subprocess."""
    print("\n☁️  Starting Cloud Run service (simulated) on http://localhost:8080...")
    
    cloud_dir = os.path.join(os.path.dirname(__file__), "cloud_service")
    
    # Set environment
    env = os.environ.copy()
    env["DEMO_MODE"] = "true"
    env["CLOUD_MODE"] = "false"
    env["PORT"] = "8080"
    
    # Start uvicorn
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"],
        cwd=cloud_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    
    # Wait for service to be ready
    time.sleep(3)
    
    if process.poll() is not None:
        print("❌ Cloud service failed to start")
        stdout, stderr = process.communicate()
        print(f"STDERR: {stderr.decode()}")
        return None
    
    print("✅ Cloud Run service running (CLOUD_MODE=false for demo)")
    return process


def start_ui():
    """Start the React UI."""
    ui_dir = os.path.join(os.path.dirname(__file__), "ui")
    
    # Check if node_modules exists
    node_modules = os.path.join(ui_dir, "node_modules")
    if not os.path.exists(node_modules):
        print("\n📦 Installing UI dependencies (first run only)...")
        subprocess.run(
            "npm install",
            cwd=ui_dir,
            capture_output=True,
            shell=True
        )
    
    print("\n🖥️  Starting UI on http://localhost:3000...")
    
    process = subprocess.Popen(
        "npm run dev",
        cwd=ui_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    
    time.sleep(3)
    
    if process.poll() is not None:
        print("⚠️  UI failed to start")
        return None
    
    print("✅ UI running at http://localhost:3000")
    return process


def run_local_agent(duration: int):
    """Run the local agent."""
    print(f"\n🤖 Starting local agent (will run for {duration} seconds)...")
    print(f"    Local API: http://localhost:5000")
    
    local_dir = os.path.join(os.path.dirname(__file__), "local_agent")
    
    # Import and run directly
    sys.path.insert(0, local_dir)
    
    # Set environment
    os.environ["CLOUD_SERVICE_URL"] = "http://localhost:8080"
    os.environ["DEMO_MODE"] = "true"
    
    # Import after setting path
    from main import KairosAgent, ActivityTracker
    
    # Speed up for demo
    ActivityTracker.SUMMARY_INTERVAL = 15  # 15 seconds instead of 5 minutes
    
    # Create and run agent
    agent = KairosAgent()
    agent.run(duration_seconds=duration, enable_ui_api=True)


def main():
    """Main demo entry point."""
    print_banner()
    
    # Parse arguments
    quick_mode = "--quick" in sys.argv
    no_ui = "--no-ui" in sys.argv
    duration = 30 if quick_mode else 120  # 2 minutes for full demo
    
    print(f"Mode: {'Quick' if quick_mode else 'Full'} Demo ({duration}s)")
    print(f"UI: {'Disabled' if no_ui else 'Enabled'}")
    print("="*60)
    
    # Clean up any ports from previous runs
    cleanup_ports()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    has_node = check_ui_dependencies() if not no_ui else False
    
    # Start cloud service
    cloud_process = start_cloud_service()
    if not cloud_process:
        sys.exit(1)
    
    # Start UI if available
    ui_process = None
    if has_node and not no_ui:
        ui_process = start_ui()
        if ui_process:
            # Open browser after a short delay
            time.sleep(2)
            print("\n🌐 Opening UI in browser...")
            webbrowser.open("http://localhost:3000")
    
    try:
        # Give services time to fully initialize
        print("\n⏳ Waiting for services to initialize...")
        time.sleep(2)
        
        # Test cloud service
        print("\n🔍 Testing cloud service...")
        try:
            import httpx
            response = httpx.get("http://localhost:8080/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Cloud service healthy")
                print(f"   Vertex AI: {'Available' if data.get('vertex_ai_available') else 'Demo Mode'}")
            else:
                print(f"⚠️  Cloud service returned: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Could not reach cloud service: {e}")
        
        # Run local agent
        run_local_agent(duration)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Demo interrupted by user")
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        if ui_process:
            if sys.platform == "win32":
                ui_process.terminate()
            else:
                ui_process.send_signal(signal.SIGTERM)
            try:
                ui_process.wait(timeout=5)
            except:
                pass
        
        if cloud_process:
            if sys.platform == "win32":
                cloud_process.terminate()
            else:
                cloud_process.send_signal(signal.SIGTERM)
            try:
                cloud_process.wait(timeout=5)
            except:
                pass
        
        print("✅ Demo complete!")


def demo_summary():
    """Print a summary of what the demo showed."""
    summary = """
╔═══════════════════════════════════════════════════════════════╗
║                     DEMO SUMMARY                              ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  What you just saw:                                           ║
║                                                               ║
║  1. AUTONOMOUS AGENT LOOP                                     ║
║     Observe → Summarize → Decide → Act → Reflect              ║
║     The agent ran without user control                        ║
║                                                               ║
║  2. CLOUD RUN SERVICE (FastAPI)                               ║
║     • /health - Service health check                          ║
║     • /analyze - Activity analysis endpoint                   ║
║     • /status - Detailed service status                       ║
║                                                               ║
║  3. VERTEX AI (Gemini) INTEGRATION                            ║
║     • Structured prompting with system context                ║
║     • JSON output for reliable parsing                        ║
║     • Graceful fallback when unavailable                      ║
║                                                               ║
║  4. MINIMAL ETHICAL UI                                        ║
║     • READ-ONLY - cannot control the agent                    ║
║     • Shows: Intent, Confidence, Reasoning                    ║
║     • Builds trust through transparency                       ║
║     • No surveillance metrics or scores                       ║
║                                                               ║
║  5. PRIVACY BY DESIGN                                         ║
║     • Only summaries leave the device                         ║
║     • No keystrokes, no screenshots                           ║
║     • User goals drive decisions                              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(summary)


if __name__ == "__main__":
    main()
    demo_summary()
