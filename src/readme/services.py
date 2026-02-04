import json
import time
import uuid
from typing import Tuple

from src.readme.schemas import (
    FactJson,
    DocTarget,
    FrontendRuntime,
    BackendRuntime,
    ReadmePollResponse
)
from src.infrastructure.queue import task_queue
from src.infrastructure.schemas import LLMTask, TaskStatus


# Allowed repository types to prevent unexpected or invalid values.
ALLOWED_REPOSITORY_TYPES = {
    "web",
    "backend",
    "frontend",
    "mobile",
    "cli",
    "library",
    "desktop",
    "service",
    "api",
    "tool",
}


# Fixed README templates; content must not deviate from these structures.
TEMPLATE_DEVELOPER_V1 = """# {name}

## Overview
{overview}

## Repository
- Name: {name}
- Type: {repo_type}

## Runtime
- Frontend: {frontend_summary}
- Backend: {backend_summary}

## Scripts
- Dev: {script_dev}
- Build: {script_build}
- Start: {script_start}
"""

TEMPLATE_DESIGNER_V1 = """# {name}

## Summary
{overview}

## Tech Snapshot
- Frontend: {frontend_summary}
- Backend: {backend_summary}

## Scripts
- Dev: {script_dev}
- Build: {script_build}
- Start: {script_start}
"""

TEMPLATE_GENERAL_V1 = """# {name}

## Overview
{overview}

## Runtime
- Frontend: {frontend_summary}
- Backend: {backend_summary}

## How to Run
- Dev: {script_dev}
- Build: {script_build}
- Start: {script_start}
"""

TEMPLATE_EXTENSION_V1 = """# {name}

## Overview
{overview}

## Runtime
- Frontend: {frontend_summary}
- Backend: {backend_summary}

## Scripts
- Dev: {script_dev}
- Build: {script_build}
- Start: {script_start}
"""


def validate_fact(fact: FactJson) -> None:
    """
    Validate Fact JSON beyond basic schema checks.
    Raises ValueError with a human-readable message on failure.
    """
    errors = []

    if not fact.repository:
        errors.append("repository is required")
    else:
        if not fact.repository.name or not fact.repository.name.strip():
            errors.append("repository.name is required")
        if not fact.repository.type or not fact.repository.type.strip():
            errors.append("repository.type is required")
        if fact.repository.type not in ALLOWED_REPOSITORY_TYPES:
            errors.append(
                f"repository.type must be one of {sorted(ALLOWED_REPOSITORY_TYPES)}"
            )

    if errors:
        raise ValueError("; ".join(errors))


def select_template(doc_target: DocTarget) -> Tuple[str, str]:
    """Pick a fixed template by target audience."""
    if doc_target == DocTarget.developer:
        return "readme_developer_v1", TEMPLATE_DEVELOPER_V1
    if doc_target == DocTarget.designer:
        return "readme_designer_v1", TEMPLATE_DESIGNER_V1
    if doc_target == DocTarget.extension:
        return "readme_extension_v1", TEMPLATE_EXTENSION_V1
    return "readme_general_v1", TEMPLATE_GENERAL_V1


def mock_llm_generate(rendered_template: str) -> str:
    """
    Mock LLM call. For now, simply returns the rendered template
    without adding or removing information.
    """
    return rendered_template


def _format_optional_value(value: str, present: bool) -> str:
    """
    Distinguish between missing fields and explicit nulls.
    - Missing field: Not present
    - Null/None: Not specified
    """
    if not present:
        return "Not present"
    if value is None:
        return "Not specified"
    return value


def _format_frontend(frontend: FrontendRuntime, present: bool) -> str:
    if not present:
        return "Not present"
    if frontend is None:
        return "Not specified"

    framework_present = "framework" in frontend.model_fields_set
    bundler_present = "bundler" in frontend.model_fields_set

    framework = _format_optional_value(frontend.framework, framework_present)
    bundler = _format_optional_value(frontend.bundler, bundler_present)
    return f"Framework: {framework}; Bundler: {bundler}"


def _format_backend(backend: BackendRuntime, present: bool) -> str:
    if not present:
        return "Not present"
    if backend is None:
        return "Not specified"

    framework_present = "framework" in backend.model_fields_set
    language_present = "language" in backend.model_fields_set
    runtime_present = "runtime" in backend.model_fields_set

    framework = _format_optional_value(backend.framework, framework_present)
    language = _format_optional_value(backend.language, language_present)
    runtime = _format_optional_value(backend.runtime, runtime_present)
    return f"Framework: {framework}; Language: {language}; Runtime: {runtime}"


def _format_scripts(fact: FactJson) -> Tuple[str, str, str]:
    if fact.scripts is None:
        return "Not present", "Not present", "Not present"

    dev_present = "dev" in fact.scripts.model_fields_set
    build_present = "build" in fact.scripts.model_fields_set
    start_present = "start" in fact.scripts.model_fields_set

    dev = _format_optional_value(fact.scripts.dev, dev_present)
    build = _format_optional_value(fact.scripts.build, build_present)
    start = _format_optional_value(fact.scripts.start, start_present)
    return dev, build, start


def generate_readme(fact: FactJson, doc_target: DocTarget) -> Tuple[str, str]:
    """
    Deterministically create a README from Fact JSON and a fixed template.
    Returns (content, template_name).
    """
    template_name, template = select_template(doc_target)

    overview = f'Repository "{fact.repository.name}" is a "{fact.repository.type}" project.'

    # Runtime formatting with explicit null vs missing handling.
    runtime_present = fact.runtime is not None
    frontend_present = runtime_present and "frontend" in fact.runtime.model_fields_set
    backend_present = runtime_present and "backend" in fact.runtime.model_fields_set

    frontend_summary = _format_frontend(
        fact.runtime.frontend if runtime_present else None,
        frontend_present,
    )
    backend_summary = _format_backend(
        fact.runtime.backend if runtime_present else None,
        backend_present,
    )

    script_dev, script_build, script_start = _format_scripts(fact)

    rendered = template.format(
        name=fact.repository.name,
        repo_type=fact.repository.type,
        overview=overview,
        frontend_summary=frontend_summary,
        backend_summary=backend_summary,
        script_dev=script_dev,
        script_build=script_build,
        script_start=script_start,
    )

    content = mock_llm_generate(rendered)
    return content, template_name


async def create_readme_task(fact: FactJson, doc_target: DocTarget, mode: str) -> str:
    """
    Create an LLMTask for README generation and enqueue it.
    Returns the task_id for polling.
    """
    template_name, template = select_template(doc_target)

    payload = {
        "fact": fact.model_dump(),
        "mode": mode,
        "doc_target": doc_target.value,
        "template": template_name,
        "template_body": template,
    }

    task_id = str(uuid.uuid4())
    task = LLMTask(
        id=task_id,
        domain="readme",
        status=TaskStatus.PENDING,
        system_instruction="Generate README content strictly from the provided Fact JSON and template.",
        user_message=json.dumps(payload),
        result=None,
        created_at=time.time(),
    )

    await task_queue.add_task(task)
    return task_id

async def get_readme_status(task_id: str) -> Optional[ReadmePollResponse]:
    """
    Fetch task from queue and format as ReadmePollResponse.
    """

    # Fetch generic task from infrastructure 
    task = await task_queue.get_task(task_id)
    if not task:
        return None
    
    # Map generic task to Domain Scheme
    return ReadmePollResponse(
        task_id=task.id,
        status=task.status.value,
        content=task.result
    )