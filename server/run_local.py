"""
One-command local runner for the standalone trip-planner service.

Does the setup, starts the server, and — critically — writes everything it
does to server/run_log.txt as it happens, not just at the end. If the
console window closes, crashes, or gets swallowed by Windows, the log file
on disk still has the real error in it.

Run with: python server/run_local.py
(server/run_windows.bat just calls this and pauses afterward.)
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = Path(__file__).resolve().parent / "run_log.txt"


def log(line, logfile):
    print(line)
    logfile.write(line + "\n")
    logfile.flush()


def run_streamed(cmd, logfile, cwd=None):
    log(f"$ {' '.join(cmd)}", logfile)
    process = subprocess.Popen(
        cmd, cwd=cwd or REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    for line in process.stdout:
        print(line, end="")
        logfile.write(line)
        logfile.flush()
    process.wait()
    return process.returncode


def main():
    with open(LOG_PATH, "w", encoding="utf-8") as logfile:
        log("=== AU Trip Planner - local run ===", logfile)
        log(f"Python: {sys.version}", logfile)
        log(f"Working directory: {REPO_ROOT}", logfile)
        log("", logfile)

        log("Installing dependencies (first run takes a minute)...", logfile)
        code = run_streamed(
            [sys.executable, "-m", "pip", "install", "-r", str(REPO_ROOT / "server" / "requirements.txt")],
            logfile,
        )
        if code != 0:
            log("", logfile)
            log(f"ERROR: pip install failed with exit code {code}.", logfile)
            log(f"Full log saved to: {LOG_PATH}", logfile)
            log("Send that file back for a fix.", logfile)
            return code

        log("", logfile)
        log("Starting server on http://localhost:8000 ...", logfile)
        log("Leave this window open. Press Ctrl+C to stop.", logfile)
        log("", logfile)
        code = run_streamed(
            [sys.executable, "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", "8000"],
            logfile,
        )
        if code != 0:
            log("", logfile)
            log(f"ERROR: server exited with code {code}.", logfile)
            log(f"Full log saved to: {LOG_PATH}", logfile)
            log("Send that file back for a fix.", logfile)
        return code


if __name__ == "__main__":
    sys.exit(main())
