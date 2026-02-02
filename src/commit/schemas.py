from pydantic import BaseModel
from typing import List, Optional

class CommitStyle(BaseModel):
    convention: str
    useEmojis: bool
    language: str

class SubTextConfig(BaseModel):
    project_descriptions: str 
    style: CommitStyle
    rules: List[str]

class CommitRequest(BaseModel):
    diff: str
    config: SubTextConfig
    history: List[str]

class CommitTaskResponse(BaseModel):
    task_id: str
    status: str = "pending"
    message: str = "Request queued."

# Polling for client-server commit
class CommitPollResponse(BaseModel):
    task_id: str
    status: str
    commit_message: Optional[str] = None
    error: Optional[str] = None

