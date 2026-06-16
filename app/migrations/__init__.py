"""Migration system registry and public API."""

from app.migrations.models import MigrationDescriptor, MigrationError, MigrationRecord
from app.migrations.v001_seed_security_data import seed_security_data

MIGRATIONS: list[MigrationDescriptor] = [
    MigrationDescriptor(version="V001", name="seed_security_data", fn=seed_security_data),
]

__all__ = ["MIGRATIONS", "MigrationDescriptor", "MigrationRecord", "MigrationError"]
