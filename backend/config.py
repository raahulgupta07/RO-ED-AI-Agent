#!/usr/bin/env python3
"""
Configuration file for PDF extraction pipeline
Centralized settings for all steps
"""

import os
from pathlib import Path

# ============================================================================
# BASE DIRECTORY
# ============================================================================

BASE_DIR = Path(__file__).parent

# ============================================================================
# PDF CONFIGURATION
# ============================================================================

# Update this path to your PDF file (or dynamically set by Streamlit app)
# For Docker/Streamlit: Leave empty, will be set when file is uploaded
# For CLI: Set to your local PDF path
PDF_PATH = None  # Set dynamically by Streamlit on file upload

# ============================================================================
# API CONFIGURATION
# ============================================================================

# OpenRouter API Key
API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Try to load from .env if not in environment
if not API_KEY:
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith("OPENROUTER_API_KEY"):
                    API_KEY = line.split("=")[1].strip().strip('"')
                    break

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

OCR_MODEL = "anthropic/claude-3-haiku"
EXTRACTION_MODEL = "anthropic/claude-3-haiku"

# ============================================================================
# OUTPUT CONFIGURATION
# ============================================================================

RESULTS_DIR = Path(__file__).parent / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_FOLDER = Path(__file__).parent / "data" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# ============================================================================
# PROCESSING CONFIGURATION
# ============================================================================

# OCR resolution (2-3x recommended)
OCR_RESOLUTION = 3

# Extraction resolution
EXTRACTION_RESOLUTION = 2

# API timeout (seconds)
API_TIMEOUT = 180

# Rate limiting delay (seconds)
RATE_LIMIT_DELAY = 1

# ============================================================================
# AGENTIC PIPELINE CONFIGURATION
# ============================================================================

# Retry settings
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds (2, 4, 8)

# Adaptive OCR: retry at higher resolution if chars extracted < threshold
OCR_MIN_CHARS = 50
OCR_HIRES_RESOLUTION = 5

# Confidence threshold: fields below this are flagged for review
CONFIDENCE_THRESHOLD = 0.7

# Decision gate thresholds
ACCURACY_ACCEPT = 90     # >= 90% → accept as-is
ACCURACY_FIX = 60        # 60-89% → re-extract failed fields
ACCURACY_RETRY = 30      # 30-59% → full re-extraction
# < 30% → escalate to human review

# Max agentic cycles
MAX_FIX_CYCLES = 2       # max field-fix attempts
MAX_FULL_RETRIES = 1     # max full re-extraction attempts

# Self-review model (can be same or different)
REVIEW_MODEL = "anthropic/claude-3-haiku"
