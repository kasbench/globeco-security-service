"""Migration runner – discovers, filters, and executes pending migrations."""

from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.migrations import MIGRATIONS
from app.migrations.models import MigrationError


async def run_migrations(db: AsyncIOMotorDatabase) -> None:
    """
    Discover all registered migrations, skip already-applied ones,
    and execute pending migrations in version order.
    Raises MigrationError on failure, which prevents service startup.
    """
    collection = db["migration_history"]

    # Ensure unique index on name to prevent duplicate application
    await collection.create_index("name", unique=True)

    # Query for previously applied migrations
    applied_cursor = collection.find({"status": "success"}, {"name": 1})
    applied_names: set[str] = {doc["name"] async for doc in applied_cursor}

    # Filter to only pending migrations
    pending = [m for m in MIGRATIONS if m.name not in applied_names]

    # Sort pending migrations by version (lexicographic order)
    pending.sort(key=lambda m: m.version)

    # Execute each pending migration in order
    for migration in pending:
        try:
            await migration.fn(db)
        except Exception as exc:
            raise MigrationError(migration.name, exc) from exc

        # Record successful application
        await collection.insert_one(
            {
                "name": migration.name,
                "applied_at": datetime.now(timezone.utc),
                "status": "success",
            }
        )
