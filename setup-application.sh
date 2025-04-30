#!/bin/bash

# This script sets up the entire application for local or cloud deployment.
# Usage: ./setup-application.sh <build|deploy> <local|cloud>

DEPLOY_ENV=$2
if [ -z "$DEPLOY_ENV" ]; then
  echo "Usage: $0 <build|deploy> <local|cloud>"
  exit 1
fi

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
  for service in "${services[@]}"; do
    echo "Building $service..."
    docker build -t "${service,,}:local" ./$service
  done
}

# Step 2: Push Docker images to registry (for cloud deployment)
push_images() {
  echo "Pushing Docker images to registry..."
  CLOUD_REGISTRY="gcr.io/your-gcp-project-id"
  services=("user_auth_service" "notification_service" "product_inventory_service" "order_payment_service" "api_gateway" "Frontend")
  for service in "${services[@]}"; do
    echo "Pushing $service to $CLOUD_REGISTRY..."
    docker tag "$service:local" "$CLOUD_REGISTRY/$service:latest"
    docker push "$CLOUD_REGISTRY/$service:latest"
  done
}

# Step 3: Deploy using Helm
deploy_with_helm() {
  echo "Deploying application using Helm..."
  if [ "$DEPLOY_ENV" == "cloud" ]; then
    helm upgrade --install ecommerce ./ecommerce \
      --set image.registry="gcr.io/your-gcp-project-id" \
      --set image.tag="latest" \
      --namespace ecommerce
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
  DEPLOY_ENV=$2
  if [ -z "$DEPLOY_ENV" ]; then
    echo "Usage: $0 build <local|cloud>"
    exit 1
  fi
  ensure_namespace
  configure_minikube_docker  # Ensure Minikube's Docker is used for local builds
  build_images
  if [ "$DEPLOY_ENV" == "cloud" ]; then
    push_images
  fi
elif [ "$1" == "deploy" ]; then
  DEPLOY_ENV=$2
  if [ -z "$DEPLOY_ENV" ]; then
    echo "Usage: $0 deploy <local|cloud>"
    exit 1
  fi
  ensure_namespace
  update_configmap
  deploy_with_helm
else
  echo "Invalid command. Usage: $0 <build|deploy> <local|cloud>"
  exit 1
fi

echo "Application setup complete for $DEPLOY_ENV deployment."