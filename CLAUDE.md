# CLAUDE.md — Project Guide for AI Assistants

## What This Project Is

RO-ED AI Agent — agentic document intelligence system that extracts structured data from Myanmar import customs PDFs. Built by City AI Team.

## Tech Stack

- **UI:** Streamlit 1.31 + streamlit-shadcn-ui 0.1.19
- **Backend:** Python 3.9
- **Database:** SQLite (auto-created at backend/data/extraction_history.db)
- **AI:** OpenRouter API (anthropic/claude-3-haiku for OCR + extraction + review)
- **Container:** Docker (single service)
- **PDF Processing:** PyMuPDF (fitz)

## Project Structure

```
RO-ED-Lang/
├── README.md                  # Installation & usage guide
├── CLAUDE.md                  # This file
├── docker-compose.yml         # Single service container
├── start-docker.sh            # One-command startup
├── .gitignore                 # Protects .env and data/
├── .dockerignore
└── backend/
    ├── .env.example           # API key template
    ├── .env                   # Real API key (not in git)
    ├── config.py              # All settings (models, thresholds, paths)
    ├── database.py            # SQLite ops (init, CRUD, stats)
    ├── streamlit_app.py       # Main UI (~1500 lines, 4 tabs)
    ├── step1_analyze_metadata.py     # Page classification (TEXT/IMAGE)
    ├── step2_extract_text_pages.py   # PyMuPDF text extraction
    ├── step3_ocr_image_pages.py      # Parallel OCR + retry + adaptive res
    ├── step4_claude_structured_extraction.py  # AI extraction + confidence
    ├── step4b_self_review.py         # Self-review agent
    ├── step5_cross_validate.py       # Validation (items + declaration)
    ├── step6_accuracy_matrix.py      # Field-level accuracy
    ├── step7_create_final_excel.py   # 2-sheet Excel output
    ├── agent_decision_gate.py        # Decision gate (accept/fix/retry/escalate)
    ├── run_complete_pipeline.py      # CLI runner
    ├── Dockerfile
    ├── requirements.txt
    └── data/                         # Auto-created, not in git
        ├── uploads/
        ├── results/
        └── extraction_history.db
```

## Key Architecture Decisions

- **Single container** — no PostgreSQL, no Redis, no frontend server. Just Streamlit.
- **SQLite** — auto-creates on first run, no config needed. DB path hardcoded in database.py line 15.
- **OpenRouter** — single API key accesses all models. Only env var the app needs.
- **Agentic pipeline** — 9 steps with self-review, decision gate, retry logic. Not a simple linear flow.
- **Session persistence** — job results saved to `data/results/_last_session.json` so they survive browser refresh.
- **Duplicate detection** — PDF hash (MD5) checked before processing. Same file won't be re-extracted unless user forces it.

## Pipeline Flow

```
PDF → Step 1: Classify pages (TEXT vs IMAGE)
    → Step 2: Extract text pages (PyMuPDF, free)
    → Step 3: OCR image pages (parallel, retry, adaptive resolution)
    → Step 4: AI extraction (confidence scores per field)
    → Step 5: Self-review agent (auto-corrects decimals, units, formats)
    → Step 6: Cross-validate (items 6 fields + declaration 16 fields)
    → Step 7: Decision gate
        ├── ≥90% accuracy → ACCEPT
        ├── 60-89% → FIX specific fields via targeted LLM call
        ├── 30-59% → FULL re-extraction
        └── <30% → ESCALATE for human review
    → Step 8: Accuracy matrix
    → Step 9: Generate Excel
```

## Config Reference (backend/config.py)

Only env var needed: `OPENROUTER_API_KEY`

Key settings:
- `OCR_MODEL` / `EXTRACTION_MODEL` / `REVIEW_MODEL` — all set to anthropic/claude-3-haiku
- `MAX_RETRIES=3`, `RETRY_BACKOFF_BASE=2` — retry with 2s, 4s, 8s backoff
- `ACCURACY_ACCEPT=90`, `ACCURACY_FIX=60`, `ACCURACY_RETRY=30` — decision gate thresholds
- `CONFIDENCE_THRESHOLD=0.7` — fields below this flagged for review
- `OCR_RESOLUTION=3`, `OCR_HIRES_RESOLUTION=5` — adaptive OCR resolution

## Database Schema (SQLite)

Tables: `jobs`, `items`, `declarations`, `processing_logs`, `pdf_metadata`

Key function: `database.init_database()` — auto-creates all tables with migration support (ALTER TABLE for new columns).

## UI Tabs (streamlit_app.py)

1. **Home** — Upload PDF, run extraction, view results (cards + tables + PDF preview + heatmap)
2. **History** — All jobs with filters (date, status, PDF name), expandable details with card view
3. **Product Items** — Consolidated items table across all jobs with filters and export
4. **Declaration Data** — Consolidated declarations across all jobs with filters and export

## Common Tasks

- **Change AI model:** Edit `config.py` lines 46-48, rebuild container
- **Change port:** Edit `docker-compose.yml` ports section
- **Reset data:** Delete `backend/data/` contents, restart container
- **Add new extraction field:** Update prompt in step4, validation in step5, Excel in step7, UI in streamlit_app.py

## Don't

- Don't rename `step4_claude_structured_extraction.py` — imported by name everywhere
- Don't use `ui.select()`, `ui.date_picker()`, `ui.hover_card()`, `ui.progress()` — they crash with Streamlit 1.31 (stylable_container key bug). Use native `st.selectbox`, `st.date_input`, `st.progress` instead.
- Don't commit `backend/.env` — contains real API key
- Don't use `from config import PDF_PATH` — use `config.PDF_PATH` (it's set dynamically)
