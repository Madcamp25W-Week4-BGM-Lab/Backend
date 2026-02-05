from fastapi import APIRouter, HTTPException

from src.readme.schemas import ReadmeGenerateRequest, ReadmeGenerateResponse, ReadmePollResponse
from src.readme.services import (
    validate_fact,
    generate_readme,
    create_intent_task,
    select_template,
    get_readme_status,
    select_readme_system_prompt,
)

router = APIRouter()

@router.post("/", response_model=ReadmeGenerateResponse)
async def generate_readme_endpoint(payload: ReadmeGenerateRequest) -> ReadmeGenerateResponse:
    """
    Generate README content based on a validated Fact JSON.
    """
    try:
        validate_fact(payload.fact)
        select_readme_system_prompt(payload.fact.repository.repo_type)
    except ValueError as exc:
        # Validation errors must return 400.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.async_mode:
        task_id = await create_intent_task(payload.fact)
        template_name, _ = select_template(payload.doc_target)
        return ReadmeGenerateResponse(
            task_id=task_id,
            template=template_name,
            fallback=False,
        )

    content, template_name = generate_readme(
        payload.fact,
        payload.doc_target,
    )

    # Fallback is always false for now; keep the field for future failover.
    return ReadmeGenerateResponse(
        content=content,
        template=template_name,
        fallback=False,
    )

@router.get("/{task_id}", response_model=ReadmePollResponse)
async def get_readme_result(task_id: str):
    """
    Client polls this endpoint to check if the README is ready.
    """
    response = await get_readme_status(task_id)
    if not response:
        raise HTTPException(status_code=404, detail="Task not found")
    return response
