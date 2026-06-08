"""
本地 browser runner 的 HTTP 服务。

启动方式：
python -m app.local_runner.main
"""
from __future__ import annotations

from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.local_runner.runtime import LocalRunnerJob, RunnerLaunchPayload


class LaunchRequest(BaseModel):
    task_id: int
    backend_base_url: str = Field(..., min_length=1)
    runner_token: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)


app = FastAPI(title="Local Browser Runner", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

RUNNING_JOBS: dict[int, LocalRunnerJob] = {}


@app.middleware("http")
async def add_local_network_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response(status_code=204)
    else:
        response = await call_next(request)

    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    else:
        response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = request.headers.get(
        "access-control-request-headers",
        "content-type",
    )
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response


def _normalize_backend_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="backend_base_url 无效")
    return normalized


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "local-browser-runner",
        "active_tasks": list(RUNNING_JOBS.keys()),
    }


@app.post("/launch")
def launch(req: LaunchRequest):
    existing = RUNNING_JOBS.get(req.task_id)
    if existing and existing.thread and existing.thread.is_alive():
        return {
            "accepted": True,
            "message": "该任务已有执行器在运行",
            "task_id": req.task_id,
        }

    payload = RunnerLaunchPayload(
        task_id=req.task_id,
        backend_base_url=_normalize_backend_base_url(req.backend_base_url),
        runner_token=req.runner_token,
        session_id=req.session_id,
    )
    job = LocalRunnerJob(payload)
    RUNNING_JOBS[req.task_id] = job
    job.start()
    return {
        "accepted": True,
        "message": "本地执行器已启动",
        "task_id": req.task_id,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.local_runner.main:app", host="127.0.0.1", port=18765, reload=False)
