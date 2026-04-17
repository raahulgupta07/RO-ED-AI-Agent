# RO-ED AI Agent

Document intelligence system that extracts structured data from import/export PDF documents using AI vision + Master Agent architecture with self-learning.

Built by **City AI Team** — City Holdings Myanmar

---

## How It Works

```
PDF → HD Images → Vision AI per page → QA → Master Agents → QA → Verifier → Results
```

9 steps. No Tesseract. No hardcoding. Zero calculations. Every value read directly from the document.

---

## Features

- **Master + Column Agent architecture** — Declaration (16 agents), Items (9 agents per product)
- **Claude Sonnet verification** — Premium model cross-checks every value against source page images
- **json_schema enforced** — Guaranteed valid JSON output, all fields present, zero parse errors
- **Token optimized** — Deduplicated fields, no metadata sent to assembler (~11% savings)
- **Self-learning** — User corrections feed back as few-shot examples
- **Vision QA** — Re-runs low-quality pages automatically
- **Table QA** — Re-runs missing fields until all filled
- **Cross-validation** — Items sum must match declaration total
- **Pipeline Visualizer** — Real-time flow diagram showing each step's progress
- **Confidence indicators** — Green/yellow/red dots on every table and page
- **Annotated PDF** — Highlights where values were found on original PDF
- **Excel export** — Items + Declaration as separate sheets
- **Field search** — Search any value across all pages with copy buttons
- **Document map** — Clickable page grid with expand to see image + data
- **Duplicate detection** — VIEW RESULTS (free) or RE-PROCESS (double confirmation)
- **Persistent sessions** — Results stay when navigating away (localStorage)
- **10 concurrent users** — SQLite WAL + API semaphore + per-job isolation
- **Review queue** — Auto-approve (≥95%) / Needs review (80-95%) / Escalate (<80%)
- **REST API** — `POST /api/extract` for headless integration
- **Batch processing** — Multiple PDFs with real-time streaming terminal
- **100% accuracy** — Tested on 12 verified customs PDFs, zero corrections needed
- **Cost: ~$0.14-0.18 per PDF**

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | SvelteKit 5 + TailwindCSS 4.2 |
| Backend | FastAPI 0.115 + Uvicorn (Python 3.12) |
| Database | SQLite (WAL mode, 30s busy_timeout) |
| Vision + Assembler | Google Gemini 3 Flash Preview via OpenRouter |
| Verifier | Anthropic Claude Sonnet 4.6 via OpenRouter |
| PDF | PyMuPDF at 300 DPI + Pillow (NO Tesseract) |
| Auth | Local JWT + Keycloak OIDC |
| Container | Docker (4GB RAM, 2 CPUs) |

---

## Quick Install

```bash
git clone <repo-url> RO-ED-Lang && cd RO-ED-Lang
cp backend/.env.example backend/.env  # Add OPENROUTER_API_KEY
cd frontend && npm install && npm run build && cd ..
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
docker-compose up -d --build
```

Open **http://localhost:9000** — Login: `admin` / `admin123`

### Environment Variables

| Variable | Required | Where | Description |
|----------|----------|-------|-------------|
| `OPENROUTER_API_KEY` | Yes | `backend/.env` | API key for AI models |
| `JWT_SECRET_KEY` | Yes | Environment | Secret for JWT token signing |
| `KEYCLOAK_REALM_URL` | No | Settings page | Keycloak SSO (optional) |

---

## Pipeline Architecture

```
Step 1:  SPLITTER           — PDF → HD images (300 DPI)
Step 2:  VISION AGENTS      — Per-page extraction (parallel, 8 workers, semaphore=16)
Step 3:  VISION QA          — Re-run bad pages only
Step 4:  DECLARATION AGENT  — 16 column agents (json_schema enforced)
Step 5:  DECLARATION QA     — Re-run missing fields only
Step 6:  ITEMS AGENT        — 9 column agents (json_schema enforced)
Step 7:  ITEMS QA           — Re-run missing fields only
Step 8:  CROSS-VALIDATION   — Items sum = declaration total
Step 9:  VERIFIER           — Claude Sonnet checks against page images
```

### Models

| Step | Model | Role |
|------|-------|------|
| Vision | Gemini 3 Flash | Read each page image → JSON |
| Declaration Agent | Gemini 3 Flash | 16 column agents find declaration fields |
| Items Agent | Gemini 3 Flash | 9 column agents find item fields |
| Verifier | Claude Sonnet 4.6 | Cross-check all values against page images |

---

## Output Tables

### Table 1: Product Items (9 fields per item)

| Field | Description |
|-------|-------------|
| Item Name | Full product description |
| Quantity (1) | Quantity with unit |
| Invoice Unit Price | Price per unit in foreign currency |
| Customs Value (MMK) | Value in local currency |
| Customs Duty Rate | Duty as decimal (0.15 = 15%) |
| Commercial Tax % | Tax as decimal (0.05 = 5%) |
| HS Code | Harmonized system tariff code |
| Origin Country | Country of origin |
| Exchange Rate (1) | Foreign to local currency rate |

### Table 2: Customs Declaration (16 fields)

Declaration No, Date, Importer, Consignor, Invoice Number, Invoice Price, Currency, Currency 2, Exchange Rate, Total Customs Value, Customs Duty, Commercial Tax, Advance Income Tax, Security Fee, MACCS Service Fee, Exemption/Reduction

---

## UI Pages

| Tab | Description |
|-----|-------------|
| **Agent** | Upload PDFs, pipeline visualizer, streaming log, all results |
| **History** | Job list → same results view (ResultAccordion) |
| **Review** | Confidence queue: auto-approve ≥95%, review 80-95%, escalate <80% |
| **Items** | All items across jobs |
| **Declarations** | All declarations across jobs |
| **Costs** | Daily trends, per-PDF costs |
| **Settings** | Users + Auth + Groups |

### Results View (RESULTS | PDF ANNOTATED | PIPELINE LOG)

1. Pipeline Flow Visualizer
2. KPI Cards
3. Field Confidence
4. Document Insights
5. Product Items table
6. Customs Declaration table
7. Corrections Log
8. Document Summary
9. Field Search
10. Document Map (expandable)

---

## CLI Usage

```bash
cd backend && python -m pipeline.pipeline /path/to/document.pdf
```

---

## Performance

| Metric | Value |
|--------|-------|
| Accuracy | 100% (12 PDFs, zero corrections) |
| Cost | $0.14-0.18 per PDF |
| Speed | 60-130s per PDF |
| Max pages tested | 29 pages |
| Max items | 8 per document |
| Concurrent users | 10 |

---

## Troubleshooting

| Issue | Symptom | Fix |
|-------|---------|-----|
| `res.json()` hangs | "LOADING..." forever, server logs 200 OK | Use `res.text()` + `JSON.parse()` in `api.ts` instead of `res.json()` |
| Pipeline view stuck | Job shows DONE but results don't appear | Replace array entry with new object: `queue[i] = {...entry, status: 'done'}` |
| `{@const}` crash | `ReferenceError: X is not defined` in console | `{@const}` is block-scoped — don't reference outside its `{#if}`/`{#each}` |
| 401 on some routes | Works in curl, fails in browser | Match trailing slashes in API paths exactly (`/users/` not `/users`) |
| Results not loading after pipeline | WebSocket completes but no tables shown | Check `ws.py` sends `job_data` in `file_complete` message |

### Debug "LOADING..." Issues

1. Open browser DevTools Console — check for red errors
2. If no errors: add debug state to show fetch progress (see CLAUDE.md)
3. If `fetch done: 200 OK` but stuck: body streaming issue → use `res.text()` + `JSON.parse()`
4. If JavaScript error: fix the referenced variable/scope issue
5. Test API with curl: `curl -s http://localhost:9000/api/jobs/ -H "Authorization: Bearer <token>"`

---

Created by **City AI Team** — City Holdings Myanmar
