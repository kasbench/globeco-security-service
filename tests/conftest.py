import pytest
import asyncio
from typing import AsyncGenerator
from testcontainers.mongodb import MongoDbContainer
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.security import Security
from app.models.security_type import SecurityType
from app.config import settings

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# Configure asyncio mode
def pytest_configure(config):
    config.option.asyncio_mode = "auto"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def mongodb_container():
    """Start MongoDB test container for the test session."""
    with MongoDbContainer("mongo:7.0") as mongodb:
        yield mongodb

@pytest.fixture(scope="session")
async def mongodb_client(mongodb_container):
    """Create MongoDB client connected to test container."""
    connection_url = mongodb_container.get_connection_url()
    client = AsyncIOMotorClient(connection_url)
    yield client
    client.close()

@pytest.fixture(scope="session")
async def test_database(mongodb_client):
    """Initialize test database with Beanie."""
    db = mongodb_client.test_securities_db
    await init_beanie(database=db, document_models=[SecurityType, Security])
    
    # Create indexes for optimal performance
    try:
        await Security.get_motor_collection().create_index("ticker")
        await Security.get_motor_collection().create_index([("ticker", "text")])
    except Exception as e:
        print(f"Index creation failed: {e}")  # Non-fatal for tests
    
    yield db
    
    # Cleanup: drop test database
    await mongodb_client.drop_database("test_securities_db")

@pytest.fixture
async def clean_database(test_database):
    """Clean database before each test."""
    # Clear all collections
    await Security.delete_all()
    await SecurityType.delete_all()
    yield test_database

@pytest.fixture
async def sample_security_types(clean_database):
    """Create sample security types for testing."""
    security_types = [
        SecurityType(abbreviation="CS", description="Common Stock", version=1),
        SecurityType(abbreviation="PF", description="Preferred Stock", version=1),
        SecurityType(abbreviation="BD", description="Bond", version=1),
    ]
    
    created_types = []
    for st in security_types:
        await st.insert()
        created_types.append(st)
    
    return created_types

@pytest.fixture
async def sample_securities(sample_security_types):
    """Create sample securities for testing."""
    cs_type = next(st for st in sample_security_types if st.abbreviation == "CS")
    pf_type = next(st for st in sample_security_types if st.abbreviation == "PF")
    
    securities = [
        Security(ticker="AAPL", description="Apple Inc. Common Stock", security_type_id=cs_type.id, version=1),
        Security(ticker="MSFT", description="Microsoft Corporation Common Stock", security_type_id=cs_type.id, version=1),
        Security(ticker="GOOGL", description="Alphabet Inc. Class A Common Stock", security_type_id=cs_type.id, version=1),
        Security(ticker="APPN", description="Appian Corporation Common Stock", security_type_id=cs_type.id, version=1),
        Security(ticker="APP.TO", description="AppLovin Corporation Common Stock (Toronto)", security_type_id=cs_type.id, version=1),
        Security(ticker="AAPL.PF", description="Apple Inc. Preferred Stock", security_type_id=pf_type.id, version=1),
        Security(ticker="TSLA", description="Tesla Inc. Common Stock", security_type_id=cs_type.id, version=1),
        Security(ticker="AMZN", description="Amazon.com Inc. Common Stock", security_type_id=cs_type.id, version=1),
    ]
    
    created_securities = []
    for sec in securities:
        await sec.insert()
        created_securities.append(sec)
    
    return created_securities

@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    return TestClient(app)

@pytest.fixture
async def async_client():
    """Create async FastAPI test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client 