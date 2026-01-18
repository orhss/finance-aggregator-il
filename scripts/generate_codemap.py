#!/usr/bin/env python3
"""
Codemap Generator

Generates a token-efficient codemap for Claude Code navigation.
Uses AST parsing to extract module summaries without LLM costs.
Auto-discovers directories, respecting .gitignore and .dockerignore.

Usage:
    python scripts/generate_codemap.py
"""

import ast
import fnmatch
from datetime import datetime
from pathlib import Path

# Project root (script is in scripts/)
PROJECT_ROOT = Path(__file__).parent.parent

# Output path
CODEMAP_PATH = PROJECT_ROOT / '.claude' / 'codemap.md'


def parse_ignore_file(filepath: Path) -> set[str]:
    """Parse a .gitignore or .dockerignore file, return directory patterns."""
    ignored = set()
    if not filepath.exists():
        return ignored

    for line in filepath.read_text().splitlines():
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue
        # Skip negation patterns
        if line.startswith('!'):
            continue
        # Extract directory name from patterns like "dir/", "dir/*", ".dir"
        dirname = line.rstrip('/').rstrip('*').rstrip('/')
        if dirname and not '*' in dirname:
            ignored.add(dirname)

    return ignored


def get_ignored_directories() -> set[str]:
    """Get set of directories to ignore from .gitignore and .dockerignore."""
    ignored = set()
    ignored.update(parse_ignore_file(PROJECT_ROOT / '.gitignore'))
    ignored.update(parse_ignore_file(PROJECT_ROOT / '.dockerignore'))

    # Always ignore these regardless
    ignored.update({'.git', '.claude', 'scripts'})

    return ignored


def infer_description(path: Path) -> str:
    """Infer description from __init__.py docstring or pyproject.toml."""
    init_file = path / '__init__.py'
    if init_file.exists():
        try:
            tree = ast.parse(init_file.read_text(encoding='utf-8'))
            docstring = ast.get_docstring(tree)
            if docstring:
                return docstring.split('\n')[0][:50]
        except (SyntaxError, UnicodeDecodeError):
            pass
    return ""


def discover_directories() -> dict[str, str]:
    """Auto-discover Python package directories, respecting ignore files."""
    ignored = get_ignored_directories()
    dirs = {}

    for path in sorted(PROJECT_ROOT.iterdir()):
        if not path.is_dir():
            continue

        name = path.name

        # Skip hidden dirs and ignored patterns
        if name.startswith('.') or name.startswith('_'):
            continue
        if name in ignored:
            continue

        # Must contain Python files
        py_files = list(path.rglob('*.py'))
        if not py_files:
            continue

        description = infer_description(path)
        dirs[name] = description

    return dirs


def extract_module_info(file_path: Path) -> dict | None:
    """Extract docstring and key definitions from a Python file using AST."""
    try:
        source = file_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return None

    # Get module docstring
    docstring = ast.get_docstring(tree) or ""
    if docstring:
        # Take first line only, truncate
        docstring = docstring.split('\n')[0][:60]

    # Extract classes and top-level functions
    classes = []
    functions = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
            functions.append(node.name)

    if not classes and not functions and not docstring:
        return None

    return {
        'docstring': docstring,
        'classes': classes[:5],  # Limit to 5
        'functions': functions[:5],  # Limit to 5
    }


def format_module_line(rel_path: Path, info: dict) -> str:
    """Format a single module line in compressed format."""
    parts = []

    if info['classes']:
        parts.append(f"class:{','.join(info['classes'])}")
    if info['functions']:
        parts.append(f"fn:{','.join(info['functions'])}")

    content = ' | '.join(parts) if parts else info['docstring']

    return f"- {rel_path}: {content}"


def scan_directory(dir_path: Path, description: str) -> list[str]:
    """Scan a directory and return formatted lines."""
    header = f"## {dir_path.name}/"
    if description:
        header += f" - {description}"
    lines = [header]

    if not dir_path.exists():
        lines.append("- (not found)")
        return lines

    # Get all Python files, sorted
    py_files = sorted(dir_path.rglob('*.py'))

    for py_file in py_files:
        if py_file.stem == '__init__':
            continue

        rel_path = py_file.relative_to(PROJECT_ROOT)
        info = extract_module_info(py_file)

        if info:
            lines.append(format_module_line(rel_path, info))

    if len(lines) == 1:
        lines.append("- (no modules)")

    return lines


def generate_codemap() -> str:
    """Generate the full codemap content."""
    lines = [
        "# Fin Codemap",
        "# USE THIS FILE to check if files/directories exist",
        "# Do NOT use Glob/Grep for file existence checks",
        f"# Auto-generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "# Refresh: python scripts/generate_codemap.py",
        "",
        "## Flow",
        "scrapers → services → db → cli/streamlit_app",
        "",
        "## Key Patterns",
        "- Credit cards: Selenium login → token extract → API calls",
        "- Pensions: Email MFA via IMAP (Migdal, Phoenix)",
        "- Brokers: Pure REST API clients",
        "",
    ]

    # Auto-discover and scan directories
    directories = discover_directories()

    for dir_name, description in directories.items():
        dir_path = PROJECT_ROOT / dir_name
        lines.extend(scan_directory(dir_path, description))
        lines.append("")

    return '\n'.join(lines)


def main():
    """Main entry point."""
    # Ensure .claude directory exists
    CODEMAP_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Generate and write codemap
    content = generate_codemap()
    CODEMAP_PATH.write_text(content, encoding='utf-8')

    # Report
    line_count = len(content.split('\n'))
    print(f"Updated {CODEMAP_PATH.relative_to(PROJECT_ROOT)} ({line_count} lines)")


if __name__ == '__main__':
    main()