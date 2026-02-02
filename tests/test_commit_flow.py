import pytest
from httpx import AsyncClient

# Sample Payload matching your 'CommitRequest' schema
SAMPLE_PAYLOAD = {
    "diff": "diff --git a/main.py b/main.py...",
    "config": {
        "project_descriptions": "A Python backend for VS Code",
        "style": {
            "convention": "conventional",
            "useEmojis": True,
            "language": "en"
        },
        "rules": ["No cursing", "Keep it short"]
    },
    "history": ["feat: initial commit"]
}

@pytest.mark.asyncio
async def test_full_commit_lifecycle(client: AsyncClient):
    """
    Scenario:
    1. USER POSTs a request to /generate-commit
    2. USER Polls the status (should be Pending)
    3. WORKER Pops the task (should get the prompt)
    4. WORKER Completes the task
    5. USER Polls the status (should be Completed)
    """

    # --- STEP 1: CLIENT REQUESTS COMMIT ---
    response = await client.post("/api/v1/generate-commit", json=SAMPLE_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    
    assert "task_id" in data
    task_id = data["task_id"]
    print(f"\n[1] Created Task: {task_id}")

    # --- STEP 2: CLIENT POLLS (PENDING) ---
    response = await client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    task_data = response.json()
    
    assert task_data["status"] == "pending"
    assert task_data["domain"] == "commit"
    # Ensure system/user prompt separation works
    assert "System Instruction" in str(task_data) or task_data["system_instruction"] is not None
    print("[2] Verified Task is Pending in Queue")

    # --- STEP 3: WORKER POPS TASK ---
    # Worker asks: "Any work for me?"
    response = await client.get("/queue/pop")
    assert response.status_code == 200
    worker_task = response.json()
    
    assert worker_task["id"] == task_id
    assert worker_task["status"] == "processing" # Queue should auto-update status to processing
    print("[3] Worker received the task")

    # --- STEP 4: WORKER COMPLETES TASK ---
    # Worker finishes LLM inference
    fake_llm_result = "feat: added tests for backend"
    response = await client.post(f"/queue/complete/{task_id}", json={"result": fake_llm_result})
    assert response.status_code == 200
    print("[4] Worker submitted result")

    # --- STEP 5: CLIENT POLLS (COMPLETED) ---
    response = await client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    final_data = response.json()
    
    assert final_data["status"] == "completed"
    assert final_data["result"] == fake_llm_result
    print("[5] Client retrieved final result")

@pytest.mark.asyncio
async def test_worker_no_work(client: AsyncClient):
    """
    Scenario: Worker asks for work when queue is empty.
    Should return 404 (Not Found).
    """
    response = await client.get("/queue/pop")
    assert response.status_code == 404
    print("\n[Success] Worker correctly received 404 when queue was empty")