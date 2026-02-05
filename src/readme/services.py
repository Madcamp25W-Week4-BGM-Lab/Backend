import json
import time
import uuid
from typing import Tuple, Optional, Dict, Any

from src.readme.schemas import (
    FactJson,
    DocTarget,
    FrontendRuntime,
    BackendRuntime,
    ReadmePollResponse,
    AnalysisContext,
    IntentAnalysis,
    DiagramIntent,
    RepositoryFacts,
    SemanticFacts,
    FileSystemSignals,
)
from src.infrastructure.queue import task_queue
from src.infrastructure.schemas import LLMTask, TaskStatus


ALLOWED_REPOSITORY_TYPES = {
    "research",
    "library",
    "service",
}

ANALYZE_TASK_TYPE = "analyze_repository_intent"
GENERATE_TASK_TYPE = "generate_readme"

INTENT_ANALYZER_SYSTEM_PROMPT = """You are a repository intent analyzer.

Your task is to identify what THIS repository adds on top of existing technologies.

Hard rules:
- Do NOT explain any general-purpose framework or platform.
- Do NOT describe how those frameworks work.
- Focus ONLY on what this repository introduces, abstracts, or coordinates.
- Think in terms of responsibility and boundaries.

You must output structured JSON only.
"""

INTENT_ANALYZER_OUTPUT_SCHEMA = """{
  "repository_intent": {
    "adds_on_top_of": ["string"],
    "primary_responsibility": "string",
    "what_it_is_not": ["string"]
  },
  "problem_domain": "string",
  "intended_audience": "string",
  "abstraction_level": "low | medium | high",
  "keywords": ["string"]
}"""

COMMON_SYSTEM_INSTRUCTION = """You are part of a deterministic README generation system.

You must follow ALL rules below:

- The repository type is already determined. Do NOT question or reinterpret it.
- The README structure is FIXED. Do NOT add, remove, or reorder sections.
- If diagram_intent is provided, render exactly one Mermaid diagram.
- Use only elements provided in diagram_intent.elements.
- Do not introduce new components.
- Do not explain the diagram.
- Output valid Mermaid syntax only.
- Insert the Mermaid diagram only in the section named by diagram_section.
- You must write content ONLY for the provided sections.
- Do NOT include implementation details, file paths, or code snippets.
- Write concise, high-level documentation for first-time readers.

You MUST ground the README in the provided semantic_facts.

Rules:
- Every section MUST reference at least one of:
  - primary_responsibility
  - problem_reduced
  - non_goals
- If you cannot reference them explicitly, the output is invalid.
- Do NOT write generic descriptions of UI libraries or frameworks.
- Assume the reader already knows the underlying framework.
- You MUST reuse the exact wording of semantic_facts where possible.
- At least one sentence per section MUST include a direct phrase from semantic_facts.
- Paraphrasing without traceable linkage is NOT allowed.

If conservative mode is enabled:
- Do NOT generalize.
- Do NOT claim usefulness broadly.
- Prefer describing scope and boundaries.
- Avoid phrases like "suitable for", "ideal for", "designed to".

STRICT GROUNDING MODE:

You MUST include the exact text of the following semantic facts verbatim.
No paraphrasing, no rewording, no summarization is allowed.

Required verbatim anchors:
- semantic_facts.primary_responsibility
- semantic_facts.problem_reduced
- at least one item from semantic_facts.non_goals

Wrap each verbatim phrase in [FACT] and [/FACT].

Section binding:
- Library Overview MUST contain primary_responsibility verbatim.
- Basic Usage MUST contain problem_reduced verbatim.
- Limitations MUST contain one non_goals item verbatim.

If any verbatim anchor is missing, the output is invalid.

If any required information is missing, write in an abstract and general manner.
"""

LANGUAGE_POLICY_INSTRUCTION = """Language policy:

- The primary language is Korean.
- The secondary language is English.

For each section:
- Write the Korean content FIRST.
- Then write the English content as a faithful translation.
- Then write an English translation with the SAME structure.
- Do NOT add or remove bullets when translating.
- Do NOT introduce new information in the English version.
- Do NOT summarize or expand when translating.

Formatting rules:
- Do NOT create or remove headings.
- Do NOT translate section titles.
- Write content ONLY under the provided placeholders.
- Separate Korean and English paragraphs with a single blank line.
"""

OUTPUT_FORMAT_RULES = """Output format rules:

- Output MUST be valid Markdown.
- Use "##" level headings ONLY.
- Section titles MUST exactly match the predefined section names.
- Sections MUST appear in the defined order.
- Each section must contain at least 1 paragraph.
- Do NOT include code blocks except the Mermaid diagram.
- Do NOT include TODOs or placeholders.
- Do NOT write long paragraphs.
- Each section MUST follow this structure:
  1. One short summary sentence.
  2. 3–5 bullet points.
- Each bullet point must:
  - Describe a concrete responsibility or boundary.
  - Be no longer than one sentence.
- Do NOT repeat information across bullets.
- Use ONLY existing section headings.
- Do NOT create new headings.
- For each section:
  - [Korean summary sentence]
  - 3 bullet points in Korean
  - [English summary sentence]
  - 3 bullet points in English
- Do NOT write paragraphs longer than one sentence.
- Do NOT mention the framework except as a background dependency.

If information is missing:
- Write abstract, general content.
- Do NOT state that information is missing.
"""

OUTPUT_FORMAT_RULES_BILINGUAL = """Output format rules (bilingual):

- Output MUST be valid Markdown.
- Each section MUST contain:
  - At least one Korean paragraph
  - Followed by at least one English paragraph
- Korean content must appear BEFORE English content.
- English content must be semantically equivalent to Korean content.
- Do NOT mix languages within the same paragraph.
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

Critical constraints:
- This repository is NOT the framework itself.
- You must NOT explain, introduce, or describe the framework.
- Assume the reader already fully understands the framework.
- Focus ONLY on what THIS repository adds, abstracts, or changes on top of it.

Disallowed patterns:
- Sentences starting with or similar to:
  "React is", "React provides", "React enables", "React allows"
- General explanations of components, state, lifecycle, or DOM rendering.

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

Section grounding requirements:

- Library Overview:
  MUST explain the primary_responsibility.

- Basic Usage:
  MUST relate to problem_reduced.

- Integration Flow:
  MUST describe where the responsibility fits in the system.

- Limitations:
  MUST be derived from non_goals explicitly.

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
            LANGUAGE_POLICY_INSTRUCTION.strip(),
            OUTPUT_FORMAT_RULES.strip(),
            OUTPUT_FORMAT_RULES_BILINGUAL.strip(),
            select_readme_system_prompt(repo_type).strip(),
        ]
    )


def build_readme_user_message(
    repository: Dict[str, Any],
    analysis_context: Optional[AnalysisContext],
    facts: Optional[Dict[str, Any]],
    semantic_facts: Optional[Dict[str, Any]],
    diagram_intent: Optional[DiagramIntent],
    mermaid_diagram: Optional[str],
    diagram_section: Optional[str],
    section_template: Optional[str],
    conservative: bool,
) -> str:
    payload = {
        "repository": repository,
        "analysis_context": (
            None if analysis_context is None else analysis_context.model_dump()
        ),
        "facts": facts,
        "semantic_facts": semantic_facts,
        "diagram_intent": (
            None if diagram_intent is None else diagram_intent.model_dump()
        ),
        "mermaid_diagram": mermaid_diagram,
        "diagram_section": diagram_section,
        "section_template": section_template,
        "conservative": conservative,
        "instruction": "Use semantic_facts EXACTLY as written where required.",
        "language_policy": {
            "primary": "ko",
            "secondary": "en",
        },
    }
    return json.dumps(payload)


def select_diagram_section(repo_type: str, diagram_intent: Optional[DiagramIntent]) -> Optional[str]:
    if diagram_intent is None:
        return None
    if repo_type == "library":
        return "Integration Flow"
    if repo_type == "service":
        return "System Architecture"
    if repo_type == "research":
        return "Experiment Pipeline"
    return None


def select_section_template(repo_type: str) -> Optional[str]:
    return SECTION_TEMPLATES.get(repo_type)


def build_intent_user_message(fact: FactJson) -> str:
    payload = {
        "repository": {
            "name": fact.repository.name,
            "repo_type": fact.repository.repo_type,
        },
        "facts": None if fact.facts is None else fact.facts.model_dump(),
        "semantic_facts": (
            None
            if fact.semantic_facts is None
            else fact.semantic_facts.model_dump()
        ),
        "fs_signals": (
            None if fact.fs_signals is None else fact.fs_signals.model_dump()
        ),
    }
    return json.dumps(payload)


def build_analysis_context(intent: IntentAnalysis) -> AnalysisContext:
    primary_focus = (
        f"{intent.repository_intent.primary_responsibility} on top of "
        f"{', '.join(intent.repository_intent.adds_on_top_of)}"
    )
    return AnalysisContext(
        primary_focus=primary_focus,
        problem_domain=intent.problem_domain,
        intended_audience=intent.intended_audience,
    )


def apply_semantic_sideguards(
    semantic_facts: Optional[Dict[str, Any]],
    conservative: bool,
) -> Tuple[Optional[Dict[str, Any]], bool]:
    if not semantic_facts:
        return semantic_facts, conservative

    non_goals = semantic_facts.get("non_goals")
    if not non_goals:
        semantic_facts["non_goals"] = [
            "This repository does not aim to replace the underlying framework.",
            "It focuses on a specific responsibility rather than end-to-end solutions.",
        ]
        conservative = True

    if not semantic_facts.get("problem_reduced"):
        semantic_facts["problem_reduced"] = (
            "reducing boilerplate and clarifying a narrow responsibility"
        )
        conservative = True

    return semantic_facts, conservative


def validate_readme_grounding(
    readme: str,
    semantic_facts: Optional[Dict[str, Any]],
) -> None:
    if not semantic_facts or not readme:
        return
    required = []
    if semantic_facts.get("primary_responsibility"):
        required.append(semantic_facts["primary_responsibility"])
    if semantic_facts.get("problem_reduced"):
        required.append(semantic_facts["problem_reduced"])
    non_goals = semantic_facts.get("non_goals") or []
    if non_goals:
        required.append(non_goals[0])
    if required and not any(text in readme for text in required):
        raise ValueError("README grounding validation failed")


def should_retry_strict_grounding(
    readme: str,
    semantic_facts: Optional[Dict[str, Any]],
) -> bool:
    if not semantic_facts or not readme:
        return False
    required = []
    if semantic_facts.get("primary_responsibility"):
        required.append(semantic_facts["primary_responsibility"])
    if semantic_facts.get("problem_reduced"):
        required.append(semantic_facts["problem_reduced"])
    non_goals = semantic_facts.get("non_goals") or []
    if non_goals:
        required.append(non_goals[0])
    if len(required) < 3:
        return False
    return (
        required[0] not in readme
        or required[1] not in readme
        or required[2] not in readme
    )


def apply_strict_grounding_prompt(system_prompt: str) -> str:
    return system_prompt


MERMAID_PATTERNS = {
    "library": {
        "integration_flow": (
            "```mermaid\n"
            "flowchart LR\n"
            "    App[Application Code]\n"
            "    Lib[This Library]\n"
            "    Framework[Underlying Framework]\n\n"
            "    App --> Lib\n"
            "    Lib --> Framework\n"
            "```"
        ),
    },
    "service": {
        "architecture": (
            "```mermaid\n"
            "flowchart LR\n"
            "    Client[Client]\n"
            "    Service[This Service]\n"
            "    Dependencies[External Systems]\n\n"
            "    Client --> Service\n"
            "    Service --> Dependencies\n"
            "```"
        ),
        "request_flow": (
            "```mermaid\n"
            "flowchart LR\n"
            "    User[User Action]\n"
            "    Service[Service Entry]\n"
            "    Processing[Internal Logic]\n"
            "    Response[Response]\n\n"
            "    User --> Service --> Processing --> Response\n"
            "```"
        ),
    },
    "research": {
        "experiment_pipeline": (
            "```mermaid\n"
            "flowchart LR\n"
            "    Input[Inputs]\n"
            "    Experiment[Experiment Process]\n"
            "    Evaluation[Evaluation]\n"
            "    Outcome[Findings]\n\n"
            "    Input --> Experiment --> Evaluation --> Outcome\n"
            "```"
        ),
    },
}

SECTION_TEMPLATES = {
    "library": """## Library Overview
<!-- LLM_KO -->

<!-- LLM_EN -->

## Installation
<!-- LLM_KO -->

<!-- LLM_EN -->

## Basic Usage
<!-- LLM_KO -->

<!-- LLM_EN -->

## Integration Flow
<!-- LLM_KO -->

<!-- LLM_EN -->

## API Design
<!-- LLM_KO -->

<!-- LLM_EN -->

## Use Cases
<!-- LLM_KO -->

<!-- LLM_EN -->

## Limitations
<!-- LLM_KO -->

<!-- LLM_EN -->
""",
    "service": """## Service Overview
<!-- LLM_KO -->

<!-- LLM_EN -->

## System Architecture
<!-- LLM_KO -->

<!-- LLM_EN -->

## Core Components
<!-- LLM_KO -->

<!-- LLM_EN -->

## Request Flow
<!-- LLM_KO -->

<!-- LLM_EN -->

## Deployment Context
<!-- LLM_KO -->

<!-- LLM_EN -->

## Operational Notes
<!-- LLM_KO -->

<!-- LLM_EN -->
""",
    "research": """## Project Overview
<!-- LLM_KO -->

<!-- LLM_EN -->

## Research Goal
<!-- LLM_KO -->

<!-- LLM_EN -->

## Experiment Pipeline
<!-- LLM_KO -->

<!-- LLM_EN -->

## Methodology
<!-- LLM_KO -->

<!-- LLM_EN -->

## Evaluation
<!-- LLM_KO -->

<!-- LLM_EN -->

## Key Findings
<!-- LLM_KO -->

<!-- LLM_EN -->
""",
}


FORBIDDEN_MERMAID_TERMS = {
    "component",
    "state",
    "props",
    "dom",
    "hook",
    "api list",
}


def validate_mermaid_pattern(mermaid: str, central_label: str) -> bool:
    lowered = mermaid.lower()
    if any(term in lowered for term in FORBIDDEN_MERMAID_TERMS):
        return False
    if central_label.lower() not in lowered:
        return False
    node_count = mermaid.count("[")
    return node_count <= 4


def build_diagram_intent(
    repo_type: str,
    facts: Optional[RepositoryFacts],
    fs_signals: Optional[FileSystemSignals],
) -> Optional[DiagramIntent]:
    if repo_type == "library":
        has_sdk = bool(facts and facts.has_sdk_exports)
        if has_sdk:
            return DiagramIntent(
                type="architecture",
                complexity="simple",
                elements=["Application Code", "This Library", "Underlying Framework"],
            )
        return None

    if repo_type == "service":
        has_api = bool(facts and facts.has_api_server)
        if has_api:
            return DiagramIntent(
                type="architecture",
                complexity="simple",
                elements=["Client", "This Service", "External Systems"],
            )
        return None

    if repo_type == "research":
        has_ml = bool(facts and facts.has_ml_code)
        if has_ml:
            return DiagramIntent(
                type="pipeline",
                complexity="simple",
                elements=["Inputs", "Experiment Process", "Evaluation", "Findings"],
            )
        return None

    return None


def render_mermaid(
    repo_type: str,
    diagram_intent: DiagramIntent,
    fs_signals: Optional[FileSystemSignals],
) -> Optional[str]:
    if repo_type == "library":
        mermaid = MERMAID_PATTERNS["library"]["integration_flow"]
        if not validate_mermaid_pattern(mermaid, "This Library"):
            return None
        return mermaid

    if repo_type == "service":
        mermaid = MERMAID_PATTERNS["service"]["architecture"]
        if not validate_mermaid_pattern(mermaid, "This Service"):
            return None
        if fs_signals and fs_signals.has_client:
            request_flow = MERMAID_PATTERNS["service"]["request_flow"]
            if validate_mermaid_pattern(request_flow, "Service Entry"):
                return mermaid + "\n\n" + request_flow
        return mermaid

    if repo_type == "research":
        mermaid = MERMAID_PATTERNS["research"]["experiment_pipeline"]
        if not validate_mermaid_pattern(mermaid, "Experiment Process"):
            return None
        return mermaid

    return None


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


async def create_intent_task(fact: FactJson) -> str:
    """
    Create an LLMTask for repository intent analysis and enqueue it.
    Returns the task_id for polling.
    """
    select_readme_system_prompt(fact.repository.repo_type)
    task_id = str(uuid.uuid4())
    task = LLMTask(
        id=task_id,
        domain="readme",
        task_type=ANALYZE_TASK_TYPE,
        status=TaskStatus.PENDING,
        system_instruction=(
            INTENT_ANALYZER_SYSTEM_PROMPT.strip()
            + "\n\n"
            + "assistant output schema (JSON):\n"
            + INTENT_ANALYZER_OUTPUT_SCHEMA
        ),
        user_message=build_intent_user_message(fact),
        result=None,
        created_at=time.time(),
    )
    await task_queue.add_task(task)
    return task_id


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

    diagram_intent = build_diagram_intent(
        fact.repository.repo_type,
        fact.facts,
        fact.fs_signals,
    )
    mermaid_diagram = (
        None
        if diagram_intent is None
        else render_mermaid(
            fact.repository.repo_type,
            diagram_intent,
            fact.fs_signals,
        )
    )
    diagram_section = select_diagram_section(
        fact.repository.repo_type,
        diagram_intent,
    )
    section_template = select_section_template(fact.repository.repo_type)
    semantic_facts = (
        None if fact.semantic_facts is None else fact.semantic_facts.model_dump()
    )
    conservative = (
        bool(fact.semantic_facts)
        and fact.semantic_facts.confidence == "low"
    )
    semantic_facts, conservative = apply_semantic_sideguards(
        semantic_facts,
        conservative,
    )
    user_message = build_readme_user_message(
        repository={
            "name": fact.repository.name,
            "short_description": fact.repository.short_description,
            "repo_type": fact.repository.repo_type,
        },
        analysis_context=fact.analysis_context,
        facts=None if fact.facts is None else fact.facts.model_dump(),
        semantic_facts=semantic_facts,
        diagram_intent=diagram_intent,
        mermaid_diagram=mermaid_diagram,
        diagram_section=diagram_section,
        section_template=section_template,
        conservative=conservative,
    )

    task_id = str(uuid.uuid4())
    task = LLMTask(
        id=task_id,
        domain="readme",
        task_type=GENERATE_TASK_TYPE,
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
    
    if task.task_type == ANALYZE_TASK_TYPE:
        if task.status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
            return ReadmePollResponse(
                task_id=task.id,
                status=task.status.value,
                content=None,
            )
        if task.status == TaskStatus.COMPLETED:
            try:
                intent_payload = IntentAnalysis.model_validate_json(task.result or "{}")
            except Exception:
                task.status = TaskStatus.FAILED
                return ReadmePollResponse(
                    task_id=task.id,
                    status=task.status.value,
                    content=None,
                    error="Invalid intent analysis JSON",
                )

            try:
                original_payload = json.loads(task.user_message)
            except (json.JSONDecodeError, TypeError):
                task.status = TaskStatus.FAILED
                return ReadmePollResponse(
                    task_id=task.id,
                    status=task.status.value,
                    content=None,
                    error="Invalid intent task payload",
                )

            if (
                not intent_payload.repository_intent
                or not intent_payload.repository_intent.primary_responsibility
                or not intent_payload.repository_intent.adds_on_top_of
            ):
                analysis_context = None
            else:
                analysis_context = build_analysis_context(intent_payload)
            repository = original_payload.get("repository", {})
            facts = original_payload.get("facts")
            semantic_facts = original_payload.get("semantic_facts")
            fs_signals = original_payload.get("fs_signals")
            repo_type = repository.get("repo_type")
            if not repo_type:
                task.status = TaskStatus.FAILED
                return ReadmePollResponse(
                    task_id=task.id,
                    status=task.status.value,
                    content=None,
                    error="Missing repository.repo_type in intent task payload",
                )

            task.task_type = GENERATE_TASK_TYPE
            task.status = TaskStatus.PENDING
            task.system_instruction = build_system_prompt(repo_type)
            facts_model = (
                None if facts is None else RepositoryFacts.model_validate(facts)
            )
            fs_model = (
                None
                if fs_signals is None
                else FileSystemSignals.model_validate(fs_signals)
            )
            diagram_intent = build_diagram_intent(repo_type, facts_model, fs_model)
            mermaid_diagram = (
                None
                if diagram_intent is None
                else render_mermaid(repo_type, diagram_intent, fs_model)
            )

            diagram_section = select_diagram_section(repo_type, diagram_intent)
            section_template = select_section_template(repo_type)
            conservative = False
            if semantic_facts:
                try:
                    semantic_model = SemanticFacts.model_validate(semantic_facts)
                    conservative = semantic_model.confidence == "low"
                except Exception:
                    conservative = True
            semantic_facts, conservative = apply_semantic_sideguards(
                semantic_facts,
                conservative,
            )
            task.user_message = build_readme_user_message(
                repository=repository,
                analysis_context=analysis_context,
                facts=facts,
                semantic_facts=semantic_facts,
                diagram_intent=diagram_intent,
                mermaid_diagram=mermaid_diagram,
                diagram_section=diagram_section,
                section_template=section_template,
                conservative=conservative,
            )
            task.result = None
            task.created_at = time.time()
            return ReadmePollResponse(
                task_id=task.id,
                status=task.status.value,
                content=None,
            )

    if task.task_type == GENERATE_TASK_TYPE and task.status == TaskStatus.COMPLETED:
        try:
            payload = json.loads(task.user_message)
        except (json.JSONDecodeError, TypeError):
            payload = {}
        semantic_facts = payload.get("semantic_facts")
        if should_retry_strict_grounding(task.result or "", semantic_facts):
            if not payload.get("retry_strict_grounding"):
                payload["retry_strict_grounding"] = True
                task.status = TaskStatus.PENDING
                task.system_instruction = apply_strict_grounding_prompt(
                    task.system_instruction or build_system_prompt(
                        payload.get("repository", {}).get("repo_type", "library")
                    )
                )
                task.user_message = json.dumps(payload)
                task.result = None
                task.created_at = time.time()
                return ReadmePollResponse(
                    task_id=task.id,
                    status=task.status.value,
                    content=None,
                )
            task.status = TaskStatus.FAILED
            return ReadmePollResponse(
                task_id=task.id,
                status=task.status.value,
                content=None,
                error="README grounding validation failed",
            )

    return ReadmePollResponse(
        task_id=task.id,
        status=task.status.value,
        content=task.result
    )
