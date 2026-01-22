#!/usr/bin/env python3
"""
Hook script to enforce codemap usage for broad code searches.

BLOCKING mode with grace period:
- Blocks broad code searches initially (exit 2)
- After a block, allows searches for GRACE_PERIOD seconds
- Grace period resets after expiry
"""

import sys
import json
import re
import os
import time

CODE_DIRS = ["scrapers", "services", "cli", "db", "config", "streamlit_app"]

BROAD_PATTERNS = [
    r"\*\*/\*\.py",
    r"\*\.py$",
    r"class\s+\w+",
    r"def\s+\w+",
]

GRACE_FILE = "/tmp/.codemap_grace"
GRACE_PERIOD = 30  # seconds


def is_broad_code_search(pattern: str, path: str = "") -> bool:
    """
    Detect searches that codemap would answer better.

    Args:
        pattern: Glob/grep pattern being searched
        path: Optional path being searched in

    Returns:
        True if search is broad enough that codemap should be consulted first
    """
    for code_dir in CODE_DIRS:
        if re.search(rf"{code_dir}/\*", pattern) or re.search(rf"{code_dir}/\*", path or ""):
            return True

    for broad in BROAD_PATTERNS:
        if re.search(broad, pattern):
            return True

    if path:
        for code_dir in CODE_DIRS:
            if code_dir in path and ("*" in pattern or not pattern):
                return True

    return False


def is_in_grace_period() -> bool:
    """
    Check if within grace period after a block.

    Returns:
        True if grace file exists and is younger than GRACE_PERIOD
    """
    if not os.path.exists(GRACE_FILE):
        return False

    try:
        mtime = os.path.getmtime(GRACE_FILE)
        return (time.time() - mtime) < GRACE_PERIOD
    except OSError:
        return False


def start_grace_period() -> None:
    """Create/touch the grace file to start a new grace period."""
    open(GRACE_FILE, "w").close()


def main() -> None:
    """Check tool input and block broad searches unless in grace period."""
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Task/Explore agent check
        if tool_name == "Task" and tool_input.get("subagent_type") == "Explore":
            if is_in_grace_period():
                sys.exit(0)
            start_grace_period()
            print(f"BLOCKED: Read .claude/codemap.md first. {GRACE_PERIOD}s grace period to retry.", file=sys.stderr)
            sys.exit(2)

        # Glob/Grep check
        pattern = tool_input.get("pattern", "")
        path = tool_input.get("path", "")

        if is_broad_code_search(pattern, path):
            if is_in_grace_period():
                sys.exit(0)
            start_grace_period()
            print(f"BLOCKED: Broad code search. Read .claude/codemap.md first. {GRACE_PERIOD}s grace period to retry.", file=sys.stderr)
            sys.exit(2)

    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()