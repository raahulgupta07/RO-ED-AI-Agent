# RO-ED AI Agent — Master + Column Agent Architecture
# Python 3.12 + FastAPI + Pure Vision AI (NO Tesseract)
# Build context: project root (RO-ED-Lang/)

FROM python:3.12-slim

WORKDIR /app

# System deps (mupdf for PDF rendering only — NO OCR)
RUN apt-get update && apt-get install -y \
    gcc g++ libmupdf-dev mupdf-tools curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps (cached layer)
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --timeout 300 -r requirements.txt

# Backend code — root files
COPY backend/*.py /app/

# Backend code — pipeline
COPY backend/pipeline/ /app/pipeline/

# Backend code — shared utilities
COPY backend/v2/ /app/v2/

# Backend code — platform features
COPY backend/agents/ /app/agents/

# Backend code — routes
COPY backend/routes/ /app/routes/

# Pre-built frontend (built on host via: cd frontend && npm run build)
COPY frontend/build/ /app/frontend-build/

# Ensure all files are readable
RUN chmod -R a+r /app/

# Non-root user
RUN useradd -m -u 1000 appuser

# Data directories
RUN mkdir -p /app/data/results /app/data/uploads /app/data/jobs \
    && chown -R appuser:appuser /app

ENV PYTHONUNBUFFERED=1
EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:9000/api/health || exit 1

USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000", "--limit-concurrency", "20", "--timeout-keep-alive", "300"]
