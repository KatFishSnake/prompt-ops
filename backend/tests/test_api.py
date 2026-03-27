import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_prompt(client: AsyncClient):
    r = await client.post("/api/prompts", json={"name": "test-prompt", "description": "A test"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "test-prompt"
    assert data["description"] == "A test"
    assert len(data["versions"]) == 1
    assert data["versions"][0]["is_active"] is True


@pytest.mark.asyncio
async def test_create_duplicate_prompt(client: AsyncClient):
    await client.post("/api/prompts", json={"name": "dup-test", "description": ""})
    r = await client.post("/api/prompts", json={"name": "dup-test", "description": ""})
    assert r.status_code == 400
    assert "already exists" in r.json()["detail"]


@pytest.mark.asyncio
async def test_list_prompts(client: AsyncClient):
    await client.post("/api/prompts", json={"name": "list-test-1", "description": ""})
    await client.post("/api/prompts", json={"name": "list-test-2", "description": ""})
    r = await client.get("/api/prompts")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "list-test-1" in names
    assert "list-test-2" in names


@pytest.mark.asyncio
async def test_get_prompt(client: AsyncClient):
    create = await client.post("/api/prompts", json={"name": "get-test", "description": "desc"})
    pid = create.json()["id"]
    r = await client.get(f"/api/prompts/{pid}")
    assert r.status_code == 200
    assert r.json()["name"] == "get-test"


@pytest.mark.asyncio
async def test_create_version(client: AsyncClient):
    create = await client.post("/api/prompts", json={"name": "version-test", "description": ""})
    pid = create.json()["id"]
    r = await client.post(
        f"/api/prompts/{pid}/versions",
        json={"content": "Hello {{name}}", "model_config": {"model": "gpt-4o-mini"}},
    )
    assert r.status_code == 200
    assert r.json()["version_number"] == 2
    assert r.json()["content"] == "Hello {{name}}"
    assert r.json()["is_active"] is False


@pytest.mark.asyncio
async def test_promote_version(client: AsyncClient):
    create = await client.post("/api/prompts", json={"name": "promote-test", "description": ""})
    pid = create.json()["id"]
    v1_id = create.json()["versions"][0]["id"]

    # Create v2
    v2 = await client.post(
        f"/api/prompts/{pid}/versions",
        json={"content": "New content", "model_config": {}},
    )
    v2_id = v2.json()["id"]

    # Promote v2
    r = await client.post(f"/api/prompts/{pid}/promote", json={"version_id": v2_id})
    assert r.status_code == 200
    assert r.json()["is_active"] is True

    # Verify v1 is no longer active
    prompt = await client.get(f"/api/prompts/{pid}")
    versions = prompt.json()["versions"]
    v1 = next(v for v in versions if v["id"] == v1_id)
    assert v1["is_active"] is False


@pytest.mark.asyncio
async def test_serve_active(client: AsyncClient):
    create = await client.post("/api/prompts", json={"name": "serve-test", "description": ""})
    pid = create.json()["id"]

    # Create v2 with content and promote it
    v2 = await client.post(
        f"/api/prompts/{pid}/versions",
        json={"content": "Serve this", "model_config": {"model": "gpt-4o-mini"}},
    )
    await client.post(f"/api/prompts/{pid}/promote", json={"version_id": v2.json()["id"]})

    r = await client.get("/api/prompts/serve/serve-test")
    assert r.status_code == 200
    assert r.json()["content"] == "Serve this"
    assert r.json()["prompt_name"] == "serve-test"


@pytest.mark.asyncio
async def test_serve_not_found(client: AsyncClient):
    r = await client.get("/api/prompts/serve/nonexistent")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_ingest_traces(client: AsyncClient):
    await client.post("/api/prompts", json={"name": "trace-test", "description": ""})
    r = await client.post(
        "/api/traces",
        json={
            "traces": [
                {
                    "prompt_name": "trace-test",
                    "input": {"messages": [{"role": "user", "content": "Hello"}]},
                    "output": "Hi there!",
                    "model": "gpt-4o-mini",
                    "latency_ms": 500,
                }
            ]
        },
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["output"] == "Hi there!"


@pytest.mark.asyncio
async def test_ingest_traces_unknown_prompt(client: AsyncClient):
    r = await client.post(
        "/api/traces",
        json={
            "traces": [
                {
                    "prompt_name": "unknown-prompt",
                    "input": {"messages": [{"role": "user", "content": "Hello"}]},
                    "output": "Hi!",
                }
            ]
        },
    )
    assert r.status_code == 200
    assert r.json()[0]["prompt_id"] is None


@pytest.mark.asyncio
async def test_list_traces(client: AsyncClient):
    await client.post("/api/prompts", json={"name": "trace-list-test", "description": ""})
    await client.post(
        "/api/traces",
        json={
            "traces": [
                {
                    "prompt_name": "trace-list-test",
                    "input": {"messages": [{"role": "user", "content": "Test"}]},
                    "output": "Response",
                }
            ]
        },
    )
    r = await client.get("/api/traces")
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_replay_validates_version_belongs_to_prompt(client: AsyncClient):
    # Create two prompts
    p1 = await client.post("/api/prompts", json={"name": "replay-p1", "description": ""})
    p2 = await client.post("/api/prompts", json={"name": "replay-p2", "description": ""})
    p1_id = p1.json()["id"]
    p2_v1_id = p2.json()["versions"][0]["id"]

    # Create a v2 for p1
    await client.post(
        f"/api/prompts/{p1_id}/versions",
        json={"content": "Test", "model_config": {}},
    )

    # Try to replay p1 with a version from p2 — should fail
    r = await client.post(
        "/api/replay",
        json={
            "prompt_id": p1_id,
            "source_version_id": p1.json()["versions"][0]["id"],
            "target_version_id": p2_v1_id,
        },
    )
    assert r.status_code == 404
    assert "not found for this prompt" in r.json()["detail"]


@pytest.mark.asyncio
async def test_replay_no_traces(client: AsyncClient):
    create = await client.post("/api/prompts", json={"name": "replay-empty", "description": ""})
    pid = create.json()["id"]
    v1_id = create.json()["versions"][0]["id"]
    v2 = await client.post(
        f"/api/prompts/{pid}/versions",
        json={"content": "Test", "model_config": {}},
    )

    r = await client.post(
        "/api/replay",
        json={
            "prompt_id": pid,
            "source_version_id": v1_id,
            "target_version_id": v2.json()["id"],
        },
    )
    assert r.status_code == 400
    assert "No traces" in r.json()["detail"]
