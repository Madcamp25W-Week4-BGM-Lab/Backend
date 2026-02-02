from fastapi import APIRouter, HTTPException
from src.infrastructure.queue import task_queue
from src.infrastructure.schemas import LLMTask

router = APIRouter()

# --- CLIENT ENDPOINTS (VS Code calls these) ---

@router.get("/tasks/{task_id}", response_model=LLMTask)
async def get_task_status(task_id: str):
    """Client polls this to check if their request is done."""
    task = await task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# --- WORKER ENDPOINTS (GPU Server calls these) ---

@router.post("/queue/pop", response_model=LLMTask)
async def pop_task():
    """Worker asks: 'Any work for me?'"""
    task = await task_queue.pop_pending_task()
    if not task:
        raise HTTPException(status_code=404, detail="No pending tasks")
    return task

@router.post("/queue/complete/{task_id}")
async def complete_task(task_id: str, payload: dict):
    """Worker says: 'I finished this task!'"""
    result = payload.get("result")
    task = await task_queue.complete_task(task_id, result)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "ok"}