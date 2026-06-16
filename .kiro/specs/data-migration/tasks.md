# Implementation Plan: Data Migration System

## Overview

This plan implements a custom database migration system for the GlobeCo Security Service. The implementation removes the legacy `mongo-migrate` dependency, creates a migration runner with tracking, and seeds the database with SecurityType and Security records. All code is Python 3.13 using Motor (async MongoDB driver), pytest-asyncio for tests, and Hypothesis for property-based testing.

## Tasks

- [x] 1. Set up migration module structure and core models
  - [x] 1.1 Remove `mongo-migrate` dependency and add `hypothesis` to pyproject.toml
    - Remove the line `"mongo-migrate>=0.1.2"` from the `dependencies` list in `pyproject.toml`
    - Add `"hypothesis>=6.100.0"` to the `dependencies` list in `pyproject.toml`
    - _Requirements: 1.1, 1.2_

  - [x] 1.2 Create `app/migrations/models.py` with MigrationRecord and MigrationError
    - Create `app/migrations/models.py`
    - Define `MigrationRecord` dataclass with fields: `name: str`, `applied_at: datetime`, `status: str`
    - Define `MigrationError` exception class that wraps a migration name and cause exception
    - Define `MigrationDescriptor` as a NamedTuple or dataclass with fields: `version: str`, `name: str`, `fn: Callable`
    - _Requirements: 2.1, 2.2, 3.3_

  - [x] 1.3 Create `app/migrations/__init__.py` with migration registry
    - Create `app/migrations/__init__.py`
    - Define `MIGRATIONS: list[MigrationDescriptor]` as an empty list initially (will be populated after seed migration is created)
    - Export `MIGRATIONS`, `MigrationDescriptor`, `MigrationRecord`, `MigrationError`
    - _Requirements: 3.2_

- [x] 2. Implement migration runner
  - [x] 2.1 Create `app/migrations/runner.py` with `run_migrations` function
    - Create `app/migrations/runner.py`
    - Implement `async def run_migrations(db: AsyncIOMotorDatabase) -> None`
    - Query `migration_history` collection for documents with `status: "success"` to get applied migration names
    - Filter `MIGRATIONS` registry to find pending migrations (those not in applied set)
    - Sort pending migrations by `version` field (lexicographic)
    - Execute each pending migration's `fn(db)` in order
    - On success: insert a document into `migration_history` with `name`, `applied_at` (UTC now), `status: "success"`
    - On failure: raise `MigrationError` wrapping the migration name and original exception
    - Create a unique index on `migration_history.name` to prevent duplicates
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 4.1_

  - [ ]* 2.2 Write property test for migration record correctness
    - **Property 1: Migration record correctness**
    - Create `tests/test_migration_runner.py`
    - Use Hypothesis to generate arbitrary migration functions that succeed
    - Assert: after successful execution, `migration_history` contains a document with the migration's name, `status: "success"`, and a valid UTC `applied_at` datetime
    - Use testcontainers for an isolated MongoDB instance
    - **Validates: Requirements 2.1, 2.2**

  - [ ]* 2.3 Write property test for idempotent skip of applied migrations
    - **Property 2: Idempotent skip of applied migrations**
    - In `tests/test_migration_runner.py`
    - Use Hypothesis to generate sets of migration descriptors and subsets of pre-applied records
    - Assert: only migrations without existing success records have their functions called
    - Track function invocations using mock/spy objects
    - **Validates: Requirements 2.3, 2.4, 4.1**

  - [ ]* 2.4 Write property test for version-ordered execution
    - **Property 3: Version-ordered execution**
    - In `tests/test_migration_runner.py`
    - Use Hypothesis to generate lists of migration descriptors with distinct version strings
    - Assert: migrations are executed in lexicographic order of their version field
    - Track execution order using an ordered log
    - **Validates: Requirements 3.2**

  - [ ]* 2.5 Write property test for failure propagation
    - **Property 4: Failure propagation**
    - In `tests/test_migration_runner.py`
    - Use Hypothesis to generate migrations where one raises an exception
    - Assert: `MigrationError` is raised AND no success record is written for the failing migration
    - **Validates: Requirements 3.3**

- [x] 3. Checkpoint - Verify runner logic
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement seed migration
  - [x] 4.1 Create `app/migrations/data/securities.json` seed data file
    - Create directory `app/migrations/data/`
    - Create `securities.json` containing a JSON array of 505 objects, each with `ticker` and `description` fields
    - Data represents S&P 500 constituents (e.g., `{"ticker": "AAPL", "description": "Apple Inc."}`)
    - _Requirements: 6.1, 6.2_

  - [x] 4.2 Create `app/migrations/v001_seed_security_data.py`
    - Implement `async def seed_security_data(db: AsyncIOMotorDatabase) -> None`
    - Insert one SecurityType document: `{abbreviation: "CS", description: "Common Stock", version: 1}` into the `securityType` collection
    - Read `securities.json` from the `data/` subdirectory (use `pathlib.Path(__file__).parent / "data" / "securities.json"`)
    - Parse JSON and build 505 Security documents with `ticker`, `description`, `security_type_id` (ObjectId from the created SecurityType), and `version: 1`
    - Use `insert_many` to bulk-insert the Security documents into the `security` collection
    - If SecurityType insertion fails, abort without inserting any Security documents
    - _Requirements: 5.1, 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3_

  - [x] 4.3 Register the seed migration in `app/migrations/__init__.py`
    - Import `seed_security_data` from `app.migrations.v001_seed_security_data`
    - Add `MigrationDescriptor(version="V001", name="seed_security_data", fn=seed_security_data)` to the `MIGRATIONS` list
    - _Requirements: 3.2_

  - [ ]* 4.4 Write property test for seed data referential integrity
    - **Property 5: Seed data referential integrity**
    - Create `tests/test_seed_migration.py`
    - Run the seed migration against an empty test database
    - Assert: for ALL Security documents, each has non-empty `ticker`, non-empty `description`, `version == 1`, and `security_type_id` matching the `_id` of the created SecurityType document
    - Use testcontainers for an isolated MongoDB instance
    - **Validates: Requirements 6.2, 6.3, 6.4, 7.2**

  - [ ]* 4.5 Write unit tests for seed migration
    - In `tests/test_seed_migration.py`
    - Test: seed migration creates exactly 1 SecurityType with abbreviation "CS"
    - Test: seed migration creates exactly 505 Security records
    - Test: re-running startup after seed migration does not create duplicate records (idempotency via runner)
    - Test: if SecurityType insert fails, no Security documents are created
    - _Requirements: 5.1, 5.2, 6.1, 7.1, 7.3_

- [x] 5. Checkpoint - Verify seed migration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Integrate migration runner into application startup
  - [x] 6.1 Update `app/main.py` to call `run_migrations` before `init_beanie`
    - Import `run_migrations` from `app.migrations.runner`
    - In `on_startup()`, after creating the Motor client and `db` reference but BEFORE `init_beanie()`, add `await run_migrations(db)`
    - _Requirements: 3.1, 4.1_

  - [ ]* 6.2 Write integration tests for startup ordering
    - Create `tests/test_migration_integration.py`
    - Test: migrations complete before Beanie initialization and HTTP routes are reachable
    - Test: service starts successfully when all migrations have been previously applied
    - Test: migration check with all-applied completes within 5 seconds
    - _Requirements: 3.1, 4.1, 4.2_

- [x] 7. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All tests use testcontainers for isolated MongoDB instances — no shared test state
- The `hypothesis` library is added for property-based testing alongside the existing pytest stack

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "4.1"] },
    { "id": 2, "tasks": ["2.1"] },
    { "id": 3, "tasks": ["2.2", "2.3", "2.4", "2.5", "4.2"] },
    { "id": 4, "tasks": ["4.3", "4.4", "4.5"] },
    { "id": 5, "tasks": ["6.1"] },
    { "id": 6, "tasks": ["6.2"] }
  ]
}
```
