FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies first (optimizes Docker caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the scripts and src directories into the container
COPY scripts/ ./scripts/
COPY src/ ./src/

# Runs the database migration script first, then boots FastAPI using uvicorn
CMD ["sh", "-c", "python scripts/init_db.py && uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]