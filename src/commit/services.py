import uuid
import time
from typing import Optional
from src.commit.schemas import CommitRequest, CommitPollResponse
from src.infrastructure.queue import task_queue
from src.infrastructure.schemas import LLMTask, TaskStatus

async def queue_commit_generation(request: CommitRequest) -> str:
    # Build Prompt -- two parts (system_text, user_text)
    # Convention Logic (gitmoji, conventional, angular)
    convention_instruction = ""
    if request.config.style.convention == "gitmoji":
        convention_instruction = "Start the message with a Gitmoji (e.g., ✨ for features, 🐛 for bugs)."
    if request.config.style.convention in ["conventional", "angular"]:
        convention_instruction = (
            "Format: <type>(<scope>): <subject>\n"
            "Types: feat, fix, docs, style, refactor, test, chore.\n"
            "CRITICAL: If generating multiple lines, EVERY line must strictly follow this format." # <--- ADD THIS
        )

    # Language Logic
    lang_instruction = ""
    if request.config.style.language != "en":
        lang_instruction = f"Output the commit message strictly in {request.config.style.language}."

    # Emoji Logic
    emoji_instruction = f"{request.config.style.useEmojis}"
    if request.config.style.useEmojis and request.config.style.convention != "gitmoji":
        # Explicitly tell the model WHERE to put the emoji to avoid format conflicts
        emoji_instruction += " (If true, place the emoji at the start of the <subject> part, AFTER the colon)"

    # ==> System Prompt
    system_text = (
        "You are a helpful Git Commit Message Generator.\n"
        "Your goal is to describe the code changes based on the diff, adhering to the User's specific style rules.\n\n"
        
        "### CRITICAL SYNTAX RULES:\n"
        "1. Lines starting with `-` (minus) are DELETIONS. They strictly represent code that was REMOVED or REPLACED.\n"
        "2. Lines starting with `+` (plus) are ADDITIONS. They strictly represent NEW code.\n"
        "3. NEVER hallucinate features. If a line is removed (`-`), do not say it was added.\n"
        "4. Do NOT output markdown code blocks (```). Output ONLY the raw commit message.\n\n"
        
        "### FORMATTING:\n"
        f"- Convention: {convention_instruction}\n"
        f"- Use Emojis: {emoji_instruction}\n"
        f"- Language: {lang_instruction}\n"
        "- Use IMPERATIVE mood (e.g., 'Fix bug', not 'Fixed bug').\n"
        "- Keep the subject line under 50 characters."
    )

    if request.config.rules:
         system_text += (
             "\n\n### USER RULES (High Priority):\n"
             "These rules OVERRIDE standard conventions if they conflict.\n" + 
             "\n".join([f"- {r}" for r in request.config.rules])
         )
         
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