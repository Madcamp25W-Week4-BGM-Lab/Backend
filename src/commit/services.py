import uuid
import time
from src.commit.schemas import CommitRequest
from src.infrastructure.queue import task_queue
from src.infrastructure.schemas import LLMTask, TaskStatus

async def queue_commit_generation(request: CommitRequest) -> str:
    # Build Prompt
    style_guide = f"Style: {request.config.style.convention}"
    