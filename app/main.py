import json
import uuid
import asyncio
import os
from datetime import datetime, timezone

import redis
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.worker import run_job, resume_job

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True
)

app = FastAPI(
    title="API Multiagente - Pre-entrega 7",
    description="API REST para ejecutar un sistema multiagente con LangGraph, Redis y aprobación humana.",
    version="1.0.0"
)


class TaskRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)


class ApprovalRequest(BaseModel):
    approved: bool


def get_job(job_id: str):
    raw_data = redis_client.get(f"job:{job_id}")
    return json.loads(raw_data) if raw_data else None


@app.get("/health")
async def health():
    try:
        await asyncio.to_thread(redis_client.ping)
        return {
            "status": "ok",
            "redis": "connected"
        }
    except redis.RedisError:
        raise HTTPException(
            status_code=503,
            detail="Redis no está disponible."
        )


@app.post("/tasks", status_code=202)
async def create_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks
):
    job_id = str(uuid.uuid4())

    job = {
        "job_id": job_id,
        "query": request.query,
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
        "error": None
    }

    try:
        await asyncio.to_thread(
            redis_client.set,
            f"job:{job_id}",
            json.dumps(job, ensure_ascii=False)
        )
    except redis.RedisError:
        raise HTTPException(
            status_code=503,
            detail="No se pudo guardar la tarea en Redis."
        )

    background_tasks.add_task(
        run_job,
        job_id,
        request.query
    )

    return {
        "message": "Tarea recibida y encolada.",
        "job_id": job_id,
        "status": "PENDING"
    }


@app.get("/tasks/{job_id}")
async def task_status(job_id: str):
    try:
        job = await asyncio.to_thread(get_job, job_id)
    except redis.RedisError:
        raise HTTPException(
            status_code=503,
            detail="Redis no está disponible."
        )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="No existe una tarea con ese ID."
        )

    return job


@app.post("/tasks/{job_id}/approve", status_code=202)
async def approve_task(
    job_id: str,
    request: ApprovalRequest,
    background_tasks: BackgroundTasks
):
    try:
        job = await asyncio.to_thread(get_job, job_id)
    except redis.RedisError:
        raise HTTPException(
            status_code=503,
            detail="Redis no está disponible."
        )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="No existe una tarea con ese ID."
        )

    if job["status"] != "WAITING_APPROVAL":
        raise HTTPException(
            status_code=409,
            detail="La tarea no está esperando aprobación."
        )

    background_tasks.add_task(
        resume_job,
        job_id,
        request.approved
    )

    return {
        "message": "Decisión recibida. Se está reanudando la tarea.",
        "job_id": job_id,
        "approved": request.approved
    }
