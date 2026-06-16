"""Migration system models and exceptions."""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Awaitable, NamedTuple

from motor.motor_asyncio import AsyncIOMotorDatabase


class MigrationDescriptor(NamedTuple):
    """Describes a single migration to be executed by the runner."""

    version: str
    name: str
    fn: Callable[[AsyncIOMotorDatabase], Awaitable[None]]


@dataclass
class MigrationRecord:
    """Represents a document in the migration_history collection."""

    name: str  # e.g. "V001_seed_security_data"
    applied_at: datetime  # UTC timestamp of successful execution
    status: str  # "success"


class MigrationError(Exception):
    """Raised when a migration fails, preventing service startup."""

    def __init__(self, migration_name: str, cause: Exception):
        self.migration_name = migration_name
        self.cause = cause
        super().__init__(f"Migration '{migration_name}' failed: {cause}")
