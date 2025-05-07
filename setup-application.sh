#!/bin/bash

# This script sets up the entire application for local or cloud deployment.
# Usage: ./setup-application.sh <build|deploy> [--force-rebuild] [--services=<service1,service2,...>]

# Prompt for deployment target if not provided
if [ -z "$1" ] || { [ "$1" != "build" ] && [ "$1" != "deploy" ]; }; then
  echo "Usage: $0 <build|deploy> [--force-rebuild] [--services=<service1,service2,...>]"
  exit 1
fi

# Prompt for environment if not provided
if [ -z "$2" ]; then
  echo "Select deployment target:"
  echo "1) Local (Minikube)"
  echo "2) Cloud (GCP)"
  read -p "Enter choice [1-2]: " choice
  case $choice in
    1)
      DEPLOY_ENV="local"
      ;;
    2)
      DEPLOY_ENV="gcp"
      ;;
    *)
      echo "Invalid choice. Exiting."
      exit 1
      ;;
  esac
else
  DEPLOY_ENV=$2
fi

# Check for force rebuild flag
FORCE_REBUILD=false
if [[ "$@" =~ "--force-rebuild" ]]; then
  FORCE_REBUILD=true
fi

# Parse arguments for specific flags
SERVICES=()
for arg in "$@"; do
  case $arg in
    --services=*)
      IFS=',' read -r -a SERVICES <<< "${arg#*=}"
      ;;
  esac
done

# Step 0: Ensure namespace exists and is properly labeled/annotated
ensure_namespace() {
  echo "Ensuring namespace exists and is properly configured..."
  
  echo "Namespace 'ecommerce' not found. Creating it..."
  kubectl create namespace ecommerce
  
  echo "Namespace 'ecommerce' already exists. Ensuring proper labels and annotations..."
  kubectl label namespace ecommerce app.kubernetes.io/managed-by=Helm --overwrite
  kubectl annotate namespace ecommerce meta.helm.sh/release-name=ecommerce --overwrite
  kubectl annotate namespace ecommerce meta.helm.sh/release-namespace=ecommerce --overwrite
}

# Step 0.5: Configure Minikube's Docker environment (for local deployment)
configure_minikube_docker() {
  if [ "$DEPLOY_ENV" == "local" ]; then
    echo "Configuring Minikube's Docker environment..."
    eval $(minikube docker-env)
  fi
}

# Step 1: Build Docker images
build_images() {
  echo "Building Docker images..."
  services=("user_auth_service" "notification_service" "product_inventory_service" "order_payment_service" "api_gateway" "frontend")

  # Use the services specified by the --services flag, if provided
  if [ "${#SERVICES[@]}" -gt 0 ]; then
    services=("${SERVICES[@]}")
  fi

  for service in "${services[@]}"; do
    echo "Building $service..."
    if [ "$FORCE_REBUILD" = true ]; then
      docker build --no-cache -t "${service,,}:local" ./$service
    else
      docker build -t "${service,,}:local" ./$service
    fi
  done
}

# Step 2: Push Docker images to registry (for cloud deployment)
push_images() {
  echo "Pushing Docker images to registry..."
  # This will be handled by cloud/gcp.sh for GCP
}

# Step 3: Deploy using Helm
deploy_with_helm() {
  echo "Deploying application using Helm..."
  if [ "$DEPLOY_ENV" == "gcp" ]; then
    # Call GCP-specific deployment script
    ./cloud/gcp.sh "$1" "$DEPLOY_ENV" "${SERVICES[@]}" "$FORCE_REBUILD"
    return
  elif [ "$DEPLOY_ENV" == "local" ]; then
    helm upgrade --install ecommerce ./ecommerce \
      --set image.registry="" \
      --set image.tag="local" \
      --namespace ecommerce
  else
    echo "Invalid deployment environment: $DEPLOY_ENV"
    exit 1
  fi
}

# Step 4: Update or create ConfigMap for deployment environment
update_configmap() {
  echo "Ensuring ConfigMap exists and is updated for deployment environment..."
  
  kubectl create configmap ecommerce-config \
      --namespace ecommerce \
      --from-literal=DEPLOY_ENV="$DEPLOY_ENV"
  
    echo "Updating existing ConfigMap 'ecommerce-config'..."
    kubectl label configmap ecommerce-config app.kubernetes.io/managed-by=Helm --namespace ecommerce --overwrite
    kubectl annotate configmap ecommerce-config meta.helm.sh/release-name=ecommerce --namespace ecommerce --overwrite
    kubectl annotate configmap ecommerce-config meta.helm.sh/release-namespace=ecommerce --namespace ecommerce --overwrite
    kubectl patch configmap ecommerce-config \
      --namespace ecommerce \
      --type merge \
      --patch "{\"data\":{\"DEPLOY_ENV\":\"$DEPLOY_ENV\"}}"
}

# Main script execution
if [ "$1" == "build" ]; then
  ensure_namespace
  configure_minikube_docker  # Ensure Minikube's Docker is used for local builds
  build_images
  if [ "$DEPLOY_ENV" == "gcp" ]; then
    # Call GCP-specific build/push logic
    ./cloud/gcp.sh build "$DEPLOY_ENV" "${SERVICES[@]}" "$FORCE_REBUILD"
  fi
elif [ "$1" == "deploy" ]; then
  ensure_namespace
  update_configmap
  deploy_with_helm "$1"
else
  echo "Invalid command. Usage: $0 <build|deploy> [--force-rebuild] [--services=<service1,service2,...>]"
  exit 1
fi

echo "Application setup complete for $DEPLOY_ENV deployment."