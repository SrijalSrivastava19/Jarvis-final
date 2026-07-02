import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.database import init_db
from app.main import app


@pytest_asyncio.fixture
async def client():
    # ASGITransport does not trigger FastAPI's lifespan startup, so the
    # database tables would not exist yet — initialize explicitly here.
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
