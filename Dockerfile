FROM python:3.10-slim

WORKDIR /app
ENV PYTHONPATH=/app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure FAISS index directory exists
RUN mkdir -p /app/faiss_index

# Start the FastAPI server
CMD uvicorn src.webhook_api:app --host 0.0.0.0 --port $PORT