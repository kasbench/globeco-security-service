# Requirements Document

## Introduction

This feature implements a database migration system for the GlobeCo Security Service. The migration system follows the Flyway/Liquibase pattern: it runs automatically at service startup, checks whether each migration has already been applied, and only executes pending migrations. The first migration seeds the "securities" database with a SecurityType record for Common Stock and 505 Security records representing S&P 500 constituents. Additionally, the legacy `mongo-migrate` dependency is removed from the project.

## Glossary

- **Migration_System**: The component responsible for discovering, tracking, and executing database migrations at service startup
- **Migration_Record**: A document stored in MongoDB that records whether a specific migration has been successfully applied, including metadata such as migration name, execution timestamp, and status
- **Security_Service**: The FastAPI application (globeco-security-service) that serves security data via REST APIs
- **SecurityType_Collection**: The MongoDB collection named "securityType" in the "securities" database, holding security classification records
- **Security_Collection**: The MongoDB collection named "security" in the "securities" database, holding individual security records
- **Seed_Migration**: The first migration (V001) that populates the database with the Common Stock security type and 505 S&P 500 constituent security records
- **Referential_Integrity**: The constraint that every Security record's `security_type_id` field references a valid, existing SecurityType document's `_id`

## Requirements

### Requirement 1: Remove Legacy Dependency

**User Story:** As a developer, I want the legacy `mongo-migrate` dependency removed from the project, so that the codebase does not carry unused and unmaintained dependencies.

#### Acceptance Criteria

1. WHEN the project dependencies are resolved, THE Security_Service SHALL NOT include `mongo-migrate` in its dependency list (pyproject.toml)
2. WHEN the project is built, THE Security_Service SHALL resolve all dependencies without referencing `mongo-migrate`

### Requirement 2: Migration Tracking

**User Story:** As an operator, I want the migration system to track which migrations have been applied, so that migrations are not re-executed on subsequent startups.

#### Acceptance Criteria

1. THE Migration_System SHALL store a Migration_Record in MongoDB for each successfully completed migration
2. WHEN a migration completes successfully, THE Migration_System SHALL record the migration name, execution timestamp, and a success status in the Migration_Record
3. WHEN the Migration_System starts, THE Migration_System SHALL query MongoDB for existing Migration_Records to determine which migrations have already been applied
4. WHEN a Migration_Record with a success status exists for a given migration, THE Migration_System SHALL skip execution of that migration

### Requirement 3: Startup Execution Order

**User Story:** As an operator, I want migrations to run before the service accepts traffic, so that the database is in a consistent state when API requests arrive.

#### Acceptance Criteria

1. WHEN the Security_Service starts, THE Migration_System SHALL execute all pending migrations before the HTTP server begins accepting requests
2. WHEN the Migration_System detects pending migrations, THE Migration_System SHALL execute the pending migrations in version order
3. IF a migration fails during execution, THEN THE Migration_System SHALL prevent the Security_Service from starting and log the error

### Requirement 4: Idempotent Startup Behavior

**User Story:** As an operator, I want repeated service restarts to be safe, so that the migration system does not duplicate data or corrupt the database.

#### Acceptance Criteria

1. WHEN the Security_Service starts and all migrations have been previously applied, THE Migration_System SHALL proceed to service startup without executing any migrations
2. WHEN the Security_Service starts and all migrations have been previously applied, THE Migration_System SHALL complete the migration check within 5 seconds under normal database load

### Requirement 5: Seed Migration - SecurityType Creation

**User Story:** As a system administrator, I want the initial migration to create the Common Stock security type, so that security records can reference a valid type classification.

#### Acceptance Criteria

1. WHEN the Seed_Migration executes, THE Migration_System SHALL create exactly one document in the SecurityType_Collection with abbreviation "CS", description "Common Stock", and version 1
2. WHEN the Seed_Migration has already been applied, THE Migration_System SHALL not create additional SecurityType documents

### Requirement 6: Seed Migration - Security Records Creation

**User Story:** As a system administrator, I want the initial migration to create 505 S&P 500 constituent security records, so that the application has reference data available at startup.

#### Acceptance Criteria

1. WHEN the Seed_Migration executes, THE Migration_System SHALL create exactly 505 documents in the Security_Collection
2. THE Migration_System SHALL create each Security document with a ticker, description, security_type_id, and version field
3. THE Migration_System SHALL set the version field to 1 for each created Security document
4. WHEN the Seed_Migration executes, THE Migration_System SHALL set the security_type_id of each Security document to the ObjectId of the SecurityType record created in the same migration, maintaining Referential_Integrity

### Requirement 7: Referential Integrity

**User Story:** As a developer, I want all security records to reference a valid security type, so that data queries joining these collections return consistent results.

#### Acceptance Criteria

1. THE Migration_System SHALL create the SecurityType document before creating any Security documents within the Seed_Migration
2. FOR ALL Security documents created by the Seed_Migration, THE Migration_System SHALL set security_type_id to the _id of the SecurityType document created in the same migration execution
3. IF the SecurityType document creation fails, THEN THE Migration_System SHALL abort the Seed_Migration without creating any Security documents
