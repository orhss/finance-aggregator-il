"""
Sync endpoints.

POST /sync/{institution} - start a sync (runs fin-cli sync as subprocess)
GET  /sync/stream/{job_id} - SSE stream of progress
GET  /sync/history - sync history
"""

import asyncio
import json
import subprocess
import sys
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from api.deps import CurrentUser, get_analytics
from api.schemas.sync import SyncHistoryResponse, SyncRequest
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/sync", tags=["sync"])

# In-memory job registry (ephemeral, per-process)
_jobs: dict[str, dict] = {}


@router.get("/history", response_model=list[SyncHistoryResponse])
def sync_history(
    limit: int = 20,
    institution: Optional[str] = None,
    status: Optional[str] = None,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    records = analytics.get_sync_history(limit=limit, institution=institution, status=status)
    return [SyncHistoryResponse.model_validate(r) for r in records]


@router.post("/{institution}")
def start_sync(
    institution: str,
    body: SyncRequest = SyncRequest(),
    _: str = CurrentUser,
):
    """
    Start a sync job. Returns a job_id for streaming progress via SSE.
    The actual sync runs as a subprocess calling `fin-cli sync <institution>`.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "institution": institution,
        "started_at": datetime.utcnow().isoformat(),
        "status": "pending",
        "lines": [],
        "months_back": body.months_back,
    }
    return {"job_id": job_id, "institution": institution}


@router.get("/stream/{job_id}")
async def sync_stream(job_id: str, _: str = CurrentUser):
    """
    SSE stream for sync progress.
    Starts the subprocess and streams stdout as server-sent events.
    """
    async def event_generator():
        # Send a ping so the client knows the connection is alive
        yield _sse_event("ping", {"message": "connected"})

        job = _jobs.get(job_id)
        if not job:
            yield _sse_event("error", {"message": f"Job {job_id} not found"})
            return

        institution = job["institution"]
        _jobs[job_id]["status"] = "running"

        # Build the fin-cli command
        cmd = [sys.executable, "-m", "cli.main", "sync", institution]
        if job.get("months_back") is not None:
            cmd.extend(["--months-back", str(job["months_back"])])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            async for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").rstrip()
                _jobs[job_id]["lines"].append(line)
                yield _sse_event("progress", {"message": line, "institution": institution})

            await proc.wait()
            success = proc.returncode == 0
            _jobs[job_id]["status"] = "success" if success else "error"

            yield _sse_event(
                "success" if success else "error",
                {"message": "Sync completed" if success else "Sync failed", "institution": institution},
            )
        except Exception as exc:
            _jobs[job_id]["status"] = "error"
            yield _sse_event("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event_type: str, data: dict) -> str:
    payload = json.dumps(data)
    return f"event: {event_type}\ndata: {payload}\n\n"
