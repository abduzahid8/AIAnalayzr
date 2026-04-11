"""Externalized agent prompts – loaded at runtime.

This directory contains the system prompts for all agents.
By keeping prompts separate from code:
  - Prompts can be .gitignored for proprietary deployments
  - Prompts can be A/B tested without code changes
  - Competitors who clone the repo get empty prompt files
"""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt file by name.  Falls back to empty string if missing."""
    path = PROMPTS_DIR / f"{name}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""
