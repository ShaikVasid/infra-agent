# ── Stage 1: base image ───────────────────────────────────────────────────────
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed by some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Stage 2: install Python dependencies ─────────────────────────────────────
# Copy requirements first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 3: copy application code ───────────────────────────────────────────
COPY agent/ ./agent/
COPY ui/ ./ui/
COPY main.py .

# ── Stage 4: Streamlit configuration ─────────────────────────────────────────
# Tell Streamlit not to open a browser and to listen on all interfaces
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Expose the Streamlit port
EXPOSE 8501

# Health check — confirms the UI is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ── Run the Streamlit UI ──────────────────────────────────────────────────────
CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
