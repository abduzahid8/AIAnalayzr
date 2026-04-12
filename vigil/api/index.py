"""Vercel serverless entrypoint for Vigil FastAPI app."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
VIGIL_ROOT = CURRENT_FILE.parents[1]

# Keep imports resilient for different deploy working directories.
if str(VIGIL_ROOT) not in sys.path:
    sys.path.insert(0, str(VIGIL_ROOT))

# When Vercel deploys with `vigil` as the project root, there is no parent
# directory named `vigil` on sys.path. Create a lightweight package shim so
# imports like `from vigil.core.config import settings` still resolve.
package = sys.modules.get("vigil")
if package is None:
    package = types.ModuleType("vigil")
    package.__path__ = [str(VIGIL_ROOT)]
    sys.modules["vigil"] = package

app = importlib.import_module("vigil.main").app
