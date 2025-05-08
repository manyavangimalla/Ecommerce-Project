FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create templates directory
RUN mkdir -p /app/templates

# Copy templates
COPY templates/ /app/templates/

# Copy the rest of the application
COPY *.py .

EXPOSE 5004

CMD ["python", "app.py"]