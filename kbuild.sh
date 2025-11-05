docker buildx build --platform linux/amd64,linux/arm64 \
-t kasbench/globeco-security-service:latest \
-t kasbench/globeco-security-service:1.0.0 \
--push .
kubectl delete -f k8s/deployment.yaml
kubectl apply -f k8s/deployment.yaml