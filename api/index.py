"""
Vercel Serverless Function Entry Point
======================================
Exposes the FastAPI application object for Vercel's Python runtime (@vercel/python).
Includes defensive path resolution and startup error reporting.
"""

import sys
import os
import traceback

# Add all relevant candidate roots to sys.path so server and core are always discoverable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
LAMBDA_TASK_ROOT = os.environ.get("LAMBDA_TASK_ROOT", "")

for candidate in [PROJECT_ROOT, CURRENT_DIR, LAMBDA_TASK_ROOT]:
    if candidate and candidate not in sys.path:
        sys.path.insert(0, candidate)

try:
    from server import app
except Exception as e:
    err_tb = traceback.format_exc()
    print("FATAL ERROR IN VERCEL SERVERLESS STARTUP:\n" + err_tb, file=sys.stderr)
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="Startup Diagnostic Fallback")

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    def error_diagnostic(full_path: str):
        return HTMLResponse(
            content=(
                "<!DOCTYPE html><html><head><title>Serverless Startup Error</title></head>"
                "<body style='font-family:-apple-system,BlinkMacSystemFont,sans-serif;padding:32px;background:#0d1117;color:#c9d1d9;'>"
                "<h2 style='color:#f85149;'>⚠️ Vercel Serverless Function Startup Error</h2>"
                f"<p><strong>Python sys.path:</strong> <code>{sys.path}</code></p>"
                f"<p><strong>Current Directory:</strong> <code>{os.getcwd()}</code></p>"
                f"<pre style='background:#161b22;padding:16px;border-radius:8px;border:1px solid #30363d;color:#ff7b72;white-space:pre-wrap;'>{err_tb}</pre>"
                "</body></html>"
            ),
            status_code=500
        )
