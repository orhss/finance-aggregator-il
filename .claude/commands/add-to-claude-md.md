---
description: Add a new pattern or gotcha to CLAUDE.md
---

Add the information to CLAUDE.md in the appropriate section:

## Instructions

1. Ask the user what they want to add (pattern, gotcha, command, or reference)

2. Determine the best section:
   - **Essential Commands** - If it's a new command to run
   - **Critical Project-Specific Patterns** - If it's a non-standard pattern
   - **Key Project Gotchas** - If it's something easy to miss or break
   - **When to Reference Other Files** - If it's a new @ reference

3. Keep the addition concise (1-3 lines max)

4. If the information is detailed, suggest creating a separate doc and adding an @ reference instead

5. After adding, check if file exceeds 300 lines and suggest moving content to progressive disclosure if needed

## Examples

**Good additions** (concise, project-specific):
- "Recipe ingredient units are NOT validated - handle unit conversion client-side"
- "Always run `pytest --lf` after fixing a bug to verify the fix"
- "Read @docs/api-auth.md when implementing new authenticated endpoints"

**Bad additions** (too generic or verbose):
- "Follow best practices for error handling" (too generic)
- Long paragraphs about general architecture (should be in separate doc)