from enum import Enum
from typing import Optional, Literal, List

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
    short_description: Optional[str] = None
    repo_type: Literal["research", "library", "service"]

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


class AnalysisContext(BaseModel):
    primary_focus: Optional[str] = None
    intended_audience: Optional[str] = None
    problem_domain: Optional[str] = None

    model_config = {"extra": "forbid"}


class RepositoryFacts(BaseModel):
    keywords: Optional[List[str]] = None
    has_ml_code: Optional[bool] = None
    has_api_server: Optional[bool] = None
    has_sdk_exports: Optional[bool] = None
    has_cli: Optional[bool] = None

    model_config = {"extra": "forbid"}


class SemanticFacts(BaseModel):
    primary_responsibility: Optional[str] = None
    problem_reduced: Optional[str] = None
    non_goals: Optional[List[str]] = None
    confidence: Optional[Literal["low", "medium", "high"]] = None

    model_config = {"extra": "forbid"}


class FileSystemSignals(BaseModel):
    has_dockerfile: Optional[bool] = None
    has_k8s_manifests: Optional[bool] = None
    has_celery_or_queue: Optional[bool] = None
    has_multiple_services: Optional[bool] = None
    has_client: Optional[bool] = None

    model_config = {"extra": "forbid"}


class DiagramIntent(BaseModel):
    type: Literal["architecture", "pipeline", "training_flow", "request_flow"]
    complexity: Literal["simple", "standard", "detailed"]
    elements: List[str]

    model_config = {"extra": "forbid"}


class RepositoryIntent(BaseModel):
    adds_on_top_of: List[str]
    primary_responsibility: str
    what_it_is_not: List[str]

    model_config = {"extra": "forbid"}


class IntentAnalysis(BaseModel):
    repository_intent: RepositoryIntent
    problem_domain: str
    intended_audience: str
    abstraction_level: Literal["low", "medium", "high"]
    keywords: List[str]

    model_config = {"extra": "forbid"}


class FactJson(BaseModel):
    repository: RepositoryInfo
    analysis_context: Optional[AnalysisContext] = None
    facts: Optional[RepositoryFacts] = None
    semantic_facts: Optional[SemanticFacts] = None
    fs_signals: Optional[FileSystemSignals] = None
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
