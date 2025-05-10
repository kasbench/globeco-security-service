# GlobeCo Security Service Requirements

## Background
This service is part of the GlobeCo Suite.  The GlobeCo Suite is a set of applications that will be used to benchmark autoscaling in Kubernetes.  These are not production applications and will never contain real data.  They are highly simplified versions of real applications designed to evaluate autoscalers under a variety of conditions.

The service is the GlobeCo Security Service.  In this documentation, we will refer to it as the security service.  The security service is responsible for providing security level information to other services in the GlobeCo suite.  It presents a REST interface.

## Technology
This service is written in Python 13 using FastAPI.  Data is stored in a dedicated MongoDB database.

## Data Model

The database name is `securities`

There will be two MongoDB collections: `securityType` and `security`.

### securityType
`securityType` has the following fields:

| database field name | API field name | data type | Constraint |
| --- | --- | --- | --- |
| _id | securityTypeId | ObjectId | Unique.
| abbreviation | abbreviation | String | Unique.  Required. 1 - 10 characters in length.
| description | description | String | Required. 1 - 100 characters in length.
| version | version | Number | Required.  Default to 1. |
---

### security

`security` has the following fields:

| database field name | API field name | data type | Constraint |
| --- | --- | --- | --- |
| _id | securityId |ObjectId | Unique.
| ticker | ticker |String | Unique. Required. 1 - 50 characters. |
| description | description |String | Required. 1 - 200 characters. |
| security_type_id | securityTypeId | ObjectId | Foreign key reference to a securityType.  Required. |
| version | version | number | Required. Default to 1. |
---


## DTOs

When creating or consuming APIs, use the following DTOs.

### securityType

| Verb | Payload Fields | Return Fields |
| --- | --- | --- |
| GET | | securityTypeId, abbreviation, description, version | 
| POST | abbreviation, description, version | securityTypeId, abbreviation, description, version |
| PUT | securityTypeId, abbreviation, description, version | securityTypeId, abbreviation, description, version | 
| DELETE | | | 
---

### security
| Verb | Payload Fields | Return Fields |
| --- | --- | --- |
| GET |  | securityId, ticker, description, securityType (securityTypeId, abbreviation, description), version |
| POST | ticker, description, securityTypeId, version | securityId, ticker, description, securityType (securityTypeId, abbreviation, description), version |
| PUT | securityTypeId, ticker, description, securityTypeId, version | securityId, ticker, description, securityType (securityTypeId, abbreviation, description), version |
| DELETE | |  |
---

## APIs

- Prefix all APIs with /api/v1/
- Use the DTOs specified above for payloads and return DTOs
- Use standard HTTP return codes
- All API implementations should use optimistic concurrency based on the `version` field.

### securityType

| Verb | URI | Description |
| --- | --- | --- |
| GET | securityTypes | Get all security types |
| GET | securityType/{securityTypeId} | Get the specified security type |
| POST | securityTypes | Add a new security type |
| PUT | securityType/{securityTypeId} | Update the specified security type |
| DELETE | securityType/{securityTypeId}?version={version} | Delete the specified security type |
---

### security

| Verb | URI | Description |
| --- | --- | --- |
| GET | securities | Get all securities |
| GET | security/{securityId} | Get the specified security |
| POST | securities | Add a new security |
| PUT | security/{securityId} | Update the specified security |
| DELETE | security/{securityId}?version={version} | Delete the specified security |
---

