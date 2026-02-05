from enum import Enum
from pydantic import BaseModel
from typing import Optional

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class LLMTask(BaseModel):
    id: str
    domain: str          # e.g. "commit", "readme"
    task_type: Optional[str] = None
    status: TaskStatus
    system_instruction: Optional[str] = None
    user_message: str          # The raw text for the GPU
    result: Optional[str] = None
    created_at: float
