# CLAUDE.md — Project Guide for AI Assistants

## What This Project Is

RO-ED AI Agent — document intelligence system that extracts structured data from import/export PDF documents. Master + Column Agent architecture with LLM verification and self-learning. Built by City AI Team — City Holdings Myanmar.

## Tech Stack

- **Frontend:** SvelteKit 5 (Svelte 5 runes) + TailwindCSS 4.2
- **Backend:** FastAPI 0.115 + Uvicorn (Python 3.12)
- **Database:** SQLite with WAL mode + 30s busy_timeout, 25+ tables
- **AI Models:** OpenRouter API (per-step model config)
  - Vision + Assembler: Google Gemini 3 Flash Preview (page extraction + table building)
  - Verifier: Anthropic Claude Sonnet 4.6 (cross-checks against images)
- **Auth:** Dual-mode — Local JWT (HS256) + Keycloak OIDC (RS256 via PKCE)
- **Container:** Docker (single service, 4GB RAM, non-root user)
- **PDF Processing:** PyMuPDF (fitz) at 300 DPI + Pillow enhancement. NO Tesseract.

## Project Structure

```
RO-ED-Lang/
├── CLAUDE.md / README.md
├── Dockerfile / docker-compose.yml
├── frontend/
│   └── src/
│       ├── lib/
│       │   ├── api.ts                     # API client (handles redirect + auth)
│       │   ├── colors.ts                  # Theme + dynamic page type colors
│       │   └── components/
│       │       ├── ResultAccordion.svelte  # THE main component — tables, PDF, search, map, log
│       │       ├── PipelineVisualizer.svelte # Flow diagram (step boxes with arrows)
│       │       ├── AgentTerminal.svelte    # CLI-style streaming log
│       │       ├── PageDetail.svelte       # Per-page image + extracted data
│       │       └── Header.svelte           # Navigation
│       └── routes/
│           ├── agent/        # Upload + extract + results (persisted via localStorage)
│           ├── history/      # Job list + detail (uses ResultAccordion)
│           ├── review/       # Confidence-based queue (≥95% auto, <80% escalate)
│           ├── items/        # All items across jobs
│           ├── declarations/ # All declarations across jobs
│           ├── costs/        # Cost tracking + charts
│           ├── settings/     # Users + Auth + Groups
│           └── login/
└── backend/
    ├── main.py              # FastAPI app (v3.0.0, CORS *, redirect handling)
    ├── config.py            # Models: VISION_MODEL, ASSEMBLER_MODEL, VERIFIER_MODEL
    ├── auth.py / database.py / schemas.py / middleware.py
    ├── routes/
    │   ├── auth.py          # Login, JWT, Keycloak
    │   ├── jobs.py          # Upload (10 files max, 50MB each), details, Excel, annotated PDF
    │   ├── ws.py            # WebSocket — real-time pipeline streaming
    │   ├── corrections.py   # User corrections → few-shot learning
    │   ├── data.py / users.py / settings.py / groups.py
    ├── pipeline/            # THE extraction pipeline
    │   ├── splitter.py      # PDF → 300 DPI HD images (PyMuPDF + Pillow)
    │   ├── vision.py        # Per-page agents (parallel, semaphore=16) + QA gate
    │   ├── assembler.py     # Master + Column Agents:
    │   │                      Declaration Master (16 column agents, json_schema)
    │   │                      Items Master (9 column agents, json_schema)
    │   │                      QA after each + cross-validation
    │   │                      Token-optimized (dedup fields, no metadata)
    │   ├── verifier.py      # Claude Sonnet cross-checks against page images
    │   └── pipeline.py      # Orchestrator (memory cleanup after verifier)
    ├── v2/                  # Shared utilities
    │   ├── confidence.py    # Per-field confidence scoring
    │   ├── step5_report.py  # Save results to DB (per-job files)
    │   └── step4_validate.py
    └── agents/
        └── advanced.py      # Myanmar language, PDF annotation
```

## Pipeline Architecture

```
PDF Upload
  → Step 1:  SPLITTER          — PDF → HD images (300 DPI)
  → Step 2:  VISION AGENTS     — Per-page (gemini-3-flash, parallel, 8 workers)
  → Step 3:  VISION QA         — Re-run bad pages only
  → Step 4:  DECLARATION AGENT — 16 column agents (json_schema enforced)
  → Step 5:  DECLARATION QA    — Re-run missing fields only
  → Step 6:  ITEMS AGENT       — 9 column agents (json_schema enforced)
  → Step 7:  ITEMS QA          — Re-run missing fields only
  → Step 8:  CROSS-VALIDATION  — Items sum = declaration total
  → Step 9:  VERIFIER          — Claude Sonnet checks against page images
  → Save to DB + Excel
```

## Models

| Step | Model | Cost |
|------|-------|------|
| Vision (per page) | google/gemini-3-flash-preview | ~$0.002/page |
| Declaration + Items + QA | google/gemini-3-flash-preview | ~$0.02 |
| Verifier | anthropic/claude-sonnet-4-6 | ~$0.12 |
| **Total** | | **~$0.14-0.18/PDF** |

## Key Design Principles

- **Zero hardcoded values** — no field names, currencies, tax codes in code
- **Zero calculations** — every value read directly from document
- **json_schema enforced** — guarantees valid JSON, all required fields present
- **Token optimized** — deduplicated fields, no metadata/visual/entities sent to assembler
- **Correction Memory** — user corrections feed back as few-shot examples
- **Per-job isolation** — each job gets own files, own cost tracker, no global state
- **Memory cleanup** — image data freed after verifier step

## Concurrency (10 users)

- SQLite WAL mode + 30s busy_timeout
- API semaphore: max 16 simultaneous OpenRouter calls
- Per-job file isolation (no overwrites)
- Docker: 4GB RAM, 2 CPUs
- Upload: max 10 files/batch, 50MB/file
- Uvicorn: concurrency limit 20, keep-alive 300s

## Duplicate Detection

Upload API hashes PDF (SHA256), checks DB. User sees: VIEW RESULTS (free) | RE-PROCESS (double confirmation) | CANCEL.

## UI Architecture

ResultAccordion is THE main component (agent + history):
- Tabs: RESULTS | PDF (ANNOTATED) | PIPELINE LOG
- RESULTS: Pipeline Visualizer → KPIs → Confidence → Insights → Items table → Declaration table → Corrections Log → Document Summary → Field Search → Document Map (expandable)

## Production Deployment

```bash
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
# Set OPENROUTER_API_KEY in backend/.env
docker-compose up -d --build
```

## Don't

- Don't use Tesseract
- Don't add calculations to prompts
- Don't hardcode field names, currencies, or patterns
- Don't commit `backend/.env`
- Don't use `sqlite3.connect()` — use `database._connect()`
- Don't use bare `except:` — use `except Exception:`
- Don't mutate global state
- Don't skip pages (data could be anywhere)
- Don't use `json_object` mode (9x slower than `json_schema`)
- Don't use `res.json()` in `api.ts` — use `res.text()` + `JSON.parse()` (see troubleshooting)
- Don't use `{@const}` and reference it outside its block scope in Svelte
- Don't mutate `$state` array entries in-place for view transitions — replace with new object

## Known Issues & Troubleshooting

### 1. `res.json()` hangs in browser (fetch returns 200 but body never arrives)

**Symptom:** Page shows "LOADING..." forever. Server logs show `200 OK`. curl works fine.
**Root cause:** Starlette's SPA middleware wraps API responses in a streaming proxy. In some browsers (confirmed Brave), `res.json()` hangs reading the response body stream even though headers arrive.
**Fix:** In `api.ts`, always use `res.text()` + `JSON.parse()` instead of `res.json()`. This reads the body as a complete string first (more reliable), then parses.
**How to diagnose:** Add `debugMsg` state + visible output showing fetch progress:
```javascript
debugMsg = 'calling fetch...';
const res = await fetch(url, opts);
debugMsg = `fetch done: ${res.status}`; // If stuck here → res.json() is the problem
const text = await res.text();
debugMsg = `text: ${text.length} chars`;
```

### 2. Svelte 5 `$derived` doesn't re-render after `$state` array mutation

**Symptom:** Queue shows "DONE" but pipeline view stays visible. Counter shows wrong number.
**Root cause:** `$derived(queue[selectedIndex])` returns the same object reference even after mutating its properties. Svelte 5 skips re-render if the derived value reference hasn't changed.
**Fix:** Replace the array entry with a new object instead of mutating:
```javascript
// BAD: entry.status = 'done'; queue = [...queue];
// GOOD: queue[idx] = { ...entry, status: 'done' }; queue = [...queue];
```
**Alternative:** Use explicit `$state` for view mode (`viewMode = 'results'`) instead of deriving from array entries. Simple strings always trigger re-render.

### 3. `{@const}` scoping in Svelte 5

**Symptom:** `ReferenceError: <variable> is not defined` in browser console.
**Root cause:** `{@const}` is scoped to its enclosing `{#if}`, `{#each}`, or `{#snippet}` block. Using it outside that block causes a runtime crash.
**Fix:** Either move the `{@const}` into the correct block, inline the expression, or use a `$derived` at the component script level.

### 4. WebSocket data delivery vs HTTP fetch

**Symptom:** After pipeline completes, results don't load (even though API works).
**Root cause:** The separate HTTP `getJob()` call after pipeline completion hits issue #1.
**Fix:** Send full `job_data` inline in the WebSocket `file_complete` message from `ws.py`. The frontend receives results directly — no HTTP call needed. Fallback to HTTP `getJob()` only if `msg.job_data` is null.

### 5. FastAPI trailing slash redirects (307)

**Symptom:** 401 Unauthorized on some API calls. Works in curl but not browser.
**Root cause:** FastAPI routes with trailing slash (`/users/`) redirect requests without slash (`/users`) with 307. Browser strips `Authorization` header on redirect.
**Fix:** Match frontend API paths exactly to backend route definitions (include trailing slash where defined).

## Debugging Checklist

When the UI shows "LOADING..." but server logs show 200:

1. **Check browser console** for JavaScript errors (ReferenceError, TypeError)
2. **Add debug state** to the loading template to show fetch progress
3. **Check `api.ts`** — ensure using `res.text()` + `JSON.parse()`, NOT `res.json()`
4. **Check Svelte reactivity** — are you mutating objects in-place? Replace with spread.
5. **Check `{@const}` scope** — is it used outside its block?
6. **Check WebSocket** — is `job_data` being sent and received?
7. **Test with curl** — if curl works but browser doesn't, it's a body streaming issue
