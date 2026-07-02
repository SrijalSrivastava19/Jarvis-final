from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "ollama_reachable" in body
    assert "whisper_loaded" in body
    assert "piper_available" in body


@pytest.mark.asyncio
async def test_chat_creates_conversation_and_returns_reply(client):
    with patch(
        "app.api.routes_chat.ollama_service.generate_reply",
        new=AsyncMock(return_value="Hello! How can I help you today?"),
    ):
        response = await client.post("/api/chat", json={"message": "Hi Jarvis"})

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Hello! How can I help you today?"
    assert body["conversation_id"]


@pytest.mark.asyncio
async def test_chat_continues_existing_conversation(client):
    with patch(
        "app.api.routes_chat.ollama_service.generate_reply",
        new=AsyncMock(return_value="First reply"),
    ):
        first = await client.post("/api/chat", json={"message": "Remember the number 42"})
    conversation_id = first.json()["conversation_id"]

    with patch(
        "app.api.routes_chat.ollama_service.generate_reply",
        new=AsyncMock(return_value="It was 42"),
    ) as mocked:
        second = await client.post(
            "/api/chat",
            json={"message": "What number did I say?", "conversation_id": conversation_id},
        )

    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id
    # The context sent to the LLM should include the prior turn
    sent_context = mocked.call_args.args[0]
    assert any("42" in m["content"] for m in sent_context)


@pytest.mark.asyncio
async def test_chat_rejects_empty_message(client):
    response = await client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_handles_ollama_unavailable(client):
    from app.core.exceptions import OllamaUnavailableError

    with patch(
        "app.api.routes_chat.ollama_service.generate_reply",
        new=AsyncMock(side_effect=OllamaUnavailableError("Ollama down")),
    ):
        response = await client.post("/api/chat", json={"message": "Hello"})

    assert response.status_code == 503
    assert response.json()["error_code"] == "ollama_unavailable"
