from enum import Enum
from typing import Optional, Literal

from pydantic import BaseModel, Field


class Mode(str, Enum):
    draft = "draft"
    final = "final"


class DocTarget(str, Enum):
    developer = "developer"
    designer = "designer"
    general = "general"
    extension = "extension"


class RepositoryInfo(BaseModel):
    # Required repository metadata
    name: Optional[str] = None
    type: Literal["research", "library", "service"]

    model_config = {"extra": "forbid"}


class FrontendRuntime(BaseModel):
    # Optional frontend runtime details
    framework: Optional[str] = None
    bundler: Optional[str] = None

    model_config = {"extra": "forbid"}


class BackendRuntime(BaseModel):
    # Optional backend runtime details
    framework: Optional[str] = None
    language: Optional[str] = None
    runtime: Optional[str] = None

    model_config = {"extra": "forbid"}


class RuntimeInfo(BaseModel):
    # Runtime can be partially present (frontend/backed or both)
    frontend: Optional[FrontendRuntime] = None
    backend: Optional[BackendRuntime] = None

    model_config = {"extra": "forbid"}


class ScriptsInfo(BaseModel):
    # Common package scripts (nullable)
    dev: Optional[str] = None
    build: Optional[str] = None
    start: Optional[str] = None

    model_config = {"extra": "forbid"}


class FactJson(BaseModel):
    repository: RepositoryInfo
    runtime: Optional[RuntimeInfo] = None
    scripts: Optional[ScriptsInfo] = None

    model_config = {"extra": "forbid"}


class ReadmeGenerateRequest(BaseModel):
    fact: FactJson
    mode: Mode
    doc_target: DocTarget
    async_mode: bool = Field(False, alias="async")

    model_config = {"extra": "forbid"}


class ReadmeGenerateResponse(BaseModel):
    content: Optional[str] = None
    task_id: Optional[str] = None
    template: str
    fallback: bool

    model_config = {"extra": "forbid"}

class ReadmePollResponse(BaseModel):
    task_id: str
    status: str
    content: Optional[str] = None
    error: Optional[str] = None
