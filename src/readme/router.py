from fastapi import APIRouter, HTTPException

from src.readme.schemas import ReadmeGenerateRequest, ReadmeGenerateResponse
from src.readme.services import (
    validate_fact,
    generate_readme,
    create_readme_task,
    select_template,
)

router = APIRouter()

@router.post("/generate-readme", response_model=ReadmeGenerateResponse)
async def generate_readme_endpoint(payload: ReadmeGenerateRequest) -> ReadmeGenerateResponse:
    """
    Generate README content based on a validated Fact JSON.
    """
    try:
        validate_fact(payload.fact)
    except ValueError as exc:
        # Validation errors must return 400.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.async_mode:
        task_id = await create_readme_task(
            payload.fact,
            payload.doc_target,
            payload.mode.value,
        )
        template_name, _ = select_template(payload.doc_target)
        return ReadmeGenerateResponse(
            task_id=task_id,
            template=template_name,
            fallback=False,
        )

    content, template_name = generate_readme(payload.fact, payload.doc_target)

    # Fallback is always false for now; keep the field for future failover.
    return ReadmeGenerateResponse(
        content=content,
        template=template_name,
        fallback=False,
    )
