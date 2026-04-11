"""Vercel serverless entrypoint for Vigil FastAPI app."""

from __future__ import annotations

import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
VIGIL_ROOT = CURRENT_FILE.parents[1]
PROJECT_PARENT = VIGIL_ROOT.parent

# Keep imports resilient for different deploy working directories.
if str(VIGIL_ROOT) not in sys.path:
    sys.path.insert(0, str(VIGIL_ROOT))
if str(PROJECT_PARENT) not in sys.path:
    sys.path.insert(0, str(PROJECT_PARENT))

try:
    from vigil.main import app
except ModuleNotFoundError:
    from main import app
