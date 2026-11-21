"""
Production Web Application & Hosting Server (Vercel & Cloud Ready)
===================================================================
FastAPI-powered enterprise web application for Autonomous README Writer Agent.

Hosting Capabilities:
  • Vercel Serverless Function compatibility (via api/index.py and vercel.json).
  • GitHub Repository URL ingestion (clone/archive inspection in serverless /tmp).
  • Project Zip file upload ingestion (safe extraction with Zip-Slip defense).
  • Local filesystem path inspection (for local/desktop hosting).
  • In-browser rich Markdown rendering with live interactive Mermaid.js diagrams.
  • One-click direct file downloading for generated documentation.
  • Perimeter security: Path traversal defense, API key redaction, CSP headers.

Run locally with:
  python server.py
or:
  uvicorn server:app --host 0.0.0.0 --port 8000
"""

import os
import sys
import shutil
import tempfile
import urllib.request
import logging
from typing import Optional, List, Dict, Any

# Ensure project root is in Python module path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Request, Response, Query, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from core.agent import ReadmeWriterAgent
from core.security import SecurityValidator
from core.safety import ReadmeSafetyController
from core.scanner import RepositoryScanner

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("readme_agent_server")

app = FastAPI(
    title="Autonomous README Writer Agent",
    description="Enterprise API & Web Dashboard for Automated AST Documentation Synthesis",
    version="1.0.0"
)

# --------------------------------------------------------------------------
# CORS MIDDLEWARE (Supports decoupled React SPA during dev & production)
# --------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# SECURITY MIDDLEWARE (CSP, Anti-Clickjacking, MIME Sniffing Protection)
# --------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' *; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net *; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com *; "
            "font-src 'self' https://fonts.gstatic.com data: *; "
            "img-src 'self' data: https: *; "
            "connect-src 'self' http: https: *;"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Dist directory resolution for decoupled React Frontend
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "dist"))
DIST_INDEX = os.path.join(DIST_DIR, "index.html")
DIST_ASSETS = os.path.join(DIST_DIR, "assets")

if os.path.exists(DIST_ASSETS):
    app.mount("/assets", StaticFiles(directory=DIST_ASSETS), name="assets")


# --------------------------------------------------------------------------
# REQUEST / RESPONSE DATA SCHEMAS
# --------------------------------------------------------------------------
class ValidateRequest(BaseModel):
    repo_path: str = Field(..., description="Local filesystem path to target repository")

class GenerateRequest(BaseModel):
    repo_path: str = Field(..., description="Local filesystem path to target repository")
    force: bool = Field(False, description="If True, authorizes overwriting existing README.md")
    custom_output_name: Optional[str] = Field(None, description="Optional custom filename for generated markdown")
    use_gemini: bool = Field(False, description="Toggle Gemini AI enhancement mode")
    gemini_api_key: Optional[str] = Field(None, description="Optional explicit Gemini API key")

class GitHubGenerateRequest(BaseModel):
    github_url: str = Field(..., description="Public GitHub repository URL (e.g. https://github.com/owner/repo)")
    force: bool = Field(False, description="If True, authorizes overwriting existing README.md")
    use_gemini: bool = Field(False, description="Toggle Gemini AI enhancement mode")
    gemini_api_key: Optional[str] = Field(None, description="Optional explicit Gemini API key")


# --------------------------------------------------------------------------
# IN-MEMORY CACHE FOR GENERATED SESSIONS (For secure downloading)
# --------------------------------------------------------------------------
SESSION_CACHE: Dict[str, Dict[str, Any]] = {}


# --------------------------------------------------------------------------
# HELPER: RUN AGENT ON DIRECTORY & CACHE RESULT
# --------------------------------------------------------------------------
def _execute_agent_on_dir(
    target_dir: str,
    force: bool,
    custom_output_name: Optional[str] = None,
    use_gemini: bool = False,
    gemini_api_key: Optional[str] = None
):
    telemetry_logs: List[Dict[str, Any]] = []

    def event_collector(event_type: str, data: Any):
        telemetry_logs.append({
            "type": event_type,
            "data": data if isinstance(data, (str, int, float, bool, list, dict)) else str(data)
        })

    agent = ReadmeWriterAgent(verbose=False)
    agent.register_callback(event_collector)

    result = agent.run(
        repo_path=target_dir,
        force=force,
        use_gemini=use_gemini,
        gemini_api_key=gemini_api_key,
        custom_output_name=custom_output_name
    )

    session_id = f"sess_{os.path.basename(target_dir)}_{len(SESSION_CACHE) + 1}"
    SESSION_CACHE[session_id] = {
        "filename": os.path.basename(result.output_path),
        "content": result.markdown_content,
        "output_path": result.output_path
    }

    return {
        "success": True,
        "session_id": session_id,
        "engine_mode": "Gemini 2.0 Flash AI" if use_gemini else "Local Deterministic AST",
        "output_path": result.output_path,
        "output_filename": os.path.basename(result.output_path),
        "was_overwritten": result.was_overwritten,
        "saved_as_alternate": result.saved_as_alternate,
        "entities_documented_count": result.entities_documented_count,
        "sections_included": result.sections_included,
        "markdown_content": result.markdown_content,
        "telemetry_logs": telemetry_logs
    }


# --------------------------------------------------------------------------
# API ENDPOINTS
# --------------------------------------------------------------------------
@app.get("/health")
def health_check():
    """Healthcheck endpoint for container orchestration, Vercel, and uptime monitors."""
    return {
        "status": "healthy",
        "service": "readme-writer-agent",
        "platform": "vercel-ready",
        "version": "1.0.0",
        "gemini_env_configured": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        "security": {
            "path_traversal_protection": "active",
            "secret_redaction": "active",
            "zip_slip_defense": "active",
            "non_destructive_guardrails": "active"
        }
    }


@app.post("/api/validate")
def validate_repository(req: ValidateRequest):
    """
    Performs perimeter security checks and inspects target directory safely
    without executing or writing any code.
    """
    is_safe, canonical_path, error_msg = SecurityValidator.validate_repo_path(req.repo_path)
    if not is_safe:
        return JSONResponse(status_code=400, content={"valid": False, "error": error_msg})

    try:
        safety = ReadmeSafetyController(canonical_path)
        has_existing, existing_path = safety.check_existing_readme()

        scanner = RepositoryScanner(canonical_path)
        files = scanner.scan_files()
        tech_stack = scanner.detect_tech_stack(files)

        return {
            "valid": True,
            "canonical_path": canonical_path,
            "repo_name": os.path.basename(canonical_path),
            "total_files": len(files),
            "primary_language": tech_stack.primary_language,
            "frameworks": tech_stack.frameworks,
            "has_existing_readme": has_existing,
            "existing_readme_name": os.path.basename(existing_path) if existing_path else None
        }
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return JSONResponse(status_code=500, content={"valid": False, "error": str(e)})


@app.post("/api/generate")
def generate_readme(req: GenerateRequest):
    """Generates README for a local filesystem path (with perimeter security checks)."""
    is_safe, canonical_path, error_msg = SecurityValidator.validate_repo_path(req.repo_path)
    if not is_safe:
        raise HTTPException(status_code=400, detail=f"Security Validation Blocked: {error_msg}")

    try:
        return _execute_agent_on_dir(
            canonical_path,
            force=req.force,
            custom_output_name=req.custom_output_name,
            use_gemini=req.use_gemini,
            gemini_api_key=req.gemini_api_key
        )
    except Exception as e:
        logger.error(f"Generation failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/api/generate-github")
def generate_readme_from_github(req: GitHubGenerateRequest):
    """
    Fetches a public GitHub repository zipball, extracts it safely in serverless /tmp,
    and runs the full documentation analysis pipeline. Perfect for Vercel deployments!
    """
    is_valid, owner, repo, err_msg = SecurityValidator.validate_github_url(req.github_url)
    if not is_valid:
        raise HTTPException(status_code=400, detail=err_msg)

    temp_base = tempfile.mkdtemp(prefix=f"gh_{owner}_{repo}_")
    zip_dest = os.path.join(temp_base, "repo.zip")
    extract_dest = os.path.join(temp_base, "extracted")

    try:
        # Download public zip archive from GitHub
        urls_to_try = [
            f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/main",
            f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/master"
        ]

        download_success = False
        headers = {"User-Agent": "Autonomous-Readme-Writer-Agent/1.0"}

        for u in urls_to_try:
            try:
                request = urllib.request.Request(u, headers=headers)
                with urllib.request.urlopen(request, timeout=15) as response, open(zip_dest, "wb") as out_file:
                    shutil.copyfileobj(response, out_file)
                download_success = True
                break
            except Exception:
                continue

        if not download_success:
            raise HTTPException(
                status_code=404,
                detail=f"Could not download repository '{owner}/{repo}'. Please ensure the repository is public and accessible."
            )

        # Safe extraction with Zip-Slip protection
        success, extract_err = SecurityValidator.safe_extract_zip(zip_dest, extract_dest)
        if not success:
            raise HTTPException(status_code=400, detail=f"Zip Extraction Security Alert: {extract_err}")

        # GitHub archives extract into an inner folder like 'repo-main/'
        inner_entries = os.listdir(extract_dest)
        repo_root = extract_dest
        if len(inner_entries) == 1 and os.path.isdir(os.path.join(extract_dest, inner_entries[0])):
            repo_root = os.path.join(extract_dest, inner_entries[0])

        return _execute_agent_on_dir(
            repo_root,
            force=req.force,
            use_gemini=req.use_gemini,
            gemini_api_key=req.gemini_api_key
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitHub pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"GitHub repository analysis error: {str(e)}")
    finally:
        # Cleanup zip file to conserve serverless disk space
        if os.path.exists(zip_dest):
            try:
                os.remove(zip_dest)
            except Exception:
                pass


@app.post("/api/upload-zip")
async def generate_readme_from_zip(
    file: UploadFile = File(...),
    force: bool = Form(False),
    use_gemini: bool = Form(False),
    gemini_api_key: Optional[str] = Form(None)
):
    """
    Accepts a project .zip archive uploaded directly from the browser,
    extracts it safely in serverless /tmp, and generates documentation.
    """
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip archives are supported.")

    temp_base = tempfile.mkdtemp(prefix="upload_repo_")
    zip_dest = os.path.join(temp_base, "uploaded.zip")
    extract_dest = os.path.join(temp_base, "extracted")

    try:
        # Write uploaded bytes to temp file
        with open(zip_dest, "wb") as f:
            content = await file.read()
            # Guard against massive file uploads
            if len(content) > 50 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Uploaded zip file exceeds 50MB limit.")
            f.write(content)

        # Safe extraction with Zip-Slip defense
        success, extract_err = SecurityValidator.safe_extract_zip(zip_dest, extract_dest)
        if not success:
            raise HTTPException(status_code=400, detail=f"Zip Extraction Security Alert: {extract_err}")

        # Detect extracted root
        inner_entries = os.listdir(extract_dest)
        repo_root = extract_dest
        if len(inner_entries) == 1 and os.path.isdir(os.path.join(extract_dest, inner_entries[0])):
            repo_root = os.path.join(extract_dest, inner_entries[0])

        return _execute_agent_on_dir(
            repo_root,
            force=force,
            use_gemini=use_gemini,
            gemini_api_key=gemini_api_key
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Zip upload pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Zip processing error: {str(e)}")
    finally:
        if os.path.exists(zip_dest):
            try:
                os.remove(zip_dest)
            except Exception:
                pass


@app.get("/api/download")
def download_readme(session_id: str = Query(..., description="Session identifier from generation")):
    """Directly downloads the generated markdown documentation file."""
    if session_id not in SESSION_CACHE:
        raise HTTPException(status_code=404, detail="Requested documentation session has expired or is invalid.")

    record = SESSION_CACHE[session_id]
    filename = record["filename"]
    content = record["content"]

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "text/markdown; charset=utf-8"
    }
    return Response(content=content, media_type="text/markdown", headers=headers)


# --------------------------------------------------------------------------
# SINGLE-PAGE WEB INTERFACE (HTML, CSS, JAVASCRIPT)
# --------------------------------------------------------------------------
@app.get("/")
def index():
    """Serves the decoupled React frontend dashboard (or embedded fallback)."""
    if os.path.exists(DIST_INDEX):
        return FileResponse(DIST_INDEX)
    html_content = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Autonomous README Writer Agent (Vercel Edition)</title>
  <!-- Google Fonts & CDN Libraries -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
  <style>
    :root {
      --bg-dark: #0d1117;
      --card-bg: #161b22;
      --card-border: #30363d;
      --accent-blue: #58a6ff;
      --accent-green: #2ea043;
      --accent-purple: #bc8cff;
      --accent-yellow: #d29922;
      --accent-red: #f85149;
      --text-main: #c9d1d9;
      --text-muted: #8b949e;
      --code-bg: #090d13;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: var(--bg-dark);
      color: var(--text-main);
      line-height: 1.6;
      padding-bottom: 60px;
    }
    header {
      background: #161b22;
      border-bottom: 1px solid var(--card-border);
      padding: 18px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-icon {
      font-size: 26px;
      background: linear-gradient(135deg, #1f6feb, #8957e5);
      border-radius: 8px;
      padding: 4px 8px;
    }
    .brand h1 {
      font-size: 19px;
      font-weight: 700;
      color: #f0f6fc;
      letter-spacing: -0.3px;
    }
    .brand p {
      font-size: 12px;
      color: var(--text-muted);
    }
    .header-badges {
      display: flex;
      gap: 10px;
    }
    .badge {
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }
    .badge-green { background: rgba(46, 160, 67, 0.15); color: #3fb950; border: 1px solid rgba(46, 160, 67, 0.4); }
    .badge-purple { background: rgba(188, 140, 255, 0.15); color: #d2a8ff; border: 1px solid rgba(188, 140, 255, 0.4); }
    
    .container {
      max-width: 1300px;
      margin: 28px auto;
      padding: 0 24px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }
    .card-title {
      font-size: 16px;
      font-weight: 600;
      color: #f0f6fc;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* Input Source Mode Tabs */
    .mode-tabs {
      display: flex;
      gap: 10px;
      margin-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 12px;
    }
    .mode-tab-btn {
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 8px 18px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .mode-tab-btn.active {
      background: linear-gradient(135deg, #1f6feb, #388bfd);
      color: #fff;
      border-color: #58a6ff;
    }

    .form-group {
      margin-bottom: 16px;
    }
    label {
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: #e6edf3;
      margin-bottom: 6px;
    }
    input[type="text"], input[type="file"] {
      width: 100%;
      background: var(--code-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px 14px;
      color: #f0f6fc;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      transition: border-color 0.2s;
    }
    input[type="text"]:focus {
      outline: none;
      border-color: var(--accent-blue);
      box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.2);
    }
    .quick-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }
    .chip {
      background: rgba(110, 118, 129, 0.15);
      border: 1px solid rgba(110, 118, 129, 0.3);
      color: var(--accent-blue);
      font-size: 11px;
      font-family: 'JetBrains Mono', monospace;
      padding: 4px 10px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .chip:hover {
      background: rgba(88, 166, 255, 0.15);
      border-color: var(--accent-blue);
    }
    /* Engine Toggle Styles */
    .engine-toggle-group {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-top: 6px;
    }
    @media (max-width: 768px) {
      .engine-toggle-group { grid-template-columns: 1fr; }
    }
    .engine-btn {
      padding: 14px 18px;
      background: #1c2128;
      border: 2px solid var(--card-border);
      border-radius: 10px;
      color: var(--text-muted);
      cursor: pointer;
      text-align: left;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      display: flex;
      flex-direction: column;
      gap: 5px;
      user-select: none;
    }
    .engine-btn:hover {
      border-color: #58a6ff;
      background: rgba(88, 166, 255, 0.05);
    }
    .engine-btn.active {
      background: rgba(46, 160, 67, 0.12);
      border-color: #3fb950;
      color: #f0f6fc;
      box-shadow: 0 0 12px rgba(46, 160, 67, 0.25);
    }
    .engine-btn.engine-gemini.active {
      background: rgba(188, 140, 255, 0.12);
      border-color: var(--accent-purple);
      color: #f0f6fc;
      box-shadow: 0 0 12px rgba(188, 140, 255, 0.25);
    }
    .engine-btn-title {
      font-size: 14px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .engine-btn-sub {
      font-size: 11.5px;
      color: var(--text-muted);
      font-weight: 400;
      line-height: 1.4;
    }
    .engine-btn.active .engine-btn-sub {
      color: #c9d1d9;
    }
    .api-key-box {
      background: rgba(188, 140, 255, 0.08);
      border: 1px solid rgba(188, 140, 255, 0.3);
      border-radius: 8px;
      padding: 14px 16px;
      margin-top: 14px;
      display: none;
      animation: fadeIn 0.25s ease-in-out;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }

    .options-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
      background: rgba(9, 13, 19, 0.6);
      padding: 14px 18px;
      border-radius: 8px;
      border: 1px solid var(--card-border);
      margin-top: 14px;
    }
    .toggle-label {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
      cursor: pointer;
    }
    .toggle-label input[type="checkbox"] {
      width: 18px;
      height: 18px;
      accent-color: var(--accent-yellow);
      cursor: pointer;
    }
    .btn-row {
      display: flex;
      gap: 12px;
      margin-top: 20px;
    }
    button {
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      border: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s;
    }
    .btn-primary {
      background: linear-gradient(135deg, #238636, #2ea043);
      color: #fff;
    }
    .btn-primary:hover {
      background: linear-gradient(135deg, #2ea043, #3fb950);
      transform: translateY(-1px);
    }
    .btn-secondary {
      background: #21262d;
      color: #c9d1d9;
      border: 1px solid var(--card-border);
    }
    .btn-secondary:hover {
      background: #30363d;
      color: #f0f6fc;
    }
    .btn-download {
      background: linear-gradient(135deg, #1f6feb, #388bfd);
      color: white;
    }
    .btn-download:hover {
      background: linear-gradient(135deg, #388bfd, #58a6ff);
    }
    
    /* Stats Bar */
    .stats-grid {
      display: grid;
      grid-template-columns: 1.05fr 0.85fr 1fr 0.95fr 1.35fr;
      gap: 14px;
      margin-bottom: 24px;
    }
    @media (max-width: 1024px) {
      .stats-grid { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
    }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 16px 18px;
      text-align: center;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      min-height: 96px;
      box-sizing: border-box;
      overflow: hidden;
    }
    .stat-value {
      font-size: 24px;
      font-weight: 700;
      color: #f0f6fc;
      font-family: 'JetBrains Mono', monospace;
      width: 100%;
      word-break: break-word;
    }
    .stat-filename-pill {
      font-size: 13px;
      font-weight: 600;
      line-height: 1.4;
      padding: 6px 12px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      letter-spacing: -0.2px;
      color: #e6edf3;
    }
    .stat-label {
      font-size: 11.5px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-top: 6px;
    }

    /* Live Telemetry Terminal */
    .terminal-box {
      background: #05080c;
      border: 1px solid #21262d;
      border-radius: 8px;
      padding: 16px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: #7ee787;
      max-height: 180px;
      overflow-y: auto;
      white-space: pre-wrap;
    }

    /* Viewer Tabs */
    .tab-header {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 12px;
      margin-bottom: 18px;
      align-items: center;
      justify-content: space-between;
    }
    .tab-buttons {
      display: flex;
      gap: 8px;
    }
    .tab-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      padding: 8px 16px;
      font-size: 13px;
      border-radius: 6px;
    }
    .tab-btn.active {
      background: #21262d;
      color: #f0f6fc;
      border-color: var(--card-border);
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; }

    /* Markdown Render Styling */
    .markdown-body {
      color: #c9d1d9;
      font-size: 14px;
      line-height: 1.7;
    }
    .markdown-body h1, .markdown-body h2, .markdown-body h3 {
      color: #f0f6fc;
      margin: 24px 0 14px;
      font-weight: 600;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 8px;
    }
    .markdown-body pre {
      background: var(--code-bg);
      border: 1px solid var(--card-border);
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12.5px;
      margin: 16px 0;
    }
    .markdown-body code {
      background: rgba(110, 118, 129, 0.2);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12.5px;
    }
    .markdown-body table {
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
      font-size: 13px;
    }
    .markdown-body th, .markdown-body td {
      border: 1px solid var(--card-border);
      padding: 10px 14px;
      text-align: left;
    }
    .markdown-body th {
      background: #1c2128;
      color: #f0f6fc;
      font-weight: 600;
    }
    .markdown-body tr:nth-child(even) {
      background: rgba(22, 27, 34, 0.6);
    }
    .raw-textarea {
      width: 100%;
      height: 600px;
      background: #090d13;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      color: #e6edf3;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12.5px;
      padding: 16px;
      line-height: 1.6;
      resize: vertical;
    }
    .alert-banner {
      padding: 14px 18px;
      border-radius: 8px;
      font-size: 13px;
      margin-bottom: 20px;
      display: none;
    }
    .alert-warn {
      background: rgba(210, 153, 34, 0.15);
      border: 1px solid rgba(210, 153, 34, 0.4);
      color: #e3b341;
    }
    .alert-success {
      background: rgba(46, 160, 67, 0.15);
      border: 1px solid rgba(46, 160, 67, 0.4);
      color: #3fb950;
    }
    .alert-error {
      background: rgba(248, 81, 73, 0.15);
      border: 1px solid rgba(248, 81, 73, 0.4);
      color: #f85149;
    }
    .spinner {
      border: 3px solid rgba(255,255,255,0.1);
      width: 18px;
      height: 18px;
      border-radius: 50%;
      border-left-color: #fff;
      animation: spin 0.8s linear infinite;
      display: none;
    }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-icon">🤖</div>
      <div>
        <h1>README Writer Agent</h1>
        <p>Deterministic AST Code Inspection • Cloud & Vercel Ready</p>
      </div>
    </div>
    <div class="header-badges">
      <span class="badge badge-green">🛡️ Security Guardrails Active</span>
      <span class="badge badge-purple">▲ Vercel Serverless Ready</span>
    </div>
  </header>

  <div class="container">

    <!-- INPUT CONFIGURATION CARD -->
    <div class="card">
      <div class="card-title">📁 Choose Source Mode</div>
      
      <!-- MODE SELECTION TABS -->
      <div class="mode-tabs">
        <button class="mode-tab-btn active" id="btnModeGithub" onclick="setMode('github')">🌐 GitHub URL (Recommended for Vercel)</button>
        <button class="mode-tab-btn" id="btnModeZip" onclick="setMode('zip')">📦 Upload Project (.zip)</button>
        <button class="mode-tab-btn" id="btnModeLocal" onclick="setMode('local')">💻 Local Filesystem Path</button>
      </div>

      <!-- MODE 1: GITHUB URL -->
      <div id="sectionGithub" class="form-group">
        <label for="githubUrl">Public GitHub Repository URL</label>
        <input type="text" id="githubUrl" placeholder="https://github.com/Abhijit2244/readme-writer-agent" value="https://github.com/Abhijit2244/readme-writer-agent">
        <div class="quick-chips">
          <span style="font-size: 11px; color: var(--text-muted); align-self: center;">Quick Test:</span>
          <span class="chip" onclick="setGithub('https://github.com/Abhijit2244/readme-writer-agent')">Abhijit2244/readme-writer-agent</span>
        </div>
      </div>

      <!-- MODE 2: UPLOAD ZIP -->
      <div id="sectionZip" class="form-group" style="display: none;">
        <label for="zipFile">Select Project Zip Archive (.zip)</label>
        <input type="file" id="zipFile" accept=".zip">
        <p style="font-size: 12px; color: var(--text-muted); margin-top: 6px;">
          Safe extraction with automated Zip-Slip path traversal defense.
        </p>
      </div>

      <!-- MODE 3: LOCAL PATH -->
      <div id="sectionLocal" class="form-group" style="display: none;">
        <label for="repoPath">Local Repository Filesystem Path</label>
        <input type="text" id="repoPath" placeholder="e.g. C:/Users/Username/Projects/my-project or /home/user/my-project" value="">
        <div style="background: rgba(210, 153, 34, 0.12); border: 1px solid rgba(210, 153, 34, 0.35); border-radius: 8px; padding: 10px 14px; margin-top: 10px; font-size: 12px; color: #e3b341; display: flex; align-items: flex-start; gap: 8px;">
          <span style="font-size: 15px;">⚠️</span>
          <span>
            <strong>Cloud Notice:</strong> Local filesystem paths (e.g. <code>C:/Users/...</code>) only work when running this server locally on your own machine. When hosted on cloud platforms like <strong>Vercel</strong>, the server cannot access your personal device's files unless cloned there—please use the <strong>🌐 GitHub URL</strong> or <strong>📦 Upload Project (.zip)</strong> tab!
          </span>
        </div>
      </div>

      <!-- GENERATION ENGINE TOGGLE (Local Deterministic vs Gemini AI) -->
      <div style="margin-top: 20px; border-top: 1px solid var(--card-border); padding-top: 16px;">
        <label style="font-weight: 600; font-size: 13.5px; color: #f0f6fc; margin-bottom: 8px; display: block;">
          ⚡ Analysis & Synthesis Engine:
        </label>
        <div class="engine-toggle-group">
          <div class="engine-btn active" id="btnEngineLocal" onclick="setEngine('local')">
            <div class="engine-btn-title">⚡ Local Deterministic AST Mode</div>
            <div class="engine-btn-sub">100% Offline • Free & Instant • Zero API keys required • Direct Python AST extraction</div>
          </div>
          <div class="engine-btn engine-gemini" id="btnEngineGemini" onclick="setEngine('gemini')">
            <div class="engine-btn-title">✨ Gemini 2.0 Flash AI Mode</div>
            <div class="engine-btn-sub">Google Gemini AI • Enriches undocumented functions & synthesizes executive summaries</div>
          </div>
        </div>
      </div>

      <div class="options-row">
        <label class="toggle-label">
          <input type="checkbox" id="forceOverwrite">
          <span><strong>Allow Overwrite Existing README</strong> (<code>--force</code>)</span>
        </label>
        <span style="font-size: 12px; color: var(--text-muted);">
          🔒 Default preserves existing <code>README.md</code> ➔ writes to <code>README.generated.md</code>
        </span>
      </div>

      <div class="btn-row">
        <button class="btn-primary" id="btnGenerate" onclick="dispatchGenerate()">
          <span class="spinner" id="genSpinner"></span>
          <span>⚡ Generate Production README</span>
        </button>
      </div>
    </div>

    <!-- ALERTS CONTAINER -->
    <div id="alertBox" class="alert-banner"></div>

    <!-- METRICS BAR (Hidden until generated) -->
    <div id="statsRow" class="stats-grid" style="display: none;">
      <div class="stat-card">
        <div class="stat-value" id="statEngine" style="font-size: 15px; font-weight: 600; line-height: 1.35; padding: 0 4px; color: #7ee787;">⚡ Local AST</div>
        <div class="stat-label">Active Engine</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="statFiles">0</div>
        <div class="stat-label">Sections Built</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="statEntities">0</div>
        <div class="stat-label">Classes & Functions</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="statStatus" style="font-size: 18px; font-weight: 700;">Safe</div>
        <div class="stat-label">Safety Decision</div>
      </div>
      <div class="stat-card">
        <div class="stat-value stat-filename-pill" id="statFile" title="README.md">README.md</div>
        <div class="stat-label">Target File</div>
      </div>
    </div>

    <!-- TELEMETRY LOG CARD -->
    <div class="card" id="telemetryCard" style="display: none;">
      <div class="card-title">📡 Real-Time Telemetry & AST Extraction Logs</div>
      <div class="terminal-box" id="telemetryLog"></div>
    </div>

    <!-- RESULTS & PREVIEW CARD (Hidden until generated) -->
    <div class="card" id="previewCard" style="display: none;">
      <div class="tab-header">
        <div class="tab-buttons">
          <button class="tab-btn active" id="tabBtnPreview" onclick="switchTab('preview')">👁️ Rendered HTML Preview</button>
          <button class="tab-btn" id="tabBtnRaw" onclick="switchTab('raw')">📝 Raw Markdown</button>
        </div>
        <div style="display: flex; gap: 10px;">
          <button class="btn-secondary" onclick="copyMarkdown()">📋 Copy Markdown</button>
          <button class="btn-download" id="btnDownload" onclick="triggerDownload()">📥 Download README.md</button>
        </div>
      </div>

      <!-- Tab 1: Rendered View -->
      <div id="tabPreview" class="tab-content active">
        <div class="markdown-body" id="markdownRendered"></div>
      </div>

      <!-- Tab 2: Raw Markdown View -->
      <div id="tabRaw" class="tab-content">
        <textarea class="raw-textarea" id="markdownRaw" readonly></textarea>
      </div>
    </div>

  </div>

  <script>
    if (typeof mermaid !== 'undefined') {
      try {
        mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' });
      } catch (e) {
        console.warn('Mermaid initialization notice:', e);
      }
    }

    let currentMode = 'github';
    let currentEngine = 'local';
    let currentSessionId = null;
    let currentMarkdownText = "";
    let currentOutputFilename = "README.md";

    // Auto-probe server environment key status on load
    window.addEventListener('DOMContentLoaded', () => {
      fetch('/health')
        .then(res => res.json())
        .then(data => {
          const badge = document.getElementById('envKeyStatusBadge');
          const input = document.getElementById('geminiApiKey');
          if (!badge || !input) return;
          if (data.gemini_env_configured) {
            badge.className = 'badge badge-green';
            badge.innerHTML = '🟢 Detected in .env / Vercel';
            input.placeholder = 'Auto-loaded from .env (leave blank or enter override)';
          } else {
            badge.className = 'badge';
            badge.style.background = 'rgba(210, 153, 34, 0.15)';
            badge.style.color = '#e3b341';
            badge.innerHTML = '⚪ Not in .env (enter key above)';
            input.placeholder = 'AIzaSy... (enter your Gemini API key)';
          }
        })
        .catch(e => console.warn('Health probe error:', e));
    });

    function setEngine(engine) {
      currentEngine = engine;
      const isGemini = (engine === 'gemini');
      document.getElementById('btnEngineLocal').classList.toggle('active', !isGemini);
      document.getElementById('btnEngineGemini').classList.toggle('active', isGemini);
      document.getElementById('geminiKeyContainer').style.display = isGemini ? 'block' : 'none';
    }

    function toggleApiKeyVisibility() {
      const input = document.getElementById('geminiApiKey');
      input.type = (input.type === 'password') ? 'text' : 'password';
    }

    function setMode(mode) {
      currentMode = mode;
      document.getElementById('btnModeGithub').classList.toggle('active', mode === 'github');
      document.getElementById('btnModeZip').classList.toggle('active', mode === 'zip');
      document.getElementById('btnModeLocal').classList.toggle('active', mode === 'local');

      document.getElementById('sectionGithub').style.display = (mode === 'github') ? 'block' : 'none';
      document.getElementById('sectionZip').style.display = (mode === 'zip') ? 'block' : 'none';
      document.getElementById('sectionLocal').style.display = (mode === 'local') ? 'block' : 'none';
    }

    function setGithub(url) {
      document.getElementById('githubUrl').value = url;
    }

    function setLocalPath(path) {
      document.getElementById('repoPath').value = path;
    }

    function showAlert(msg, type = 'warn') {
      const box = document.getElementById('alertBox');
      if (!box) return;
      box.className = `alert-banner alert-${type}`;
      box.innerHTML = msg;
      box.style.display = 'block';
      box.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function hideAlert() {
      const box = document.getElementById('alertBox');
      if (box) box.style.display = 'none';
    }

    function switchTab(tab) {
      document.getElementById('tabBtnPreview').classList.toggle('active', tab === 'preview');
      document.getElementById('tabBtnRaw').classList.toggle('active', tab === 'raw');
      document.getElementById('tabPreview').classList.toggle('active', tab === 'preview');
      document.getElementById('tabRaw').classList.toggle('active', tab === 'raw');
    }

    async function dispatchGenerate() {
      hideAlert();

      // Immediately clear and hide previous generation results
      currentSessionId = null;
      currentMarkdownText = "";
      document.getElementById('previewCard').style.display = 'none';
      document.getElementById('markdownRendered').innerHTML = '';
      document.getElementById('markdownRaw').value = '';
      document.getElementById('statsRow').style.display = 'none';

      const force = document.getElementById('forceOverwrite').checked;
      const btn = document.getElementById('btnGenerate');
      const spinner = document.getElementById('genSpinner');
      const term = document.getElementById('telemetryLog');

      const isGemini = (currentEngine === 'gemini');
      const keyInput = document.getElementById('geminiApiKey');
      const apiKey = keyInput ? keyInput.value.trim() : '';

      btn.disabled = true;
      spinner.style.display = 'inline-block';
      // Immediately hide previous results so stale content is never visible during a new run
      document.getElementById('statsRow').style.display = 'none';
      document.getElementById('previewCard').style.display = 'none';
      document.getElementById('telemetryCard').style.display = 'block';
      term.innerHTML = `[AGENT] Initializing new documentation run...\\n`;
      document.getElementById('telemetryCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });

      try {
        let endpoint = '/api/generate';
        let body = null;
        let headers = {};

        if (currentMode === 'github') {
          const ghUrl = document.getElementById('githubUrl').value.trim();
          if (!ghUrl) {
            showAlert('Please provide a valid GitHub repository URL.', 'error');
            return;
          }
          endpoint = '/api/generate-github';
          headers = { 'Content-Type': 'application/json' };
          body = JSON.stringify({
            github_url: ghUrl,
            force: force,
            use_gemini: isGemini,
            gemini_api_key: apiKey || null
          });
          term.innerHTML = `[AGENT] Fetching GitHub archive for: ${ghUrl}\\n[AGENT] Engine: ${isGemini ? '✨ Gemini 2.0 Flash AI' : '⚡ Local Deterministic AST'}\\n`;

        } else if (currentMode === 'zip') {
          const fileInput = document.getElementById('zipFile');
          if (!fileInput.files || fileInput.files.length === 0) {
            showAlert('Please select a .zip project file to upload.', 'error');
            return;
          }
          endpoint = '/api/upload-zip';
          const formData = new FormData();
          formData.append('file', fileInput.files[0]);
          formData.append('force', force);
          formData.append('use_gemini', isGemini);
          if (apiKey) {
            formData.append('gemini_api_key', apiKey);
          }
          body = formData;
          term.innerHTML = `[AGENT] Uploading and extracting project archive safely...\\n[AGENT] Engine: ${isGemini ? '✨ Gemini 2.0 Flash AI' : '⚡ Local Deterministic AST'}\\n`;

        } else {
          const localPath = document.getElementById('repoPath').value.trim();
          if (!localPath) {
            showAlert('Please provide a local repository filesystem path.', 'error');
            return;
          }
          endpoint = '/api/generate';
          headers = { 'Content-Type': 'application/json' };
          body = JSON.stringify({
            repo_path: localPath,
            force: force,
            use_gemini: isGemini,
            gemini_api_key: apiKey || null
          });
          term.innerHTML = `[AGENT] Initiating inspection for local path: ${localPath}\\n[AGENT] Engine: ${isGemini ? '✨ Gemini 2.0 Flash AI' : '⚡ Local Deterministic AST'}\\n`;
        }

        const res = await fetch(endpoint, {
          method: 'POST',
          headers: headers,
          body: body
        });

        const data = await res.json();
        if (!res.ok) {
          showAlert(`<strong>Generation Failed:</strong> ${data.detail || 'Server error'}`, 'error');
          term.innerHTML += `\\n[ERROR] ${data.detail || 'Server encountered an error.'}`;
          return;
        }

        // Display telemetry
        if (data.telemetry_logs && data.telemetry_logs.length) {
          term.innerHTML = data.telemetry_logs.map(l => `[${l.type}] ${typeof l.data === 'object' ? JSON.stringify(l.data) : l.data}`).join('\\n');
        }

        currentSessionId = data.session_id;
        currentMarkdownText = data.markdown_content;
        currentOutputFilename = data.output_filename;

        // Update stats
        document.getElementById('statsRow').style.display = 'grid';
        const engineElem = document.getElementById('statEngine');
        if (engineElem) {
          engineElem.innerText = data.engine_mode || (isGemini ? '✨ Gemini 2.0' : '⚡ Local AST');
          engineElem.style.color = (data.engine_mode && data.engine_mode.includes('Gemini')) ? '#d2a8ff' : '#7ee787';
        }
        document.getElementById('statFiles').innerText = data.sections_included.length;
        document.getElementById('statEntities').innerText = data.entities_documented_count;
        document.getElementById('statStatus').innerText = data.was_overwritten ? 'Overwritten' : (data.saved_as_alternate ? 'Preserved' : 'Clean');
        document.getElementById('statFile').innerText = data.output_filename;

        document.getElementById('btnDownload').innerText = `📥 Download ${data.output_filename}`;
        document.getElementById('markdownRaw').value = currentMarkdownText;

        // Render Markdown safely (with marked.js if loaded, or fallback pre block)
        const renderedContainer = document.getElementById('markdownRendered');
        if (typeof marked !== 'undefined') {
          renderedContainer.innerHTML = marked.parse(currentMarkdownText);
        } else {
          renderedContainer.innerHTML = '<pre style="white-space: pre-wrap; color: #c9d1d9; font-family: monospace;">' +
            currentMarkdownText.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") + '</pre>';
        }

        // Render Mermaid Diagrams if library is present
        if (typeof mermaid !== 'undefined') {
          const mermaidPreBlocks = renderedContainer.querySelectorAll('pre code.language-mermaid');
          mermaidPreBlocks.forEach((codeBlock, idx) => {
            const pre = codeBlock.parentElement;
            const graphDefinition = codeBlock.innerText;
            const mermaidDiv = document.createElement('div');
            mermaidDiv.className = 'mermaid';
            mermaidDiv.id = `mermaid-${idx}`;
            mermaidDiv.innerHTML = graphDefinition;
            pre.parentNode.replaceChild(mermaidDiv, pre);
          });

          try {
            mermaid.run();
          } catch (mErr) {
            console.warn('Mermaid rendering notice:', mErr);
          }
        }

        document.getElementById('previewCard').style.display = 'block';

        if (data.saved_as_alternate) {
          showAlert(`🛡️ <strong>Safety Preservation Active:</strong> An existing README was detected! The original file was preserved, and your new documentation was saved as <code>${data.output_filename}</code> [${data.engine_mode}].`, 'warn');
        } else if (data.was_overwritten) {
          showAlert(`⚠️ <strong>Explicit Overwrite:</strong> <code>${data.output_filename}</code> was overwritten as authorized via the <code>--force</code> setting [${data.engine_mode}].`, 'warn');
        } else {
          showAlert(`🎉 <strong>Success!</strong> Publication-ready documentation generated at <code>${data.output_filename}</code> with ${data.entities_documented_count} documented components via ${data.engine_mode}.`, 'success');
        }

        document.getElementById('previewCard').scrollIntoView({ behavior: 'smooth' });

      } catch (err) {
        showAlert(`Client request failure: ${err.message}`, 'error');
      } finally {
        btn.disabled = false;
        spinner.style.display = 'none';
      }
    }

    function triggerDownload() {
      if (!currentSessionId) {
        showAlert('No documentation session available for download.', 'error');
        return;
      }
      window.location.href = `/api/download?session_id=${encodeURIComponent(currentSessionId)}`;
    }

    function copyMarkdown() {
      if (!currentMarkdownText) return;
      navigator.clipboard.writeText(currentMarkdownText).then(() => {
        showAlert('📋 Markdown copied to clipboard!', 'success');
      }).catch(err => {
        showAlert('Could not copy to clipboard: ' + err, 'error');
      });
    }
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.get("/{full_path:path}")
def serve_react_assets(full_path: str):
    """Fallback route to serve static files from React build directory or SPA index."""
    candidate = os.path.join(DIST_DIR, full_path)
    if os.path.exists(candidate) and os.path.isfile(candidate):
        return FileResponse(candidate)
    if os.path.exists(DIST_INDEX):
        return FileResponse(DIST_INDEX)
    raise HTTPException(status_code=404, detail="File not found")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    logger.info(f"🚀 Starting Autonomous README Writer Agent Web Server on http://{host}:{port}")
    uvicorn.run("server:app", host=host, port=port, reload=False)
