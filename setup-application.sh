#!/bin/bash

set -e

# Default values
ACTION=""
ENVIRONMENT=""
FORCE_REBUILD="false"
SERVICES=""
CLOUD_PROVIDER=""

# Helper: print usage
usage() {
  echo "Usage: $0 --action build|deploy --env local|cloud [--cloud-provider gcp] [--force-rebuild true|false] [--services service1,service2,...]"
  exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --action)
      ACTION="$2"
      shift 2
      ;;
    --env)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --cloud-provider)
      CLOUD_PROVIDER="$2"
      shift 2
      ;;
    --force-rebuild)
      FORCE_REBUILD="$2"
      shift 2
      ;;
    --services)
      SERVICES="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      ;;
  esac
done

# Validate required args
if [[ -z "$ACTION" || -z "$ENVIRONMENT" ]]; then
  usage
fi

# If env is cloud, --cloud-provider is required
if [[ "$ENVIRONMENT" == "cloud" ]]; then
  if [[ -z "$CLOUD_PROVIDER" ]]; then
    echo "Error: --cloud-provider flag is required when --env is cloud."
    usage
  fi
  if [[ "$CLOUD_PROVIDER" != "gcp" ]]; then
    echo "Error: Only 'gcp' is currently supported for --cloud-provider."
    exit 1
  fi
fi

# Detect services if not provided
detect_services() {
  find . -maxdepth 1 -type d \( -name 'user_auth_service' -o -name 'product_inventory_service' -o -name 'order_payment_service' -o -name 'notification_service' -o -name 'frontend' -o -name 'api_gateway' \) -exec test -f {}/Dockerfile \; -print | sed 's|^./||'
}

if [[ -z "$SERVICES" ]]; then
  SERVICES=$(detect_services | paste -sd "," -)
fi

IFS=',' read -r -a SERVICE_ARRAY <<< "$SERVICES"

# Build images
build_images_local() {
  echo "Building Docker images for local..."
  for service in "${SERVICE_ARRAY[@]}"; do
    echo "Building $service..."
    if [[ "$FORCE_REBUILD" == "true" ]]; then
      docker build --no-cache -t "${service,,}:local" ./$service
    else
      docker build -t "${service,,}:local" ./$service
    fi
  done
}

deploy_local() {
  echo "Deploying application using Helm (local)..."
  helm upgrade --install ecommerce ./ecommerce \
    --set image.registry="" \
    --set image.tag="local" \
    --namespace ecommerce
}

# Main logic
if [[ "$ENVIRONMENT" == "local" ]]; then
  if [[ "$ACTION" == "build" ]]; then
    build_images_local
  elif [[ "$ACTION" == "deploy" ]]; then
    deploy_local
  else
    usage
  fi
elif [[ "$ENVIRONMENT" == "cloud" ]]; then
  if [[ "$CLOUD_PROVIDER" == "gcp" ]]; then
    if [[ "$ACTION" == "build" ]]; then
      ./cloud/gcp.sh build "$CLOUD_PROVIDER" "$FORCE_REBUILD"
    elif [[ "$ACTION" == "deploy" ]]; then
      ./cloud/gcp.sh deploy "$CLOUD_PROVIDER"
    else
      usage
    fi
  else
    echo "Cloud provider $CLOUD_PROVIDER not supported yet."
    exit 1
  fi
else
  usage
fi

echo "Application setup complete for $ENVIRONMENT deployment."