import os
import json
import traceback

from dotenv import load_dotenv
from redis import Redis
from langgraph.types import Command

from app.observability import configure_observability
from app.graph import build_graph
from app.redis_checkpointer import RedisCheckpointer

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = Redis.from_url(
    REDIS_URL,
    decode_responses=False,
)


def get_job(job_id: str):
    raw_data = redis_client.get(f"job:{job_id}")
    return json.loads(raw_data) if raw_data else None


def save_job(job_id: str, job: dict):
    redis_client.set(
        f"job:{job_id}",
        json.dumps(job, ensure_ascii=False, default=str),
    )


def collect_interrupts(graph, config):
    snapshot = graph.get_state(config)
    interruptions = []

    for task in snapshot.tasks:
        for interruption in task.interrupts:
            interruptions.append({"value": interruption.value})

    return interruptions


def update_result(job, result):
    interruptions = result.get("__interrupt__", [])

    if interruptions:
        job["status"] = "WAITING_APPROVAL"
        job["interrupts"] = [
            {"value": interruption.value}
            for interruption in interruptions
        ]
    else:
        job["status"] = "COMPLETED"
        job["result"] = result.get("final_answer", "")
        job["metrics"] = result.get("analysis_results", {})

    return job


def run_job(job_id: str, query: str):
    lock_key = f"job-lock:{job_id}"

    if not redis_client.set(lock_key, "1", nx=True, ex=600):
        return

    try:
        job = get_job(job_id)

        if not job:
            return

        job["status"] = "RUNNING"
        save_job(job_id, job)

        configure_observability()

        checkpointer = RedisCheckpointer(redis_client)
        graph = build_graph(checkpointer=checkpointer)

        config = {
            "configurable": {
                "thread_id": job_id,
            }
        }

        result = graph.invoke(
            {"user_query": query},
            config=config,
        )

        job = update_result(job, result)
        save_job(job_id, job)

    except Exception as error:
        job = get_job(job_id) or {"job_id": job_id}
        job["status"] = "FAILED"
        job["error"] = str(error)
        job["traceback"] = traceback.format_exc()
        save_job(job_id, job)

    finally:
        redis_client.delete(lock_key)


def resume_job(job_id: str, approved: bool):
    lock_key = f"job-lock:{job_id}"

    if not redis_client.set(lock_key, "1", nx=True, ex=600):
        return

    try:
        job = get_job(job_id)

        if not job:
            raise ValueError("No existe la tarea.")

        if job["status"] != "WAITING_APPROVAL":
            raise ValueError("La tarea no está esperando aprobación.")

        job["status"] = "RUNNING"
        save_job(job_id, job)

        configure_observability()

        checkpointer = RedisCheckpointer(redis_client)
        graph = build_graph(checkpointer=checkpointer)

        config = {
            "configurable": {
                "thread_id": job_id,
            }
        }

        result = graph.invoke(
            Command(resume={"approved": approved}),
            config=config,
        )

        job = update_result(job, result)
        save_job(job_id, job)

        return job

    except Exception as error:
        job = get_job(job_id) or {"job_id": job_id}
        job["status"] = "FAILED"
        job["error"] = str(error)
        job["traceback"] = traceback.format_exc()
        save_job(job_id, job)
        raise

    finally:
        redis_client.delete(lock_key)
