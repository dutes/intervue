# Stage 1: Build the React Frontend
FROM node:20-alpine AS frontend

WORKDIR /app/client_web

# Install dependencies
COPY client_web/package.json client_web/package-lock.json ./
RUN npm ci

# Copy source and build
COPY client_web/ .
# Add a cache-busting argument if needed, or just rely on file changes
ARG CACHEBUST=1
RUN npm run build
RUN ls -la dist && ls -la dist/assets || echo "No assets found in stage 1"

# Stage 2: Setup the Python Backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY server/ ./server/

# Copy built frontend assets from Stage 1
COPY --from=frontend /app/client_web/dist ./web
RUN ls -R /app/web || echo "No web dir found in stage 2"

# Expose the API port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
