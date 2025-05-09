# E-commerce Microservices Platform

A distributed e-commerce application built with a microservices architecture, supporting both local and Google Cloud (GKE) deployments.

---

## Code Structure

```
.
├── api_gateway/                # API Gateway microservice
├── cloud/
│   └── gcp.sh                  # GCP build/push/deploy automation script
├── ecommerce/                  # Helm chart for Kubernetes deployment
│   ├── templates/              # Helm templates
│   ├── Chart.yaml              # Helm chart metadata
│   ├── values.yaml             # Default Helm values
│   └── values-gke.yaml         # GKE-specific Helm values
├── frontend/                   # Frontend web application
├── notification_service/       # Notification microservice
├── order_payment_service/      # Order and payment microservice
├── product_inventory_service/  # Product inventory microservice
├── setup-application.sh        # Unified build/deploy script
├── user_auth_service/          # User authentication microservice
└── README.md                   # Project documentation
```

---

## Microservices Overview

- **API Gateway**: Entry point for all client requests, routes to backend services.
- **User Auth Service**: Handles user authentication and authorization.
- **Product Inventory Service**: Manages product catalog and inventory, uses Redis for caching.
- **Order Payment Service**: Processes orders and payments.
- **Notification Service**: Sends notifications (email, etc.) to users.
- **Frontend**: Web interface for the e-commerce platform.

Each service is a standalone Python Flask app, containerized with Docker.

---

## Dependencies

Each service has its own `requirements.txt`. Key dependencies include:

- **Flask** (all services)
- **Flask-SQLAlchemy** (all backend services)
- **psycopg2-binary** (PostgreSQL driver)
- **PyJWT** (JWT authentication)
- **python-dotenv** (environment variable management)
- **requests** (HTTP requests)
- **redis** (Product Inventory Service)
- **nats-py** (Order Payment, Notification Services)
- **sendgrid** (Notification Service)
- **Flask-Login, Flask-WTF** (Frontend)

See each service's `requirements.txt` for details.

---

## Environment Configuration

All configuration is handled via environment variables for portability andsecurity.
                |


## Local Development

- Modify the `values.yaml` file to set configuration variables.
- Each service can be run and tested independently.
- Build and deploy all services locally using the unified script:

```bash
./setup-application.sh --action build --env local
./setup-application.sh --action deploy --env local
```
```bash
# optional --services flag to build images for specific services
./setup-application.sh --action build --env local --services frontend,user_auth_service
```

---

## GKE Deployment Prerequisites & Setup

To deploy this application on Google Kubernetes Engine (GKE), you need to:

### 1. Install Required Tools

- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
- [Docker](https://docs.docker.com/get-docker/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm](https://helm.sh/docs/intro/install/)

### 2. Authenticate with Google Cloud

```bash
gcloud auth login
gcloud auth application-default login
```

### 3. Set Your GCP Project

Edit the file `cloud/gcp.sh` and set your project ID:

```bash
GCP_PROJECT_ID="your-gcp-project-id"
```

You can find your project ID and project number in the [GCP Console](https://console.cloud.google.com/cloud-resource-manager).

Set your project in the CLI:

```bash
gcloud config set project YOUR_PROJECT_ID
```

### 4. Enable Required GCP APIs

```bash
gcloud services enable container.googleapis.com containerregistry.googleapis.com
```

### 5. Create a GKE Cluster

```bash
gcloud container clusters create ecommerce-cluster \
  --zone us-central1-a \
  --num-nodes 3
```

You can customize the cluster name, zone, and node count as needed.

### 6. Get GKE Cluster Credentials

```bash
gcloud container clusters get-credentials ecommerce-cluster --zone us-central1-a
```

This updates your `kubeconfig` so `kubectl` and `helm` can access your cluster.

### 7. (Optional) Configure Docker to Use GCR

The build script will run this, but you can do it manually if needed:

```bash
gcloud auth configure-docker
```

---

## Where to Set Project ID and Project Number

- **Project ID:**  
  Set in `cloud/gcp.sh` as `GCP_PROJECT_ID="your-gcp-project-id"`.
- **Project Number:**  
  Not directly required by the scripts, but may be needed for IAM or billing. Find it in the GCP Console if needed.

---

**After completing these steps, you can use the unified script to build and deploy:**

```bash
./setup-application.sh --action build --env cloud --cloud-provider gcp
./setup-application.sh --action deploy --env cloud --cloud-provider gcp
```

---

## Helm Chart Structure

- **Chart.yaml**: Metadata for the chart.
- **values.yaml**: Default configuration (image tags, service types, ingress, resources, etc.).
- **values-gke.yaml**: GKE-specific overrides (ingress, hosts, etc.).
- **templates/**: Kubernetes manifests for all services.

---

## Unified Build/Deploy Script

The `setup-application.sh` script provides a single entry point for building and deploying the entire stack, both locally and on GCP.

**Usage:**
```bash
./setup-application.sh --action build|deploy --env local|cloud [--cloud-provider gcp] [--force-rebuild true|false] [--services service1,service2,...]
```

- `--action` (required): `build` or `deploy`
- `--env` (required): `local` or `cloud`
- `--cloud-provider` (required if `--env cloud`): currently only `gcp` is supported
- `--force-rebuild` (optional): `true` or `false` (default: false)
- `--services` (optional): comma-separated list of services to build/deploy (default: all detected services)

---

## Example Commands

**Local build and deploy:**
```bash
./setup-application.sh --action build --env local
./setup-application.sh --action deploy --env local
```

**Cloud build and deploy (GCP):**
```bash
./setup-application.sh --action build --env cloud --cloud-provider gcp
./setup-application.sh --action deploy --env cloud --cloud-provider gcp
```

**With force rebuild:**
```bash
./setup-application.sh --action build --env cloud --cloud-provider gcp --force-rebuild true
```

**With specific services:**
```bash
./setup-application.sh --action build --env local --services user_auth_service,frontend
```

---

## Cloud Resources

- **Google Kubernetes Engine (GKE)**: Hosts the Kubernetes cluster.
- **Google Container Registry (GCR)**: Stores Docker images.
- **Helm**: Manages Kubernetes deployments.
- **Ingress (nginx)**: Handles external traffic routing.

---

## Contributions

- **Manya Shree**:  
  Developed and enhanced both frontend and backend features. Implemented core frontend logic in `frontend/` and designed user-facing pages (product listing, product detail, cart, checkout, registration, and login). Contributed to the backend logic and API integration for the product and order services, ensuring seamless user experience and robust order workflows.

- **Shubham Ghadge**:  
  Managed the Kubernetes environment and Helm chart configurations (`ecommerce/`). Automated service orchestration and deployment pipelines, including writing and maintaining the `setup-application.sh` and `cloud/gcp.sh` scripts. Explored and integrated monitoring tools for service health, and authored comprehensive testing scripts for end-to-end validation.

- **Sreeja**:  
  Developed the user authentication (`user_auth_service/`) and notification (`notification_service/`) microservices, including their APIs, models, and integration logic. Assisted in deploying and testing services on Kubernetes, and ensured consistent document formatting and code quality across the project.

- **Karthik Reddy Thippareddy**:  
  Set up Dockerfiles for all services, developed the API Gateway (`api_gateway/`), and handled service integration and routing. Led the integration of microservices, ensuring smooth inter-service communication, and participated in final system testing and troubleshooting.


