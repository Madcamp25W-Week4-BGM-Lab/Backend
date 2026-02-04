from fastapi import APIRouter, HTTPException
from src.commit.schemas import CommitRequest, CommitTaskResponse, CommitPollResponse
from src.commit import services

router = APIRouter()

@router.post("/", response_model=CommitTaskResponse)
async def generate_commit(request: CommitRequest):
    task_id = await services.queue_commit_generation(request)
    return CommitTaskResponse(task_id=task_id)

@router.get("/{task_id}", response_model=CommitPollResponse)
async def get_commit_result(task_id: str):
    response = await services.get_commit_status(task_id)
    if not response:
        raise HTTPException(status_code=404, detail="Task not found")
    return response