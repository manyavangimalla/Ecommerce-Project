# E-commerce Microservices Platform

A distributed e-commerce application built with a microservices architecture.

## Services

- **API Gateway**: Entry point for all client requests
- **User Auth Service**: Handles user authentication and authorization
- **Product Inventory Service**: Manages product catalog and inventory
- **Order Payment Service**: Processes orders and payments
- **Notification Service**: Sends notifications to users
- **Frontend**: Web interface for the e-commerce platform

## Technology Stack

- Python Flask for microservices
- Docker and Docker Compose for containerization
- Bootstrap for frontend styling

## Configuration & Deployment

All configuration is handled via environment variables for maximum portability and security. This enables seamless deployment to local, GKE, or any cloud provider.

### Required Environment Variables

| Service                  | Variable         | Description                                 |
|--------------------------|------------------|---------------------------------------------|
| All services             | DB_USER          | Database username                           |
| All services             | DB_PASSWORD      | Database password                           |
| All services             | DB_HOST          | Database host                               |
| All services             | DB_PORT          | Database port                               |
| All services             | DB_NAME          | Database name                               |
| All services             | JWT_SECRET       | JWT secret key                              |
| notification_service     | SMTP_SERVER      | SMTP server for email notifications         |
| notification_service     | SMTP_PORT        | SMTP port                                   |
| notification_service     | SMTP_USERNAME    | SMTP username                               |
| notification_service     | SMTP_PASSWORD    | SMTP password                               |
| notification_service     | SENDER_EMAIL     | Sender email address                        |
| product_inventory_service| REDIS_HOST       | Redis host for caching                      |
| product_inventory_service| REDIS_PORT       | Redis port                                  |
| All services             | (other service-specific vars as needed) |

### Local Development
- Use a `.env` file or Docker Compose to set environment variables.
- See each service's README or Dockerfile for details.

### GKE/Cloud Deployment
- Use Helm charts in the `ecommerce/` directory.
- All environment variables are injected via Kubernetes ConfigMaps and Secrets.
- See `cloud/gcp.sh` for GKE build/deploy automation.

### Multicloud
- Override values in `ecommerce/values.yaml` or via `helm install --set ...` for other clouds.

## Getting Started

### Prerequisites

- Docker and Docker Compose

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/YOUR-USERNAME/e-commerce-microservices.git
   cd e-commerce-microservices

## Deployment: Local and Cloud

This project provides a unified script for building and deploying the application in both local and cloud environments.

### Usage

```
./setup-application.sh --action build|deploy --env local|cloud [--cloud-provider gcp] [--force-rebuild true|false] [--services service1,service2,...]
```

- `--action` (required): `build` or `deploy`
- `--env` (required): `local` or `cloud`
- `--cloud-provider` (required if `--env cloud`): currently only `gcp` is supported
- `--force-rebuild` (optional): `true` or `false` (default: false)
- `--services` (optional): comma-separated list of services to build/deploy (default: all detected services)

### Examples

**Local build:**
```
./setup-application.sh --action build --env local
```

**Local deploy:**
```
./setup-application.sh --action deploy --env local
```

**Cloud build (GCP):**
```
./setup-application.sh --action build --env cloud --cloud-provider gcp
```

**Cloud deploy (GCP):**
```
./setup-application.sh --action deploy --env cloud --cloud-provider gcp
```

**With force rebuild:**
```
./setup-application.sh --action build --env cloud --cloud-provider gcp --force-rebuild true
```

**With specific services:**
```
./setup-application.sh --action build --env local --services user_auth_service,frontend
```
