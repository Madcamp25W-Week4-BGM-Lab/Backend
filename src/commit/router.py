from fastapi import APIRouter
from src.commit.schemas import CommitRequest, CommitTaskResponse
from src.commit import services

router = APIRouter()

@router.post("/generate-commit", response_model=CommitTaskResponse)
async def generate_commit(request: CommitRequest):
    task_id = await services.queue_commit_generation(request)
    return CommitTaskResponse(task_id=task_id)