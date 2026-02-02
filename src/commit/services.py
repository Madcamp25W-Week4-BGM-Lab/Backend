import uuid
import time
from src.commit.schemas import CommitRequest
from src.infrastructure.queue import task_queue
from src.infrastructure.schemas import LLMTask, TaskStatus

async def queue_commit_generation(request: CommitRequest) -> str:
    # Build Prompt -- two parts (system_text, user_text)
    system_text = (
        f"Project Context: {request.config.project_descriptions}\n"
        f"Style Guide: {request.config.style.convention} + (Emojis: {request.config.style.useEmojis})\n"
        f"Rules:\n" + "\n".join([f"- {r}" for r in request.config.rules])
    )

    user_text = f"Generate a commit message for this diff:\n\n{request.diff}"

    # Push to queue
    task = LLMTask(
        id=str(uuid.uuid4()),
        domain="commit",
        status=TaskStatus.PENDING,
        system_instruction=system_text,
        user_message=user_text,
        created_at=time.time()
    )

    await task_queue.add_task(task)
    return task.id
    
    