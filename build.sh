docker buildx build --platform linux/amd64,linux/arm64 \
-t kasbench/globeco-security-service:latest \
-t kasbench/globeco-security-service:1.0.1 \
--push .
