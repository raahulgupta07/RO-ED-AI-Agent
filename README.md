# RO-ED AI Agent

Agentic document intelligence system for extracting structured data from Myanmar import customs declaration PDFs.

Built by **City AI Team**

---

## Features

- **10-step agentic pipeline** with self-review, decision gate, and retry logic
- **Dual format extraction** — Product Items (6 fields) + Customs Declaration (16 fields)
- **Document Search** — Full-text search (FTS5) across all extracted page content
- **Interactive charts** — Plotly gauge, bar, timeline, treemap visualizations
- **User management** — Admin/user roles, bcrypt auth, activity logging
- **Persistent sessions** — stay logged in across browser refresh, with timeout
- **Per-user isolation** — users see only their own jobs and data
- **Global duplicate detection** — same PDF can't be processed twice across all users
- **Job ownership tracking** — every job shows who created/ran it
- **Cost efficient** — ~$0.012 per PDF using Claude 3 Haiku via OpenRouter

---

## Quick Install (5 minutes)

### What You Need

- Docker Desktop ([download](https://www.docker.com/products/docker-desktop/))
- OpenRouter API Key ([get one free](https://openrouter.ai/keys))

### Step 1: Download the project

```bash
git clone <repo-url> RO-ED-Lang
cd RO-ED-Lang
```

### Step 2: Create the API key file

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and replace the placeholder with your real key:

```
OPENROUTER_API_KEY=sk-or-v1-your-actual-api-key-here
```

### Step 3: Start the application

```bash
# macOS / Linux
./start-docker.sh

# Windows (PowerShell)
docker-compose up -d --build
```

First run takes 3-5 minutes (downloads Python, installs dependencies). After that it starts in seconds.

### Step 4: Login

Open `http://localhost:8080`

Default admin credentials: `admin` / `admin123`

**Change the admin password immediately after first login** via User Management tab.

---

## File Structure

```
RO-ED-Lang/
|
|-- backend/
|   |-- .env.example            <-- TEMPLATE: copy to .env
|   |-- .env                    <-- YOUR API KEY (not in git)
|   |-- streamlit_app.py        <-- Web UI (6 tabs, Plotly charts, persistent auth)
|   |-- config.py               <-- Settings (models, thresholds)
|   |-- database.py             <-- SQLite + WAL + bcrypt + FTS5 + parameterized queries
|   |-- Dockerfile              <-- Non-root user, production flags
|   |-- requirements.txt
|   |
|   |-- step1_analyze_metadata.py
|   |-- step1b_filter_agent.py
|   |-- step2_extract_text_pages.py
|   |-- step3_ocr_image_pages.py
|   |-- step4_claude_structured_extraction.py
|   |-- step4b_self_review.py
|   |-- step5_cross_validate.py
|   |-- step6_accuracy_matrix.py
|   |-- step7_create_final_excel.py
|   |-- agent_decision_gate.py
|   |-- run_complete_pipeline.py
|   |
|   |-- data/
|       |-- uploads/
|       |-- results/
|       |-- extraction_history.db
|
|-- docker-compose.yml           <-- Resource limits, named volume
|-- start-docker.sh
|-- .gitignore
```

---

## UI Tabs

| Tab | Description | Access |
|-----|-------------|--------|
| **Agent** | Upload PDF, run extraction, view results with Plotly charts, shows "By: user" badge | All users |
| **History** | Job history with timeline + accuracy charts, filters, details. Admin sees "User" column | All users (own jobs) / Admin (all) |
| **Product Items** | Consolidated items table across all jobs | All users (own jobs) / Admin (all) |
| **Declaration Data** | Consolidated declarations across all jobs | All users (own jobs) / Admin (all) |
| **Document Search** | Full-text search across page content, treemap visualization | All users (own docs) / Admin (all) |
| **User Management** | Create/edit/delete users, activity log | Admin only |

---

## Pipeline (10 Steps)

```
Step 1:  Scout Agent — Classify pages (TEXT vs IMAGE)
Step 2:  Filter Agent — Skip irrelevant pages (photos, stamps)
Step 3:  Reader Agent — Extract text from text pages (free)
Step 4:  Vision Agent — OCR image pages (parallel, retry, adaptive resolution)
Step 5:  Extractor Agent — AI structured extraction with confidence scores
Step 6:  Reviewer Agent — Self-review with document images
Step 7:  Validator Agent — Cross-validate against business rules
Step 8:  Commander Agent — Decision gate (accept/fix/retry/escalate)
Step 9:  Auditor Agent — Field-level accuracy matrix
Step 10: Reporter Agent — Generate 2-sheet Excel report + save page content to DB
```

### Cost per PDF: ~$0.012

---

## What It Extracts

### Format 1: Product Items (6 fields per item)

| Field | Example |
|-------|---------|
| Item name | UHT Whipping Cream 1L (BRAND: ANCHOR) (C/O: NEW ZEALAND) |
| Customs duty rate | 0.15 |
| Quantity + Unit | 16200 KG |
| Invoice unit price + Currency | 69.1358 THB |
| Commercial tax % | 0.05 |
| Exchange rate + Currency | THB 65.0025 |

### Format 2: Customs Declaration (16 fields)

| Category | Fields |
|----------|--------|
| Identity | Declaration No, Date, Importer, Consignor |
| Invoice | Invoice Number, Price + Currency, Exchange Rate |
| Financial | Total Customs Value, Customs Duty, Commercial Tax, Income Tax, Security Fee, MACCS Fee, Exemption |

---

## User Management

### Roles

| Role | Can Do |
|------|--------|
| **admin** | All tabs + User Management + Activity Log + see all users' jobs + reprocess any PDF |
| **user** | Agent + History + Product Items + Declaration Data + Document Search (own data only) |

### Duplicate Detection

- PDF hash (SHA256) is checked **globally across all users**
- If the same PDF was already processed by ANY user:
  - Shows who processed it and when
  - "View Results" loads existing results
  - Only the **original user** or an **admin** can click "Reprocess Anyway"
  - Other users see a disabled button

### Security

- Passwords hashed with **bcrypt** (salted)
- Sessions persist across browser refresh (validated against DB on restore)
- Session timeout: **1 hour** (unless "Remember me" checked)
- Auth restore verifies user still exists and is active before granting access
- Activity log tracks all logins, job runs, deletions, user changes
- Container runs as **non-root user** (UID 1000)
- API key validated at startup
- All SQL queries use parameterized `?` placeholders

---

## Common Commands

```bash
# Start the application
./start-docker.sh

# Stop the application
docker-compose down

# Restart after code changes
docker-compose up -d --build

# View live logs
docker-compose logs -f app

# Check if running
docker-compose ps

# Open a shell inside the container
docker-compose exec app /bin/bash

# Reset everything (delete all data including auth)
docker-compose down -v
docker-compose up -d --build
```

---

## Configuration

### Change the Port

Edit `docker-compose.yml`:
```yaml
ports:
  - "3000:8080"    # Change 3000 to your desired port
```

### Change the AI Model

Edit `backend/config.py`:
```python
OCR_MODEL = "anthropic/claude-3-haiku"
EXTRACTION_MODEL = "anthropic/claude-3-haiku"
REVIEW_MODEL = "anthropic/claude-3-haiku"
```

Available models: [openrouter.ai/models](https://openrouter.ai/models)

### Change Default Admin Password

Set environment variable before first run:
```bash
ADMIN_DEFAULT_PASSWORD=MySecurePassword123 docker-compose up -d --build
```

Or change it after login via User Management tab.

### Change Session Timeout

Edit `SESSION_TIMEOUT` in `backend/streamlit_app.py` (default: 3600 seconds = 1 hour).

---

## Deploy on a Remote Server

### Linux Server (Ubuntu/Debian)

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 2. Install Docker Compose
sudo apt install docker-compose-plugin

# 3. Upload project
scp -r RO-ED-Lang/ user@server-ip:/home/user/

# 4. SSH and start
ssh user@server-ip
cd RO-ED-Lang
cp backend/.env.example backend/.env
nano backend/.env  # paste your API key
docker compose up -d --build

# 5. Access
# http://server-ip:8080
```

### HTTPS (Production)

Put nginx in front with TLS:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

---

## Troubleshooting

### "Docker is not running"
- macOS: Open Docker Desktop from Applications
- Linux: `sudo systemctl start docker`

### "API key not set"
Check `backend/.env` — should contain your actual key, not the placeholder.

### "Port 8080 already in use"
```bash
kill $(lsof -ti:8080)
# Or use a different port in docker-compose.yml
```

### "Container won't start"
```bash
docker-compose logs app        # Check for errors
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### "Logged out after refresh"
This should no longer happen. Sessions persist via disk file. If it does:
- Check that `data/results/` directory is writable
- Check Docker volume mount is correct

### Reset all data
```bash
docker-compose down -v
docker-compose up -d --build
```

---

## Security Notes

- `.env` file is **not committed** to git (protected by `.gitignore`)
- Never share your `.env` file
- Change default admin password immediately after first login
- Container runs as non-root user (UID 1000)
- All passwords hashed with bcrypt (salted)
- SQLite database uses WAL mode for safe concurrent access
- Auth sessions validated against DB on every restore (checks user still active)
- All SQL queries use parameterized placeholders (no SQL injection)
- If deploying publicly, use HTTPS via nginx reverse proxy

---

Created by **City AI Team**
