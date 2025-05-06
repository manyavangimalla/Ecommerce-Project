FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable for unbuffered python output
ENV PYTHONUNBUFFERED=1

COPY . .

ENV PRODUCT_SERVICE_URL=http://product-inventory-service.ecommerce.svc.cluster.local
ENV USER_SERVICE_URL=http://user-auth-service.ecommerce.svc.cluster.local
ENV ORDER_SERVICE_URL=http://order-payment-service.ecommerce.svc.cluster.local
ENV NOTIFICATION_SERVICE_URL=http://notification-service.ecommerce.svc.cluster.local

EXPOSE 8080

CMD ["python", "app.py"]