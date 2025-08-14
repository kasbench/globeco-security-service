docker buildx build --platform linux/amd64,linux/arm64 -t kasbench/globeco-security-service:latest --push .
kubectl delete -f k8s/deployment.yaml
kubectl apply -f k8s/deployment.yaml