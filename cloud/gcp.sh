#!/bin/bash

# GCP-specific build/push/deploy logic for the ecommerce project
# Usage: ./cloud/gcp.sh <build|deploy> <gcp> <services> <force_rebuild>

GCP_PROJECT_ID="your-gcp-project-id"  # TODO: Replace or make dynamic
CLOUD_REGISTRY="gcr.io/$GCP_PROJECT_ID"

COMMAND=$1
DEPLOY_ENV=$2
SERVICES=($3)
FORCE_REBUILD=$4

if [ -z "$GCP_PROJECT_ID" ] || [ "$GCP_PROJECT_ID" == "your-gcp-project-id" ]; then
  echo "Please set your GCP_PROJECT_ID in cloud/gcp.sh."
  exit 1
fi

gcp_auth() {
  echo "Authenticating with Google Cloud..."
  gcloud auth configure-docker
}

build_and_push_images() {
  echo "Building and pushing Docker images to $CLOUD_REGISTRY..."
  for service in "${SERVICES[@]}"; do
    echo "Building $service..."
    if [ "$FORCE_REBUILD" = true ]; then
      docker build --no-cache -t "$service:latest" ./$service
    else
      docker build -t "$service:latest" ./$service
    fi
    echo "Tagging $service for GCR..."
    docker tag "$service:latest" "$CLOUD_REGISTRY/$service:latest"
    echo "Pushing $service to $CLOUD_REGISTRY..."
    docker push "$CLOUD_REGISTRY/$service:latest"
  done
}

deploy_with_helm() {
  echo "Deploying application to GKE using Helm..."
  helm upgrade --install ecommerce ./ecommerce \
    --set image.registry="$CLOUD_REGISTRY" \
    --set image.tag="latest" \
    --namespace ecommerce
}

case $COMMAND in
  build)
    gcp_auth
    build_and_push_images
    ;;
  deploy)
    deploy_with_helm
    ;;
  *)
    echo "Invalid command for GCP script. Use build or deploy."
    exit 1
    ;;
esac
