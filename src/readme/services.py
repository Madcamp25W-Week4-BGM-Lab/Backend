import json
import time
import uuid
from typing import Tuple, Optional

from src.readme.schemas import (
    FactJson,
    DocTarget,
    FrontendRuntime,
    BackendRuntime,
    ReadmePollResponse
)
from src.infrastructure.queue import task_queue
from src.infrastructure.schemas import LLMTask, TaskStatus


ALLOWED_REPOSITORY_TYPES = {
    "research",
    "library",
    "service",
}

COMMON_SYSTEM_INSTRUCTION = """You are part of a deterministic README generation system.

You must follow ALL rules below:

- The repository type is already determined. Do NOT question or reinterpret it.
- The README structure is FIXED. Do NOT add, remove, or reorder sections.
- A Mermaid diagram is already inserted by the backend.
- You must NOT generate Mermaid code.
- You must NOT describe Mermaid syntax.
- You must write content ONLY for the provided sections.
- Do NOT include implementation details, file paths, or code snippets.
- Write concise, high-level documentation for first-time readers.

If any required information is missing, write in an abstract and general manner.
"""

OUTPUT_FORMAT_RULES = """Output format rules:

- Output MUST be valid Markdown.
- Use "##" level headings ONLY.
- Section titles MUST exactly match the predefined section names.
- Sections MUST appear in the defined order.
- Each section must contain at least 1 paragraph.
- Do NOT include code blocks.
- Do NOT include Mermaid diagrams.
- Do NOT include TODOs or placeholders.

If information is missing:
- Write abstract, general content.
- Do NOT state that information is missing.
"""

README_SYSTEM_PROMPT_RESEARCH = """Repository type: research

This repository represents a research or experimental project.

Your role is to WRITE CONTENT for a predefined README template.
You are NOT designing the structure.

Primary goals of this README:
- Explain what research problem is being explored
- Clarify the experimental setup at a high level
- Communicate what is evaluated and learned

You MUST follow this exact section order:

1. Project Overview
2. Research Goal
3. Experiment Pipeline
4. Methodology
5. Evaluation
6. Key Findings

Section-specific guidance:

- Project Overview:
  Provide a concise summary of the research topic and context.

- Research Goal:
  Clearly state the research question or hypothesis.

- Experiment Pipeline:
  Explain the overall experimental flow conceptually.
  Refer to the existing diagram as a high-level representation only.

- Methodology:
  Describe the approach in abstract terms (data, model, process).
  Avoid implementation or algorithmic detail.

- Evaluation:
  Explain what is measured and how results are assessed.

- Key Findings:
  Summarize insights or conclusions without numeric results.

Tone:
- Academic but readable
- Abstract and intention-focused
- No procedural instructions
"""

# System prompt for library repositories.
README_SYSTEM_PROMPT_LIBRARY = """Repository type: library

This repository represents a reusable software library.

Your role is to WRITE CONTENT for a predefined README template.
You are NOT designing the structure.

Primary goals of this README:
- Explain what problem the library solves
- Show how users conceptually interact with it
- Clarify where it fits within a larger system

You MUST follow this exact section order:

1. Library Overview
2. Installation
3. Basic Usage
4. Integration Flow
5. API Design
6. Use Cases
7. Limitations

Section-specific guidance:

- Library Overview:
  Describe the purpose and scope of the library.

- Installation:
  Explain installation at a conceptual level (no commands).

- Basic Usage:
  Describe a typical usage flow without code.

- Integration Flow:
  Explain how the library integrates with external systems.
  Refer to the diagram as a usage-level flow.

- API Design:
  Describe the design philosophy and responsibility boundaries.
  Do NOT list functions or methods.

- Use Cases:
  Provide examples of when the library is useful.

- Limitations:
  Clearly state known constraints or non-goals.

Tone:
- Developer-facing
- Practical but high-level
- Usage-oriented, not internal
"""

# System prompt for service repositories.
README_SYSTEM_PROMPT_SERVICE = """Repository type: service

This repository represents a service or application system.

Your role is to WRITE CONTENT for a predefined README template.
You are NOT designing the structure.

Primary goals of this README:
- Explain what the service does
- Describe the system architecture
- Clarify component responsibilities and interactions

You MUST follow this exact section order:

1. Service Overview
2. System Architecture
3. Core Components
4. Request Flow
5. Deployment Context
6. Operational Notes

Section-specific guidance:

- Service Overview:
  Summarize the service from a user or business perspective.

- System Architecture:
  Describe the high-level structure and major components.
  Refer to the diagram as a system overview.

- Core Components:
  Explain the roles and responsibilities of key components.

- Request Flow:
  Describe how a typical request moves through the system.

- Deployment Context:
  Explain the intended runtime context abstractly.

- Operational Notes:
  Mention constraints, assumptions, or extension points.

Tone:
- Architectural and explanatory
- Oriented toward new contributors
- No environment-specific steps
"""

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
        if not fact.repository.repo_type or not str(fact.repository.repo_type).strip():
            errors.append("repository.repo_type is required")
        if fact.repository.repo_type not in ALLOWED_REPOSITORY_TYPES:
            errors.append(
                f"repository.repo_type must be one of {sorted(ALLOWED_REPOSITORY_TYPES)}"
            )

    if errors:
        raise ValueError("; ".join(errors))


def select_readme_system_prompt(repo_type: str) -> str:
    if repo_type == "research":
        return README_SYSTEM_PROMPT_RESEARCH
    if repo_type == "library":
        return README_SYSTEM_PROMPT_LIBRARY
    if repo_type == "service":
        return README_SYSTEM_PROMPT_SERVICE
    raise ValueError(f"Unsupported repository.repo_type: {repo_type}")


def build_system_prompt(repo_type: str) -> str:
    return "\n\n".join(
        [
            COMMON_SYSTEM_INSTRUCTION.strip(),
            OUTPUT_FORMAT_RULES.strip(),
            select_readme_system_prompt(repo_type).strip(),
        ]
    )


def build_user_message(fact: FactJson) -> str:
    payload = {
        "repository": {
            "name": fact.repository.name,
            "short_description": fact.repository.short_description,
            "repo_type": fact.repository.repo_type,
        },
        "analysis_context": (
            None if fact.analysis_context is None else fact.analysis_context.model_dump()
        ),
        "facts": None if fact.facts is None else fact.facts.model_dump(),
    }
    return json.dumps(payload)


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


def generate_readme(
    fact: FactJson,
    doc_target: DocTarget,
) -> Tuple[str, str]:
    """
    Deterministically create a README from Fact JSON and a fixed template.
    Returns (content, template_name).
    """
    select_readme_system_prompt(fact.repository.repo_type)
    template_name, template = select_template(doc_target)

    overview = f'Repository "{fact.repository.name}" is a "{fact.repository.repo_type}" project.'

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
        repo_type=fact.repository.repo_type,
        overview=overview,
        frontend_summary=frontend_summary,
        backend_summary=backend_summary,
        script_dev=script_dev,
        script_build=script_build,
        script_start=script_start,
    )

    content = mock_llm_generate(rendered)
    return content, template_name


async def create_readme_task(
    fact: FactJson,
    doc_target: DocTarget,
    mode: str,
) -> str:
    """
    Create an LLMTask for README generation and enqueue it.
    Returns the task_id for polling.
    """
    system_prompt = build_system_prompt(fact.repository.repo_type)
    template_name, template = select_template(doc_target)

    user_message = build_user_message(fact)

    task_id = str(uuid.uuid4())
    task = LLMTask(
        id=task_id,
        domain="readme",
        status=TaskStatus.PENDING,
        system_instruction=system_prompt,
        user_message=user_message,
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
