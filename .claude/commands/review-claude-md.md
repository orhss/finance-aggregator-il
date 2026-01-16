---
description: Review and optimize CLAUDE.md following 2026 best practices
---

Review the CLAUDE.md file and ensure it follows best practices:

## Core Principles

**CLAUDE.md Purpose**: Onboard Claude into your codebase by defining:
- **WHY**: Project goals and critical architectural decisions
- **WHAT**: Tech stack, structure, and essential commands
- **HOW**: Non-standard patterns and where to find detailed information

**Guiding Philosophy**:
- **Less is More**: Include as few instructions as reasonably possible while maintaining clarity
- **Universal Applicability**: Keep contents concise and applicable across the entire project
- **Progressive Disclosure**: Tell Claude how to find information (@ references), not all the information itself
- **Rationale**: Avoid bloating context window and instruction count by deferring details to referenced files

## Evaluation Criteria

1. **Length Check**: File should be under 300 lines. Report current line count.

2. **Content Quality**:
   - Remove generic programming advice (PEP 8, "write clean code", etc.)
   - Keep only project-specific patterns and gotchas
   - Ensure commands are exact and actionable
   - Verify progressive disclosure is used (@ references)

3. **Progressive Disclosure**:
   - Check that detailed content is moved to referenced files
   - Verify @ syntax is used correctly with explicit "when to read" guidance
   - Ensure references are one level deep (no daisy-chaining)

4. **Outdated Information**:
   - Check for commands that no longer work
   - Verify file paths still exist
   - Confirm tech stack versions are current
   - Remove completed TODOs or deprecated patterns

5. **Critical Gotchas**:
   - Ensure non-standard patterns are documented
   - Verify protected directories are listed
   - Check that easy-to-miss patterns are highlighted

## Actions to Take

1. Read and analyze current CLAUDE.md
2. Check referenced files exist and are relevant
3. Report findings with specific line numbers
4. Suggest specific edits or deletions
5. If issues found, ask if user wants you to apply fixes

Focus on making the file more concise and leveraging progressive disclosure where possible.