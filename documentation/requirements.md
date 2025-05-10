# GlobeCo Security Service Requirements

## Background
This service is part of the GlobeCo Suite.  The GlobeCo Suite is a set of applications that will be used to benchmark autoscaling in Kubernetes.  These are not production applications and will never contain real data.  They are highly simplified versions of real applications designed to evaluate autoscalers under a variety of conditions.

The service is the GlobeCo Security Service.  In this documentation, we will refer to it as the security service.  The security service is responsible for providing security level information to other services in the GlobeCo suite.  It presents a REST interface.

## Technology
This service is written in Python 13 using FastAPI.  Data is stored in a dedicated MongoDB database.

## Data Model

There will be two MongoDB collections: `securityType` and `security`.

### securityType
`securityType` has the following fields:

| field name | data type | Constraint |
| --- | --- | --- |
| _id | ObjectId | Unique.
| abbreviation | String | Unique.  Required. 1 - 10 characters in length.
| description | String | Required. 1 - 100 characters in length.
| version | Number | Required.  Default to 1. |
---

### security

`security` has the following fields:

| field name | data type | Constraint |
| --- | --- | --- |
| _id | ObjectId | Unique.
| ticker | String | Unique. Required. 1 - 50 characters. |
| description | String | Required. 1 - 200 characters. |
| security_type_id | ObjectId | Foreign key reference to a securityType.  Required. |
| version | number | Required. Default to 1. |
---


## DTOs

When creating or consuming APIs, use the following DTOs.

### securityType

| Verb | Payload Fields | Return Fields |
| --- | --- | --- |
| GET | | _id, abbreviation, description, version | 
| POST | abbreviation, description, version | _id, abbreviation, description, version |
| PUT | _id, abbreviation, description, version | _id, abbreviation, description, version | 
| DELETE | _id,  version | | 
---

### security
| Verb | Payload Fields | Return Fields |
| --- | --- | --- |
| GET |  | _id, ticker, description, security_type (_id, abbreviation, description), version |
| POST | ticker, description, security_type_id, version | _id, ticker, description, security_type (_id, abbreviation, description), version |
| PUT | _id, ticker, description, security_type_id, version | _id, ticker, description, security_type (_id, abbreviation, description), version |
| DELETE | _id, ticker, description, security_type_id, version |  |



