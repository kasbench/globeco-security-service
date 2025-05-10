import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["MONGODB_DB"] = "test_securities"
os.environ["TEST_MODE"] = "1"
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

from app.models.security_type import SecurityType
from app.models.security import Security

# Utility to get a free port

def get_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

@pytest_asyncio.fixture(scope="module")
def server():
    port = get_free_port()
    url = f"http://localhost:{port}/api/v1"
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1)
    yield url
    server.should_exit = True
    thread.join()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db(server):
    async with httpx.AsyncClient(base_url=server) as client:
        await client.post("/test/cleanup")
        yield
        await client.post("/test/cleanup")

@pytest.mark.asyncio
async def test_create_and_get_security(server):
    async with httpx.AsyncClient(base_url=server) as client:
        # Create a security type first
        st_payload = {"abbreviation": "EQ", "description": "Equity", "version": 1}
        st_resp = await client.post("/securityTypes", json=st_payload)
        st_id = st_resp.json()["securityTypeId"]
        # Create security
        payload = {"ticker": "AAPL", "description": "Apple Inc.", "securityTypeId": st_id, "version": 1}
        resp = await client.post("/securities", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["securityType"]["abbreviation"] == "EQ"
        # Get security
        sec_id = data["securityId"]
        get_resp = await client.get(f"/security/{sec_id}")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["ticker"] == "AAPL"
        assert get_data["securityType"]["abbreviation"] == "EQ"

@pytest.mark.asyncio
async def test_update_security(server):
    async with httpx.AsyncClient(base_url=server) as client:
        # Create a security type
        st_payload = {"abbreviation": "BD", "description": "Bond", "version": 1}
        st_resp = await client.post("/securityTypes", json=st_payload)
        st_id = st_resp.json()["securityTypeId"]
        # Create security
        payload = {"ticker": "TSLA", "description": "Tesla Inc.", "securityTypeId": st_id, "version": 1}
        resp = await client.post("/securities", json=payload)
        sec_id = resp.json()["securityId"]
        # Update security
        update_payload = {"ticker": "TSLA", "description": "Tesla Motors", "securityTypeId": st_id, "version": 1}
        update_resp = await client.put(f"/security/{sec_id}", json=update_payload)
        assert update_resp.status_code == 200
        assert update_resp.json()["description"] == "Tesla Motors"

@pytest.mark.asyncio
async def test_delete_security(server):
    async with httpx.AsyncClient(base_url=server) as client:
        # Create a security type
        st_payload = {"abbreviation": "ETF", "description": "Exchange Traded Fund", "version": 1}
        st_resp = await client.post("/securityTypes", json=st_payload)
        st_id = st_resp.json()["securityTypeId"]
        # Create security
        payload = {"ticker": "SPY", "description": "S&P 500 ETF", "securityTypeId": st_id, "version": 1}
        resp = await client.post("/securities", json=payload)
        sec_id = resp.json()["securityId"]
        # Delete security
        del_resp = await client.delete(f"/security/{sec_id}?version=1")
        assert del_resp.status_code == 204
        # Confirm deletion
        get_resp = await client.get(f"/security/{sec_id}")
        assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_get_all_securities(server):
    async with httpx.AsyncClient(base_url=server) as client:
        # Create a security type
        st_payload = {"abbreviation": "OPT", "description": "Option", "version": 1}
        st_resp = await client.post("/securityTypes", json=st_payload)
        st_id = st_resp.json()["securityTypeId"]
        # Create security
        payload = {"ticker": "AAPL220121C00145000", "description": "AAPL Jan 2022 Call Option", "securityTypeId": st_id, "version": 1}
        await client.post("/securities", json=payload)
        # Get all securities
        resp = await client.get("/securities")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(sec["ticker"] == "AAPL220121C00145000" for sec in data)

@pytest.mark.asyncio
async def test_security_version_conflict(server):
    async with httpx.AsyncClient(base_url=server) as client:
        # Create a security type
        st_payload = {"abbreviation": "FUT", "description": "Future", "version": 1}
        st_resp = await client.post("/securityTypes", json=st_payload)
        st_id = st_resp.json()["securityTypeId"]
        # Create security
        payload = {"ticker": "ESZ21", "description": "S&P 500 Dec 2021 Future", "securityTypeId": st_id, "version": 1}
        resp = await client.post("/securities", json=payload)
        sec_id = resp.json()["securityId"]
        # Try to update with wrong version
        update_payload = {"ticker": "ESZ21", "description": "Updated", "securityTypeId": st_id, "version": 2}
        update_resp = await client.put(f"/security/{sec_id}", json=update_payload)
        assert update_resp.status_code == 409
        # Try to delete with wrong version
        del_resp = await client.delete(f"/security/{sec_id}?version=2")
        assert del_resp.status_code == 409 