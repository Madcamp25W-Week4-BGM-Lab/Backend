import pytest
import pytest_asyncio  # <--- 1. Import this
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.infrastructure.queue import task_queue

# 2. Synchronous fixtures can stay as @pytest.fixture
@pytest.fixture(autouse=True)
def clear_queue():
    """Resets the in-memory queue before every test."""
    task_queue.tasks.clear()
    yield

# 3. Async fixtures MUST use @pytest_asyncio.fixture
@pytest_asyncio.fixture
async def client():
    """Creates an async HTTP client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac