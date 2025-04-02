FROM python:3.10-slim

WORKDIR /app
ENV PYTHONPATH=/app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Start with the test API instead
CMD uvicorn src.test_api:app --host 0.0.0.0 --port $PORT