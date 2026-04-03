# RO-ED AI Agent
# Python 3.9 + PDF processing + Streamlit UI

FROM python:3.9-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ libmupdf-dev mupdf-tools curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 appuser

# Application code
COPY *.py ./

# Data directories + fix permissions on all app files
RUN mkdir -p /app/data/results /app/data/uploads /app/data/jobs \
    && chown -R appuser:appuser /app

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/_stcore/health || exit 1

USER appuser

CMD ["streamlit", "run", "streamlit_app.py", \
     "--server.port=8080", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.maxUploadSize=50", \
     "--server.runOnSave=false", \
     "--client.showErrorDetails=false", \
     "--client.toolbarMode=minimal", \
     "--logger.level=info"]
