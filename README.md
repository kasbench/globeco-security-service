# GlobeCo Security Service

## Introduction
The **GlobeCo Security Service** is a microservice in the GlobeCo Suite, designed to provide security type and security information for benchmarking autoscaling in Kubernetes environments. This service is not intended for production use and does not contain real data. It is built with Python 13, FastAPI, Beanie, and MongoDB.

## Author
Noah Krieger

## Technology Stack
- Python 13
- FastAPI 0.115.12
- Beanie 1.29 (MongoDB ODM)
- MongoDB
- Pytest (for testing)

## Database
- **Database name:** `securities`
- **Collections:**
  - `securityType`
  - `security`

## Security Type Data Model

| Database Field | API Field         | Type      | Constraints                                  |
|---------------|------------------|-----------|----------------------------------------------|
| _id           | securityTypeId   | ObjectId  | Unique                                       |
| abbreviation  | abbreviation     | String    | Unique, Required, 1-10 characters            |
| description   | description      | String    | Required, 1-100 characters                   |
| version       | version          | Number    | Required, Default: 1                         |

## Security Type API

All endpoints are prefixed with `/api/v1/`.

### DTOs

#### SecurityType
| Verb | Payload Fields                        | Return Fields                                 |
|------|---------------------------------------|-----------------------------------------------|
| GET  |                                       | securityTypeId, abbreviation, description, version |
| POST | abbreviation, description, version     | securityTypeId, abbreviation, description, version |
| PUT  | securityTypeId, abbreviation, description, version | securityTypeId, abbreviation, description, version |
| DELETE |                                     |                                               |

### Endpoints

#### Get all security types
- **GET** `/api/v1/securityTypes`
- **Response:** List of security types

#### Get a specific security type
- **GET** `/api/v1/securityType/{securityTypeId}`
- **Response:** Security type object

#### Create a new security type
- **POST** `/api/v1/securityTypes`
- **Payload:**
  ```json
  {
    "abbreviation": "EQ",
    "description": "Equity security type",
    "version": 1
  }
  ```
- **Response:** Created security type object

#### Update a security type
- **PUT** `/api/v1/securityType/{securityTypeId}`
- **Payload:**
  ```json
  {
    "abbreviation": "EQ",
    "description": "Updated description",
    "version": 1
  }
  ```
- **Response:** Updated security type object

#### Delete a security type
- **DELETE** `/api/v1/securityType/{securityTypeId}?version={version}`
- **Response:** 204 No Content

### Optimistic Concurrency
All update and delete operations require the correct `version` field. If the version does not match, a 409 Conflict is returned.

## Example Usage

**Create a security type:**
```bash
curl -X POST http://localhost:8000/api/v1/securityTypes \
  -H 'Content-Type: application/json' \
  -d '{"abbreviation": "EQ", "description": "Equity", "version": 1}'
```

**Get all security types:**
```bash
curl http://localhost:8000/api/v1/securityTypes
```

**Update a security type:**
```bash
curl -X PUT http://localhost:8000/api/v1/securityType/<securityTypeId> \
  -H 'Content-Type: application/json' \
  -d '{"abbreviation": "EQ", "description": "Updated", "version": 1}'
```

**Delete a security type:**
```bash
curl -X DELETE http://localhost:8000/api/v1/securityType/<securityTypeId>?version=1
```

## Running the Service

1. Ensure MongoDB is running on `localhost:27017`.
2. Install dependencies with `uv pip install -r requirements.txt` (or use `uv` as your package manager).
3. Start the service:
   ```bash
   uvicorn app.main:app --reload
   ```

## Testing

Run all tests with:
```bash
pytest
```

---
For more details, see the `documentation/requirements.md` file.
