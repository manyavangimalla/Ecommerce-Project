# ElectroCart - Microservices E-commerce Platform
ElectroCart is a robust, microservices-based e-commerce application designed for scalability, security, and efficiency. This project implements a comprehensive architecture with distinct services for different aspects of an e-commerce platform.

# System Architecture
ElectroCart consists of the following microservices:
API Gateway: Routes client requests to appropriate microservices
Frontend Application: Manages user interactions and presentation
User Authentication Service: Handles user registration and authentication
Order Payment Service: Processes orders and payments
Notification Service: Manages email and in-app notifications
Product Inventory Service: Handles product listings and inventory management
Technologies Used
Backend: Python, Flask
Database: PostgreSQL
Caching: Redis
Authentication: JWT (JSON Web Tokens)
Containerization: Docker
Orchestration: Kubernetes
Email Services: SendGrid, Resend API
Prerequisites
Docker and Docker Compose
kubectl for Kubernetes deployment
Google Cloud SDK (for GKE deployment)
Git
Local Development Setup
Clone the Repository

# Create a Python virtual environment (optional but recommended)
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
API Gateway
# Navigate to the API Gateway directory
cd api_gateway

# Install dependencies
pip install -r requirements.txt

# Run the service
python app.py

# The API Gateway will start on http://localhost:5000
Frontend Application
# Navigate to the Frontend directory
cd frontend

# Install dependencies
pip install -r requirements.txt

# Run the service
python app.py

# The Frontend will start on http://localhost:8080
User Authentication Service
# Navigate to the User Authentication Service directory
cd user_auth_service

# Install dependencies
pip install -r requirements.txt

# Run the service
python app.py

# The User Authentication Service will start on http://localhost:5001
Product Inventory Service
# Navigate to the Product Inventory Service directory
cd product_inventory_service

# Install dependencies
pip install -r requirements.txt

# Run the service
python app.py

# The Product Inventory Service will start on http://localhost:5002
Order Payment Service

# Navigate to the Order Payment Service directory
cd order_payment_service

# Install dependencies
pip install -r requirements.txt

# Run the service
python app.py

# The Order Payment Service will start on http://localhost:5003
Notification Service

# Navigate to the Notification Service directory
cd notification_service

# Install dependencies
pip install -r requirements.txt

# Run the service
python app.py

# The Notification Service will start on http://localhost:5004
All Services Combined Installation
If you want to install all dependencies at once (useful for development):

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows

# Install all dependencies
pip install -r api_gateway/requirements.txt
pip install -r frontend/requirements.txt
pip install -r user_auth_service/requirements.txt
pip install -r product_inventory_service/requirements.txt
pip install -r order_payment_service/requirements.txt
pip install -r notification_service/requirements.txt
Running with Environment Variables
For local development, you may need to set environment variables:

# On Windows (PowerShell)
$env:DATABASE_URL="postgresql://postgres:password@localhost:5432/electrocart"
$env:JWT_SECRET="your-secret-key"
$env:REDIS_HOST="localhost"
$env:REDIS_PORT="6379"
python app.py

# On macOS/Linux
DATABASE_URL="postgresql://postgres:password@localhost:5432/electrocart" \
JWT_SECRET="your-secret-key" \
REDIS_HOST="localhost" \
REDIS_PORT="6379" \
python app.py
Using Python-dotenv
Alternatively, you can create a .env file in each service directory and use python-dotenv:

Create a .env file in each service directory with the appropriate variables
Run the service with python app.py (the app will load the environment variables from the .env file)
Database Setup
If you need to set up the PostgreSQL database manually:

# Install PostgreSQL client (if not already installed)
# On Ubuntu/Debian:
sudo apt-get install postgresql-client

# On macOS with Homebrew:
brew install postgresql

# Create database
createdb electrocart

# Connect to database
psql -d electrocart

# In the psql console, you can create tables or run SQL scripts
Redis Setup (for caching)
If you need to install Redis locally:
# On Ubuntu/Debian:
sudo apt-get install redis-server

# On macOS with Homebrew:
brew install redis
brew services start redis

# Verify Redis is running
redis-cli ping
# Should respond with PONG

# Build and start all services
docker-compose -f docker-compose-new.yml up --build

# To run in detached mode
docker-compose -f docker-compose-new.yml up -d

# To stop all services
docker-compose -f docker-compose-new.yml down
Accessing Services Locally
Frontend: http://localhost:8080
API Gateway: http://localhost:5000
User Service: http://localhost:5001
Product Service: http://localhost:5002
Order Service: http://localhost:5003
Notification Service: http://localhost:5004
Google Kubernetes Engine (GKE) Deployment
1. Set Up Google Cloud Project
# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project Project-ID
# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable artifactregistry.googleapis.com
2. Create Artifact Repository
# Create Docker repository
gcloud artifacts repositories create electrocart-repo \
    --repository-format=docker \
    --location=us-central1 \
    --description="ElectroCart Docker repository"

# Configure Docker to use gcloud credentials
gcloud auth configure-docker us-central1-docker.pkg.dev
3. Build and Push Docker Images
# API Gateway
cd api_gateway
docker build -t us-central1-docker.pkg.dev/Project-ID/electrocart-repo/api-gateway:latest .
docker push us-central1-docker.pkg.dev/Project-ID/electrocart-repo/api-gateway:latest
cd ..

# Frontend
cd frontend
docker build -t us-central1-docker.pkg.dev/Project-ID/electrocart-repo/frontend:latest .
docker push us-central1-docker.pkg.dev/Project-ID/electrocart-repo/frontend:latest
cd ..

# User Service
cd user_service
docker build -t us-central1-docker.pkg.dev/Project-ID/electrocart-repo/user-service:latest .
docker push us-central1-docker.pkg.dev/Project-ID/electrocart-repo/user-service:latest
cd ..

# Product Service
cd product_service
docker build -t us-central1-docker.pkg.dev/Project-ID/electrocart-repo/product-service:latest .
docker push us-central1-docker.pkg.dev/Project-ID/electrocart-repo/product-service:latest
cd ..

# Order Service
cd order_service
docker build -t us-central1-docker.pkg.dev/Project-ID/electrocart-repo/order-service:latest .
docker push us-central1-docker.pkg.dev/Project-ID/electrocart-repo/order-service:latest
cd ..

# Notification Service
cd notification_service
docker build -t us-central1-docker.pkg.dev/Project-ID/electrocart-repo/notification-service:latest .
docker push us-central1-docker.pkg.dev/Project-ID/electrocart-repo/notification-service:latest
cd ..
4. Create GKE Cluster

gcloud container clusters create electrocart-cluster \
    --num-nodes=3 \
    --zone=us-central1-a \
    --machine-type=e2-medium
5. Configure kubectl

gcloud container clusters get-credentials electrocart-cluster --zone=us-central1-a
6. Deploy to Kubernetes

#Apply Kubernetes configuration
kubectl apply -f all-services.yaml

#Check deployment status
kubectl get pods
kubectl get services
7. Access the Application

#Get the external IP for your frontend service
kubectl get service frontend-service

Key environment variables include:
Database connection strings
JWT secret keys
Service URLs
API keys for external services
Monitoring and Maintenance
#Check logs for a specific service
kubectl logs deployment/api-gateway

#Scale a deployment
kubectl scale deployment/frontend --replicas=3

#Update a deployment
kubectl set image deployment/api-gateway api-gateway=us-central1-docker.pkg.dev/Project-ID/electrocart-repo/api-gateway:v2
Branching Strategy
master: Production-ready code
local_deployment: For local development and testing
Contributing
Fork the repository
Create your feature branch (git checkout -b feature/amazing-feature)
Commit your changes (git commit -m 'Add some amazing feature')
Push to the branch (git push origin feature/amazing-feature)
Open a Pull Request
License
This project is licensed under the MIT License - see the LICENSE file for details.

Acknowledgments
Flask framework and its ecosystem
Google Kubernetes Engine
Docker and container orchestration technologies
The open source community


## Contributions

- **Manya Shree**:  
  Developed and enhanced both frontend and backend features. Implemented core frontend logic in `frontend/` and designed user-facing pages (product listing, product detail, cart, checkout, registration, and login). Contributed to the backend logic and API integration for the product and order services, ensuring seamless user experience and robust order workflows.

- **Shubham Ghadge**:  
  Managed the Kubernetes environment and Helm chart configurations (`ecommerce/`). Automated service orchestration and deployment pipelines, including writing and maintaining the `setup-application.sh` and `cloud/gcp.sh` scripts. Explored and integrated monitoring tools for service health, and authored comprehensive testing scripts for end-to-end validation.

- **Sreeja**:  
  Developed the user authentication (`user_auth_service/`) and notification (`notification_service/`) microservices, including their APIs, models, and integration logic. Assisted in deploying and testing services on Kubernetes, and ensured consistent document formatting and code quality across the project.

- **Karthik Reddy Thippareddy**:  
  Set up Dockerfiles for all services, developed the API Gateway (`api_gateway/`), and handled service integration and routing. Led the integration of microservices, ensuring smooth inter-service communication, and participated in final system testing and troubleshooting.