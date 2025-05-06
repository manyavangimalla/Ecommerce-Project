FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable for unbuffered python output
ENV PYTHONUNBUFFERED=1

COPY . .

EXPOSE 8080

CMD ["python", "app.py"]