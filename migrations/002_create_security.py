from beanie import Document
from pymongo import ASCENDING
from pymongo.operations import IndexModel

class Forward:
    @staticmethod
    async def run(db):
        # Create the security collection with indexes and constraints
        await db.create_collection("security")
        await db["security"].create_indexes([
            IndexModel([("ticker", ASCENDING)], unique=True),
            IndexModel([("security_type_id", ASCENDING)]),
        ])
        # Optionally, insert a sample document or set up validation rules here

class Backward:
    @staticmethod
    async def run(db):
        await db.drop_collection("security") 