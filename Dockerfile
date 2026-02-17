# Stage 1: Build the React Frontend
FROM node:20-alpine AS frontend

WORKDIR /app/client_web

# Install dependencies (cache based on package.json)
COPY client_web/package.json client_web/package-lock.json ./
RUN npm ci

# Copy source and build
COPY client_web/ .
RUN ls -R .
RUN cat index.html
RUN ls -la src/ || echo "src/ not found"
RUN npm run build
RUN ls -R dist/ || echo "dist/ not found"

# Stage 2: Setup the Python Backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for some python packages)
# RUN apt-get update && apt-get install -y --no-install-recommends ...

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY server/ ./server/

# Copy built frontend assets from Stage 1 to where the backend expects them
# We'll put them in /app/web, and update main.py to look there
COPY --from=frontend /app/client_web/dist ./web

# Expose the API port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
