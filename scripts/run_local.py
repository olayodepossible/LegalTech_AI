#!/usr/bin/env python3
"""
Run both frontend and backend locally for development.
This script starts the NextJS frontend and FastAPI backend in parallel.
"""

import os
import sys
import shutil
import subprocess
import signal
import time
from pathlib import Path


def resolve_npm_executable() -> str | None:
    """Locate npm on PATH; on Windows also try npm.cmd and the folder next to node.exe."""
    for name in ("npm", "npm.cmd"):
        found = shutil.which(name)
        if found:
            return found
    node = shutil.which("node")
    if not node:
        return None
    parent = Path(node).resolve().parent
    for candidate in (parent / "npm.cmd", parent / "npm", parent / "npm.ps1"):
        if candidate.is_file():
            return str(candidate)
    return None

# Track subprocesses for cleanup
processes = []

def cleanup(signum=None, frame=None):
    """Clean up all subprocess on exit"""
    print("\n🛑 Shutting down services...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            proc.kill()
    sys.exit(0)

# Register cleanup handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def check_requirements():
    """Check if required tools are installed"""
    checks = []

    # Check Node.js
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        node_version = result.stdout.strip()
        checks.append(f"✅ Node.js: {node_version}")
    except FileNotFoundError:
        checks.append("❌ Node.js not found - please install Node.js")

    # Check npm (Windows: often npm.cmd or next to node.exe)
    npm_exe = resolve_npm_executable()
    if npm_exe:
        try:
            result = subprocess.run(
                [npm_exe, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            npm_version = (result.stdout or result.stderr).strip() or "unknown"
            checks.append(f"✅ npm: {npm_version}")
        except OSError:
            checks.append("❌ npm found but failed to run - check your Node.js install")
    else:
        checks.append(
            "❌ npm not found - reinstall Node.js (include npm) or ensure npm is on PATH"
        )

    # Check uv (which manages Python for us)
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        uv_version = result.stdout.strip()
        checks.append(f"✅ uv: {uv_version}")
    except FileNotFoundError:
        checks.append("❌ uv not found - please install uv")

    print("\n📋 Prerequisites Check:")
    for check in checks:
        print(f"  {check}")

    # Exit if any critical tools are missing
    if any("❌" in check for check in checks):
        print("\n⚠️  Please install missing dependencies and try again.")
        sys.exit(1)

def check_env_files():
    """Check if environment files exist"""
    project_root = Path(__file__).parent.parent

    root_env = project_root / ".env"
    frontend_env = project_root / "frontend" / ".env.local"

    missing = []

    if not root_env.exists():
        missing.append(".env (root project file)")
    if not frontend_env.exists():
        missing.append("frontend/.env.local")

    if missing:
        print("\n⚠️  Missing environment files:")
        for file in missing:
            print(f"  - {file}")
        print("\nPlease create these files with the required configuration.")
        print("The root .env should have all backend variables from Parts 1-7.")
        print("The frontend/.env.local should have Clerk keys.")
        sys.exit(1)

    print("✅ Environment files found")

def start_backend():
    """Start FastAPI via the backend uv workspace so ``contract-analyst`` and other members resolve."""
    project_root = Path(__file__).parent.parent
    backend_root = project_root / "backend"

    print("\n🚀 Starting FastAPI backend...")

    if not (backend_root / ".venv").exists():
        print("  Installing backend workspace dependencies (uv sync)...")
        subprocess.run(["uv", "sync"], cwd=backend_root, check=True)

    # Inherit stdout/stderr so logs are not buffered in a pipe (PIPE can fill and stall or break children on Windows)
    proc = subprocess.Popen(
        ["uv", "run", "--package", "api", "python", "api/main.py"],
        cwd=backend_root,
    )
    processes.append(proc)

    # Wait for backend to start
    print("  Waiting for backend to start...")
    for _ in range(30):  # 30 second timeout
        try:
            import httpx
            response = httpx.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("  ✅ Backend running at http://localhost:8000")
                print("     API docs: http://localhost:8000/docs")
                return proc
        except:
            time.sleep(1)

    print("  ❌ Backend failed to start")
    cleanup()

def start_frontend():
    """Start the NextJS frontend"""
    frontend_dir = Path(__file__).parent.parent / "frontend"

    print("\n🚀 Starting NextJS frontend...")

    npm_exe = resolve_npm_executable()
    if not npm_exe:
        print("  ❌ npm not found (needed for Next.js). Reinstall Node.js or fix PATH.")
        sys.exit(1)

    # Check if dependencies are installed
    if not (frontend_dir / "node_modules").exists():
        print("  Installing frontend dependencies...")
        subprocess.run([npm_exe, "install"], cwd=frontend_dir, check=True)

    proc = subprocess.Popen(
        [npm_exe, "run", "dev"],
        cwd=frontend_dir,
    )
    processes.append(proc)

    # Wait for frontend to start (HTTP poll only — select() does not work on Windows pipes)
    print("  Waiting for frontend to start...")
    import httpx

    for i in range(90):
        if proc.poll() is not None:
            print("  ❌ Frontend process exited before the dev server was ready.")
            cleanup()

        try:
            httpx.get("http://localhost:3000", timeout=2)
            print("  ✅ Frontend running at http://localhost:3000")
            return proc
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        except httpx.HTTPError:
            # Server is listening (e.g. 404) — dev server is up
            print("  ✅ Frontend running at http://localhost:3000")
            return proc

        if i > 0 and i % 10 == 0:
            print(f"    ... still waiting ({i}s; first Next compile can be slow)")
        time.sleep(1)

    print("  ❌ Frontend failed to start")
    cleanup()


def monitor_processes():
    """Keep the script alive while backend/frontend run; their logs go to this terminal (inherited stdio)."""
    print("\n" + "="*60)
    print("🎯 Legal Companion Advisor - Local Development")
    print("="*60)
    print("\n📍 Services:")
    print("  Frontend: http://localhost:3000")
    print("  Backend:  http://localhost:8000")
    print("  API Docs: http://localhost:8000/docs")
    print("\n📝 Backend and Next.js logs print above/below in this terminal. Press Ctrl+C to stop.\n")
    print("="*60 + "\n")

    labels = ["backend", "frontend"]
    while True:
        for proc, label in zip(processes, labels):
            if proc.poll() is not None:
                print(f"\n⚠️  {label} exited unexpectedly (exit code {proc.returncode}).")
                cleanup()
        time.sleep(0.5)

def main():
    """Main entry point"""
    print("\n🔧 Legal Companion Advisor - Local Development Setup")
    print("="*50)

    # Check prerequisites
    check_requirements()
    check_env_files()

    # Install httpx if needed
    try:
        import httpx
    except ImportError:
        print("\n📦 Installing httpx for health checks...")
        subprocess.run(["uv", "add", "httpx"], check=True)

    # Start services
    backend_proc = start_backend()
    frontend_proc = start_frontend()

    # Monitor processes
    try:
        monitor_processes()
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()