# Update Documentation

Review recent code changes and identify which documentation files need updating based on the Documentation Maintenance mapping in CLAUDE.md.

## Process

1. **Check Recent Changes**:
   - Run `git status` to see uncommitted changes
   - Run `git diff --name-only HEAD~5..HEAD` to see recent commits
   - Identify modified files in key areas

2. **Map Changes to Documentation**:

   **If modified files include**:
   - `app/models/usage_stats.py`, `app/services/usage_service.py`, `app/dependencies/usage.py`
     → Update: `docs/technical/account-tiers-implementation.md`

   - New E2E tests in `frontend/e2e/tests/`
     → Update: `docs/technical/e2e-testing-progress.md`

   - New backend tests in `backend/tests/test_*_endpoints.py`
     → Update: `docs/technical/backend-api-test-coverage.md`

   - `app/services/search_service.py`, search endpoints
     → Update: `docs/technical/api-specifications.md` and `CLAUDE.md`

   - Dockerfiles, docker-compose files, deployment scripts
     → Update: `DOCKER_IMPLEMENTATION_PLAN.md` or `SERVER_DEPLOYMENT_GUIDE.md`

   - Database migrations, new models
     → Update: `docs/technical/postgresql-migration-progress.md` and `CLAUDE.md`

   - New API endpoints/routers
     → Update: `CLAUDE.md` "API Endpoints Structure"

   - Critical patterns (privacy, search_vector, like_count, image storage, account tiers)
     → Update: `CLAUDE.md` "Critical Project-Specific Patterns"

3. **Provide Specific Recommendations**:
   - List each documentation file that needs updating
   - Specify which sections to modify
   - Suggest the type of update needed (status change, new content, clarification)

4. **Offer to Help**:
   - Ask if user wants help making the updates
   - Can draft update text for specific sections
   - Can update progress tracking (✅/⚠️/❌ status)

## Example Output Format

```
📋 Documentation Updates Needed:

Based on recent changes, the following docs need updating:

1. ✅ docs/technical/backend-api-test-coverage.md
   - Mark OCR endpoints as COMPLETED (tests added in test_ocr_endpoints.py)
   - Update progress: 19/25 endpoints (76% complete)

2. ⚠️ CLAUDE.md
   - Add new /api/notifications endpoint to "API Endpoints Structure"

3. 📝 docs/technical/account-tiers-implementation.md
   - Update status from 98% to 100% if Stripe integration is complete
   - Add notes about new email notification triggers

Would you like me to help make these updates?
```

## Notes

- This command analyzes git changes to detect what needs updating
- Follows the Documentation Maintenance mapping in CLAUDE.md
- Provides actionable, specific recommendations
- Can help draft the actual updates