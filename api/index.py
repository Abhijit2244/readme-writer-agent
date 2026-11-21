"""
Vercel Serverless Function Entry Point
======================================
Exposes the FastAPI application object for Vercel's Python runtime (@vercel/python).
Includes defensive path resolution, ASGI path normalization, and startup error reporting.
"""

import sys
import os
import traceback
import urllib.parse

# Add all relevant candidate roots to sys.path so server and core are always discoverable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
LAMBDA_TASK_ROOT = os.environ.get("LAMBDA_TASK_ROOT", "")

for candidate in [PROJECT_ROOT, CURRENT_DIR, LAMBDA_TASK_ROOT]:
    if candidate and candidate not in sys.path:
        sys.path.insert(0, candidate)

try:
    from server import app as fastapi_app

    class VercelPathNormalizer:
        """
        ASGI Middleware that restores the real incoming client request path
        when Vercel rewrites incoming traffic to /api/index.py.
        """
        def __init__(self, asgi_app):
            self.asgi_app = asgi_app

        async def __call__(self, scope, receive, send):
            if scope.get("type") == "http":
                raw_query = scope.get("query_string", b"").decode("latin-1")

                # 1. Check if Vercel passed path via query parameter: ?__vpath=...
                if "__vpath=" in raw_query:
                    params = dict(qc.split("=", 1) for qc in raw_query.split("&") if "=" in qc)
                    if "__vpath" in params:
                        vpath = urllib.parse.unquote(params["__vpath"]).lstrip("/")
                        norm_path = f"/api/{vpath}" if not vpath.startswith("api/") else f"/{vpath}"
                        scope["path"] = norm_path
                        scope["raw_path"] = norm_path.encode("latin-1")
                        # Strip __vpath from query string so endpoints don't see internal parameter
                        clean_params = [qc for qc in raw_query.split("&") if not qc.startswith("__vpath=")]
                        scope["query_string"] = "&".join(clean_params).encode("latin-1")

                # 2. If path is generic entrypoint (/api, /api/index.py), check Vercel headers
                curr_path = scope.get("path", "")
                if curr_path in ("/api/index.py", "/api/index", "/api", "/api/"):
                    headers = dict(scope.get("headers", []))
                    for h_name in [b"x-forwarded-uri", b"x-real-path", b"x-vercel-forwarded-path", b"x-matched-path", b"x-invoke-path"]:
                        val = headers.get(h_name)
                        if val:
                            val_str = val.decode("latin-1").split("?")[0].strip()
                            if val_str and val_str not in ("/api/index.py", "/api/index", "/api", "/api/"):
                                scope["path"] = val_str
                                scope["raw_path"] = val_str.encode("latin-1")
                                break

            await self.asgi_app(scope, receive, send)

    app = VercelPathNormalizer(fastapi_app)

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
