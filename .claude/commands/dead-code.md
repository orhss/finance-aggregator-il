# Dead Code Detection and Removal

Detect and remove unused code using vulture.

## Step 1: Run vulture

Run vulture with 80% minimum confidence, including the whitelist for known false positives:

```bash
pipx run vulture . .vulture_whitelist.py --min-confidence 80 --exclude ".venv,venv,__pycache__,node_modules,.git"
```

The `.vulture_whitelist.py` file contains intentionally "unused" items like:
- Pytest fixtures used for side effects (patching)
- Smoke test imports that verify module loading

## Step 2: Review output

Analyze the vulture output. For each item reported:

1. **Verify it's truly unused** - Search for references in the codebase
2. **Categorize**:
   - `unused import` - Safe to remove
   - `unused variable` - Safe to remove (check it's not a side effect)
   - `unused function` - Verify not called dynamically or via decorators
   - `unused class` - Verify not instantiated dynamically
   - `unused attribute` - Check not accessed via `getattr` or similar

## Step 3: Remove confirmed dead code

For each verified unused item:
1. Read the file
2. Remove the unused code
3. Clean up any orphaned imports that result from removal

## Important considerations

- **Skip test files** - Test functions may appear unused but are discovered by pytest
- **Skip `__init__.py` exports** - These expose API, not unused
- **Skip CLI entry points** - Functions called by Typer/Click decorators
- **Skip abstract methods** - Implementations may exist in subclasses
- **Skip dataclass fields** - May be used for serialization

## Adding to whitelist

If you find a false positive that will recur, add it to `.vulture_whitelist.py`:

```python
# Description of why this is intentionally unused
some_identifier  # noqa
```

## After cleanup

Run the tests to ensure nothing broke:

```bash
pytest tests/ -x
```