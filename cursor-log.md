Instructions:
- Log every request that you receive.
- Log every action that you take in an enumerated list.
- Follow the format provided in the sample below.
- Make sure there are two blank lines between each section.


Prompt: Please perform step 1 in @execution-plan.md
Actions:
1. Checked the migrations directory and found it empty.
2. Investigated the beanie migration template and models for structure.
3. Created migrations/001_create_security_type.py to define Forward and Backward classes for the securityType collection, including a unique index on abbreviation.

Prompt: Perform step 2 in @execution-plan.md
Actions:
1. Reviewed the example migration in migrations/001_create_security_type.py.
2. Created migrations/002_create_security.py to define Forward and Backward classes for the security collection, including a unique index on ticker and an index on security_type_id.

Prompt: Perform step 3 in @execution-plan.md
Actions:
1. Created app/config.py to store MongoDB connection settings using Pydantic BaseSettings.
2. Updated app/main.py to initialize the MongoDB connection and Beanie ODM using the settings from config.py, connecting to localhost:27017.

Prompt: Execute step 4 of @execution-plan.md
Actions:
1. Created beanie-migration.sh in the project root to run all Python migration scripts in the migrations directory using uv python.



