#!/usr/bin/env python3
"""
Hook script to nudge Claude toward using codemap.md for broad code searches.

This is a SOFT warning - it doesn't block, just reminds.
Only triggers on broad/exploratory searches that codemap answers better.

Token cost: ~20-30 tokens per warning, only fires 1-5 times per session.
"""

import os
import sys
import json
import re

# Broad code directories that codemap covers
CODE_DIRS = ["scrapers", "services", "cli", "db", "config", "streamlit_app"]

# Patterns that indicate broad exploratory search
BROAD_PATTERNS = [
    r"\*\*/\*\.py",              # **/*.py
    r"\*\.py$",                  # *.py at root
    r"class\s+\w+",             # class definitions
    r"def\s+\w+",               # function definitions
]


def is_broad_code_search(pattern: str, path: str = "") -> bool:
    """Detect searches that codemap would answer better."""

    # Searching entire code directories with wildcard?
    for code_dir in CODE_DIRS:
        # Match patterns like "scrapers/*", "scrapers/**", "services/*.py"
        if re.search(rf"{code_dir}/\*", pattern) or re.search(rf"{code_dir}/\*", path or ""):
            return True

    # Broad wildcard Python search?
    for broad in BROAD_PATTERNS:
        if re.search(broad, pattern):
            return True

    # Path-based broad search (e.g., path="scrapers" with pattern="*.py")
    if path:
        for code_dir in CODE_DIRS:
            if code_dir in path and ("*" in pattern or not pattern):
                return True

    return False


def main():
    """Check tool input and emit warning if appropriate."""

    try:
        # Get tool input from environment (Claude Code passes this as TOOL_INPUT)
        tool_input_str = os.environ.get("TOOL_INPUT", "{}")
        tool_input = json.loads(tool_input_str)

        # Extract pattern and path from Glob/Grep input
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")

        if is_broad_code_search(pattern, path):
            # Emit soft warning - short and actionable
            print("Tip: .claude/codemap.md has the full code index (files, classes, functions).")

    except Exception:
        # Never block on hook errors - fail silently
        pass

    # Always exit 0 (allow) - this is a soft nudge, not a blocker
    sys.exit(0)


if __name__ == "__main__":
    main()