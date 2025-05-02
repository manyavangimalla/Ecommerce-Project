FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV API_URL=http://api-gateway.ecommerce.svc.cluster.local

EXPOSE 8080

CMD ["python", "app.py"]