# CLAUDE.md — Project Guide for AI Assistants

## What This Project Is

RO-ED AI Agent — agentic document intelligence system that extracts structured data from Myanmar import customs PDFs. Built by City AI Team.

## Tech Stack

- **UI:** Streamlit 1.31 + streamlit-shadcn-ui 0.1.19 + Plotly 5.18
- **Backend:** Python 3.9
- **Database:** SQLite with WAL mode, FTS5 full-text search (auto-created at backend/data/extraction_history.db)
- **AI:** OpenRouter API (anthropic/claude-3-haiku for OCR + extraction + review)
- **Auth:** bcrypt password hashing, role-based access (admin/user), persistent sessions, session timeout
- **Container:** Docker (single service, non-root user, resource limits)
- **PDF Processing:** PyMuPDF (fitz)

## Project Structure

```
RO-ED-Lang/
├── README.md                  # Installation & usage guide
├── CLAUDE.md                  # This file
├── docker-compose.yml         # Single service + named volume + resource limits
├── start-docker.sh            # One-command startup
├── .gitignore                 # Protects .env, data/, logs
├── .dockerignore
└── backend/
    ├── .env.example           # API key template
    ├── .env                   # Real API key (not in git)
    ├── config.py              # All settings (models, thresholds, paths) + API key validation
    ├── database.py            # SQLite ops (WAL, bcrypt auth, FTS5 search, activity logs, parameterized queries)
    ├── streamlit_app.py       # Main UI (~2300 lines, 6 tabs, Plotly charts, persistent auth)
    ├── step1_analyze_metadata.py     # Page classification (TEXT/IMAGE)
    ├── step1b_filter_agent.py        # LLM vision filter (skip photos/stamps)
    ├── step2_extract_text_pages.py   # PyMuPDF text extraction
    ├── step3_ocr_image_pages.py      # Parallel OCR + retry + adaptive res
    ├── step4_claude_structured_extraction.py  # AI extraction + confidence (generic prompt examples)
    ├── step4b_self_review.py         # Self-review agent (with document images)
    ├── step5_cross_validate.py       # Validation (items + declaration)
    ├── step6_accuracy_matrix.py      # Field-level accuracy
    ├── step7_create_final_excel.py   # 2-sheet Excel output
    ├── agent_decision_gate.py        # Decision gate (accept/fix/retry/escalate) with images + confidence
    ├── run_complete_pipeline.py      # CLI runner
    ├── Dockerfile                    # Non-root user, production Streamlit flags
    ├── requirements.txt
    └── data/                         # Auto-created, not in git
        ├── uploads/
        ├── results/
        └── extraction_history.db
```

## Key Architecture Decisions

- **Single container** — no PostgreSQL, no Redis, no frontend server. Just Streamlit.
- **SQLite + WAL mode** — auto-creates on first run, WAL for concurrent reads, FTS5 for document search. All queries use parameterized `?` placeholders (no f-string SQL).
- **OpenRouter** — single API key accesses all models. Only env var the app needs.
- **Agentic pipeline** — 10 steps with self-review (with images), decision gate (with images + confidence), retry logic.
- **Persistent sessions** — auth saved to `data/results/_auth_session.json`, survives browser refresh. Validated against DB on restore (checks user still active).
- **Global duplicate detection** — PDF hash (SHA256) checked across ALL users. If User A processed a PDF, User B cannot re-upload the same file. Only original user or admin can reprocess.
- **User isolation** — jobs, page content, stats scoped to user_id. Admins see all. Each job stores `user_id` + `username`.
- **bcrypt auth** — passwords hashed with bcrypt + salt. Legacy SHA256 auto-migrated on login.
- **Non-root Docker** — container runs as appuser (UID 1000).

## Pipeline Flow

```
PDF → Step 1: Classify pages (TEXT vs IMAGE)
    → Step 1B: Filter Agent (skip photos/stamps via LLM vision)
    → Step 2: Extract text pages (PyMuPDF, free)
    → Step 3: OCR image pages (parallel, retry, adaptive resolution)
    → Step 4: AI extraction (all pages as images + confidence scores)
    → Step 4B: Self-review agent (with document images — auto-corrects decimals, units, formats)
    → Step 5: Cross-validate (items 6 fields + declaration 16 fields)
    → Step 6: Decision gate (uses validation accuracy + confidence scores)
        ├── ≥90% accuracy → ACCEPT
        ├── 60-89% → FIX specific fields via targeted LLM call (with images)
        ├── 30-59% → FULL re-extraction (re-runs Step 4 + 4B, compares against previous accuracy)
        └── <30% → ESCALATE for human review
    → Step 7: Accuracy matrix
    → Step 8: Generate Excel
    → Save page content to DB (for Document Search / RAG)
```

## Database Schema (SQLite + WAL + FTS5)

Tables: `jobs`, `items`, `declarations`, `processing_logs`, `pdf_metadata`, `users`, `activity_logs`, `page_contents`, `page_contents_fts`

Key columns on `jobs`: `user_id`, `username` — links every job to the user who ran it.

Key features:
- `database._connect()` — creates connection with WAL, NORMAL sync, 64MB cache, foreign keys ON, 10s timeout
- `database.init_database()` — auto-creates all tables with migration support (ALTER TABLE for new columns)
- `page_contents_fts` — FTS5 virtual table with porter stemming for full-text search
- All passwords hashed with bcrypt (auto-migrates old SHA256 on login)
- All SQL queries use parameterized `?` placeholders — no f-string SQL construction

## Auth & Roles

- **admin** — sees all users' jobs, user management tab, activity logs, global stats, can reprocess any PDF
- **user** — sees only own jobs, own stats, no user management, cannot reprocess PDFs uploaded by other users
- Default admin: `admin` / `admin123` (change immediately in production)
- Sessions persist across browser refresh via `_auth_session.json` (validated against DB on restore)
- Session timeout: 1 hour (skipped if "Remember me" checked)
- On restore: verifies user still exists and is active in DB before granting access
- Activity log tracks: LOGIN, LOGOUT, RUN_JOB, DELETE_JOB, CREATE_USER, UPDATE_USER, DELETE_USER

## Duplicate Detection

- PDF hash (SHA256) is checked **globally across all users** before processing
- If the same PDF was already processed by ANY user:
  - Shows who processed it and when
  - "View Results" button loads existing results
  - "Reprocess Anyway" only available to original user or admin
  - Regular users see disabled button with message: "Only {user} or admin can reprocess"
- Results header shows "By: {username}" badge so you always know who ran the extraction

## UI Tabs (streamlit_app.py)

1. **Agent** — Upload PDF, run extraction, view results (KPI cards + Plotly gauge/bar charts + tables + PDF preview + "By: user" badge)
2. **History** — Jobs with filters, Plotly timeline + accuracy charts, expandable details. Admin sees "User" column + all jobs. Users see only own jobs.
3. **Product Items** — Consolidated items table across jobs with filters and export (per-user scoped)
4. **Declaration Data** — Consolidated declarations across jobs with filters and export (per-user scoped)
5. **Document Search** — FTS5 search across all page content, Plotly treemap + stacked bar, export CSV (per-user scoped)
6. **User Management** (admin only) — Create/edit/delete users + Activity Log with filters

## Config Reference (backend/config.py)

Required env var: `OPENROUTER_API_KEY`
Optional env var: `ADMIN_DEFAULT_PASSWORD` (defaults to admin123)

Key settings:
- `OCR_MODEL` / `EXTRACTION_MODEL` / `REVIEW_MODEL` — all set to anthropic/claude-3-haiku
- `MAX_RETRIES=3`, `RETRY_BACKOFF_BASE=2` — retry with 2s, 4s, 8s backoff
- `ACCURACY_ACCEPT=90`, `ACCURACY_FIX=60`, `ACCURACY_RETRY=30` — decision gate thresholds
- `CONFIDENCE_THRESHOLD=0.7` — fields below this flagged for review + re-extraction
- `OCR_RESOLUTION=3`, `OCR_HIRES_RESOLUTION=5` — adaptive OCR resolution

## Common Tasks

- **Change AI model:** Edit `config.py` lines 46-48, rebuild container
- **Change port:** Edit `docker-compose.yml` ports section
- **Reset data:** `docker-compose down -v && docker-compose up -d --build`
- **Add new extraction field:** Update prompt in step4, validation in step5, Excel in step7, UI in streamlit_app.py
- **Change session timeout:** Edit `SESSION_TIMEOUT` in streamlit_app.py (default 3600s)
- **Change default admin password:** Set `ADMIN_DEFAULT_PASSWORD` env var before first run

## Known Fixes Applied

- Extraction prompt uses generic placeholders (not real data) to prevent LLM copying example values
- `fix_fields()` and `self_review()` send document images to LLM (not text-only)
- FULL_RETRY compares re-extraction accuracy against previous validation accuracy (not completeness)
- `get_failed_fields()` always receives `extracted_data` for confidence-based field selection
- `pandas.style.map()` used instead of deprecated `applymap()`
- Auth restore validates user still exists and is active in DB before granting session

## Don't

- Don't rename `step4_claude_structured_extraction.py` — imported by name everywhere
- Don't use `ui.select()`, `ui.date_picker()`, `ui.hover_card()`, `ui.progress()` — they crash with Streamlit 1.31 (stylable_container key bug). Use native `st.selectbox`, `st.date_input`, `st.progress` instead.
- Don't commit `backend/.env` — contains real API key
- Don't use `from config import PDF_PATH` — use `config.PDF_PATH` (it's set dynamically)
- Don't put real data in extraction prompt examples — LLM will copy them instead of extracting from document
- Don't use `sqlite3.connect()` directly — use `database._connect()` for WAL mode and proper settings
- Don't use f-strings to build SQL queries — always use `?` parameterized queries
- Don't use `pandas.style.applymap()` — use `.map()` (applymap deprecated in pandas 2.1+)
