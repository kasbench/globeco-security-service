import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["MONGODB_DB"] = "test_securities"
import pytest
import pytest_asyncio
import asyncio
import socket
import threading
import time
import httpx
from app.main import app
import motor.motor_asyncio
import uvicorn

def get_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["test_securities"]
    await db["securityType"].drop()
    yield
    await db["securityType"].drop()

@pytest_asyncio.fixture(scope="module")
def server():
    port = get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1)  # Wait for the server to start
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join()

@pytest.mark.asyncio
async def test_create_and_get_security_type(server):
    async with httpx.AsyncClient(base_url=server) as client:
        payload = {"abbreviation": "EQ", "description": "Equity", "version": 1}
        resp = await client.post("/api/v1/securityTypes", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["abbreviation"] == "EQ"
        assert data["description"] == "Equity"
        assert data["version"] == 1
        security_type_id = data["securityTypeId"]
        resp = await client.get(f"/api/v1/securityType/{security_type_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["abbreviation"] == "EQ"
        assert data["description"] == "Equity"
        assert data["version"] == 1

@pytest.mark.asyncio
async def test_get_all_security_types(server):
    async with httpx.AsyncClient(base_url=server) as client:
        # Create a security type first
        payload = {"abbreviation": "EQ", "description": "Equity", "version": 1}
        await client.post("/api/v1/securityTypes", json=payload)
        # Now test GET
        resp = await client.get("/api/v1/securityTypes")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(st["abbreviation"] == "EQ" for st in data)

@pytest.mark.asyncio
async def test_update_security_type(server):
    async with httpx.AsyncClient(base_url=server) as client:
        payload = {"abbreviation": "BD", "description": "Bond", "version": 1}
        resp = await client.post("/api/v1/securityTypes", json=payload)
        security_type_id = resp.json()["securityTypeId"]
        update_payload = {"abbreviation": "BDX", "description": "Bond X", "version": 1}
        resp = await client.put(f"/api/v1/securityType/{security_type_id}", json=update_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["abbreviation"] == "BDX"
        assert data["description"] == "Bond X"
        assert data["version"] == 2

@pytest.mark.asyncio
async def test_update_security_type_version_conflict(server):
    async with httpx.AsyncClient(base_url=server) as client:
        payload = {"abbreviation": "OPT", "description": "Option", "version": 1}
        resp = await client.post("/api/v1/securityTypes", json=payload)
        security_type_id = resp.json()["securityTypeId"]
        update_payload = {"abbreviation": "OPTX", "description": "Option X", "version": 99}
        resp = await client.put(f"/api/v1/securityType/{security_type_id}", json=update_payload)
        assert resp.status_code == 409

@pytest.mark.asyncio
async def test_delete_security_type(server):
    async with httpx.AsyncClient(base_url=server) as client:
        payload = {"abbreviation": "DEL", "description": "Delete Me", "version": 1}
        resp = await client.post("/api/v1/securityTypes", json=payload)
        security_type_id = resp.json()["securityTypeId"]
        resp = await client.delete(f"/api/v1/securityType/{security_type_id}?version=1")
        assert resp.status_code == 204
        resp = await client.get(f"/api/v1/securityType/{security_type_id}")
        assert resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_security_type_version_conflict(server):
    async with httpx.AsyncClient(base_url=server) as client:
        payload = {"abbreviation": "DEL2", "description": "Delete Me 2", "version": 1}
        resp = await client.post("/api/v1/securityTypes", json=payload)
        security_type_id = resp.json()["securityTypeId"]
        resp = await client.delete(f"/api/v1/securityType/{security_type_id}?version=99")
        assert resp.status_code == 409 