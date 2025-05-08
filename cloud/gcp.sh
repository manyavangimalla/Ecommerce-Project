#!/bin/bash

# GCP-specific build/push/deploy logic for the ecommerce project
# Usage: ./cloud/gcp.sh <build|deploy> <gcp> <services> <force_rebuild>

GCP_PROJECT_ID="cogent-joy-453920-v4"  # TODO: Replace or make dynamic
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
  echo "Detecting service directories with Dockerfile..."
  SERVICE_DIRS=( $(find . -maxdepth 1 -type d \( -name 'user_auth_service' -o -name 'product_inventory_service' -o -name 'order_payment_service' -o -name 'notification_service' -o -name 'frontend' -o -name 'api_gateway' \) -exec test -f {}/Dockerfile \; -print | sed 's|^./||') )
  echo "Found services: ${SERVICE_DIRS[*]}"
  echo "Building and pushing Docker images to $CLOUD_REGISTRY..."
  for service in "${SERVICE_DIRS[@]}"; do
    IMAGE_NAME="$service:latest"
    echo "Building $service as $IMAGE_NAME..."
    if [ "$FORCE_REBUILD" = true ]; then
      docker build --no-cache -t "$IMAGE_NAME" ./$service
    else
      docker build -t "$IMAGE_NAME" ./$service
    fi
    echo "Tagging $IMAGE_NAME for GCR..."
    docker tag "$IMAGE_NAME" "$CLOUD_REGISTRY/$IMAGE_NAME"
    echo "Pushing $IMAGE_NAME to $CLOUD_REGISTRY..."
    docker push "$CLOUD_REGISTRY/$IMAGE_NAME"
  done
}

deploy_with_helm() {
  echo "Deploying application to GKE using Helm..."
  # kubectl get namespace ecommerce >/dev/null 2>&1 || kubectl create namespace ecommerce
  helm upgrade --install ecommerce ./ecommerce \
    --set image.registry="$CLOUD_REGISTRY" \
    --set image.tag="latest" \
    -f ecommerce/values-gke.yaml \
    --namespace ecommerce \
    --create-namespace
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
