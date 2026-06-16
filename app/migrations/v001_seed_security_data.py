"""V001 Seed Migration – creates SecurityType and Security documents."""

import json
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorDatabase


async def seed_security_data(db: AsyncIOMotorDatabase) -> None:
    """
    1. Insert a SecurityType document (abbreviation="CS", description="Common Stock", version=1)
    2. Read security data from JSON file
    3. Insert 505 Security documents with security_type_id pointing to the created SecurityType
    """
    # Step 1: Insert SecurityType document
    security_type_doc = {
        "abbreviation": "CS",
        "description": "Common Stock",
        "version": 1,
    }

    result = await db["securityType"].insert_one(security_type_doc)
    security_type_id = result.inserted_id

    # Step 2: Read securities data from JSON file
    data_path = Path(__file__).parent / "data" / "securities.json"
    with open(data_path, "r", encoding="utf-8") as f:
        securities_data = json.load(f)

    # Step 3: Build Security documents with reference to the created SecurityType
    security_docs = [
        {
            "ticker": item["ticker"],
            "description": item["description"],
            "security_type_id": security_type_id,
            "version": 1,
        }
        for item in securities_data
    ]

    # Step 4: Bulk-insert Security documents
    await db["security"].insert_many(security_docs)
