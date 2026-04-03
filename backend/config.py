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
                    API_KEY = line.split("=", 1)[1].strip().strip('"')
                    break

# Validate API key at startup
if not API_KEY or API_KEY == "sk-or-v1-your-openrouter-key-here":
    import logging
    logging.warning("OPENROUTER_API_KEY not set or still placeholder — API calls will fail")

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================
# Available models via OpenRouter (all support vision/image input):
#
# Budget tier (~$0.01-0.02 per PDF):
#   "anthropic/claude-3-haiku"           — $0.25/$1.25 per M tokens (struggles with comma-separated numbers)
#   "google/gemini-2.5-flash"            — $0.30/$2.50 per M tokens (best value, native Google OCR, handles commas correctly)
#   "google/gemini-3-flash-preview"      — $0.50/$3.00 per M tokens (latest, enhanced data extraction)
#
# Mid tier (~$0.05-0.10 per PDF):
#   "google/gemini-2.5-pro"              — $1.25/$10.00 per M tokens (highest accuracy, 1M context)
#   "google/gemini-3-pro-preview"        — frontier reasoning, 1M context
#
# Premium tier (~$0.15+ per PDF):
#   "anthropic/claude-3.5-sonnet"        — $3.00/$15.00 per M tokens (best for complex layouts)
#   "anthropic/claude-sonnet-4-6"        — latest Claude, strongest vision

OCR_MODEL = "google/gemini-3.1-flash-lite-preview"
EXTRACTION_MODEL = "google/gemini-3.1-flash-lite-preview"

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
REVIEW_MODEL = "google/gemini-3.1-flash-lite-preview"
