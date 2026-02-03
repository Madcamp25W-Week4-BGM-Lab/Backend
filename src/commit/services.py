import uuid
import time
from typing import Optional
from src.commit.schemas import CommitRequest, CommitPollResponse
from src.infrastructure.queue import task_queue
from src.infrastructure.schemas import LLMTask, TaskStatus

async def queue_commit_generation(request: CommitRequest) -> str:
    # Build Prompt -- two parts (system_text, user_text)
    system_text = (
        "You are a strict, semantic Git Commit Message Generator.\n"
        "Your ONLY goal is to describe the code changes accurately based on the provided diff.\n\n"
        
        "### CRITICAL SYNTAX RULES:\n"
        "1. Lines starting with `-` (minus) are DELETIONS. They strictly represent code that was REMOVED or REPLACED.\n"
        "2. Lines starting with `+` (plus) are ADDITIONS. They strictly represent NEW code.\n"
        "3. NEVER hallucinate features. If a line is removed (`-`), do not say it was added.\n"
        "4. Do NOT output markdown code blocks (```). Output ONLY the raw commit message.\n\n"
        
        "### FORMATTING:\n"
        f"- Convention: {request.config.style.convention}\n"
        f"- Use Emojis: {request.config.style.useEmojis}\n"
        f"- Language: {request.config.style.language}\n"
        "- Use IMPERATIVE mood (e.g., 'Fix bug', not 'Fixed bug').\n"
        "- Keep the subject line under 50 characters."
    )

    if request.config.rules:
         system_text += "\n\n### USER RULES:\n" + "\n".join([f"- {r}" for r in request.config.rules])

    user_text = (
        f"Project Context: {request.config.project_descriptions}\n\n"
        "Analyze the following Git Diff and generate the commit message:\n"
        "--- DIFF START ---\n"
        f"{request.diff}\n"
        "--- DIFF END ---"
    )

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
    
async def get_commit_status(task_id: str) -> Optional[CommitPollResponse]:
    # fetch generic task
    task = await task_queue.get_task(task_id)
    if not task:
        return None

    # unpack into Domain Schema 
    return CommitPollResponse(
        task_id=task.id,
        status=task.status.value,  # Convert Enum to string
        commit_message=task.result # Map 'result' -> 'commit_message'
    )