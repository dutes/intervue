# Stage 1: Build the React Frontend
FROM node:22-alpine AS frontend

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

# Install system dependencies (curl for the LLM clients + downloads; ca-certificates for HTTPS)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# --- Piper local neural TTS ---
# Bundle the Piper binary + a multi-speaker voice (en_US-libritts_r-medium, 904 speakers) so
# read-aloud works fully offline, with no API key, inside the container. The tarball extracts
# to /opt/piper/ (executable + bundled onnxruntime/espeak-ng libs and data).
ARG PIPER_VERSION=2023.11.14-2
RUN curl -sSL -o /tmp/piper.tar.gz \
        "https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/piper_linux_x86_64.tar.gz" \
    && tar -xzf /tmp/piper.tar.gz -C /opt \
    && rm /tmp/piper.tar.gz \
    && /opt/piper/piper --help > /dev/null 2>&1 || true

# Voice model + its config must sit side by side; Piper auto-loads <model>.onnx.json.
RUN mkdir -p /app/voices \
    && curl -sSL -o /app/voices/en_US-libritts_r-medium.onnx \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx" \
    && curl -sSL -o /app/voices/en_US-libritts_r-medium.onnx.json \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx.json"

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
ENV PYTHONUNBUFFERED=1 \
    TTS_PROVIDER=piper \
    PIPER_BIN=/opt/piper/piper \
    PIPER_VOICE=/app/voices/en_US-libritts_r-medium.onnx

# Command to run the application
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
