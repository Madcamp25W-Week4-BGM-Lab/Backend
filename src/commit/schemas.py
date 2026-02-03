from pydantic import BaseModel
from typing import List, Optional

class CommitStyle(BaseModel):
    convention: str                     # conventional, angular, gitmoji
    language: str                       # en, kr, ...
    casing: str = "lower"               # lower, higher
    max_length: int = 50                # any commit length
    ticket_prefix: Optional[str] = None # AUTH, PROJ, ... 

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

