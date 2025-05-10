from beanie import Document
from pymongo import ASCENDING
from pymongo.operations import IndexModel

class Forward:
    @staticmethod
    async def run(db):
        # Create the securityType collection with indexes and constraints
        await db.create_collection("securityType")
        await db["securityType"].create_indexes([
            IndexModel([("abbreviation", ASCENDING)], unique=True),
        ])
        # Optionally, insert a sample document or set up validation rules here

class Backward:
    @staticmethod
    async def run(db):
        await db.drop_collection("securityType") 