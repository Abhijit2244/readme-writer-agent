"""
Vercel Serverless Function Entry Point
======================================
Exposes the FastAPI application object for Vercel's Python runtime (@vercel/python).
"""

import sys
import os

# Ensure the parent directory (project root) is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from server import app

# Vercel looks for 'app' as the ASGI application entry point
