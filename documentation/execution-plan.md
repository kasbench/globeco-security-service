# Step-by-Step Instructions

Please perform each step when instructed.  Only perform one step at a time.

1. Configure the project to connect to the MongoDB database on local host at port 27017 and database `securities`. Please add an entry with this prompt and your actions in the cursor-log.md file following the instructions in the file.
2. Please implement the APIs for security type using the requirements provided in @requirements.md.  Please add an entry with this prompt and your actions in the cursor-log.md file following the instructions in the file.
3. Please generate the Pytest tests for all the code you created in the previous step.  Please add an entry with this prompt and your actions in the cursor-log.md file following the instructions in the file.
4. Please update the README.md file with an introduction and full documentation on the security type data model and API.  Please add an entry with this prompt and your actions in the cursor-log.md file following the instructions in the file.
5. Please create an OpenAPI schema `openapi.yaml' in the project root.  Please include the full specification for the security type API.  Please add an entry with this prompt and your actions in the cursor-log.md file following the instructions in the file.
6. Please implement the APIs for security using the requirements provided in @requirements.md.  Use the code for security type as an example.  Strive for consistency.  Please add an entry with this prompt and your actions in the cursor-log.md file following the instructions in the file.
7. Please create pytest tests for the code you created in the previous step.  Please use @test_security_type.py as an example.  Strive for consistency.  Please add an entry with this prompt and your actions in the cursor-log.md file following the instructions in the file.
8. Please add documentation for the security data model and API to readme.md.  Please add an entry with this prompt and your actions in the cursor-log.md file following the instructions in the file.
9. Please update the openapi schema `openapi.yaml` with the spec for security.  Please add an entry with this prompt and your actions in the cursor-log.md file following the instructions in the file.
10. Please create a Dockerfile for this application.  Please add an entry with this prompt and your actions in the cursor-log.md file following the instructions in the file.
11. I will be deploying this service to Kubernetes.  We need to implement liveness, readiness, and startup health checks.  Please implement the probes.
12. Please create all the files necessary to deploy to this application as a service to Kubernetes.  Please include the liveness, readiness, and startup probes you just created.  The deployment should start with one instance of the service and should scale up to a maximum of 100 instances.  It should have up 100 millicores and 200 MiB of memory.  The name of the service is `globeco-security-service` in the `globeco` namespace.  You do not need to create the namespace. Please add an entry with this prompt and your actions in the cursor-log.md file following the instructions in the file.
13. Please document the health checks (liveness, readiness/startup) in the README.md file and the openapi.yaml OpenAPI spec.  Please add an entry with this prompt and your actions in the cursor-log.md file following the instructions in the file.
