# RO-ED AI Agent

Agentic document intelligence system for extracting structured data from Myanmar import customs declaration PDFs.

Built by **City AI Team**

---

## Quick Install (5 minutes)

### What You Need

- Docker Desktop ([download](https://www.docker.com/products/docker-desktop/))
- OpenRouter API Key ([get one free](https://openrouter.ai/keys))

### Step 1: Download the project

```bash
# Clone the repository
git clone <repo-url> RO-ED-Lang
cd RO-ED-Lang
```

Or if you received a ZIP file:
```bash
unzip RO-ED-Lang.zip
cd RO-ED-Lang
```

### Step 2: Create the API key file

The application needs an OpenRouter API key to call AI models. Create a `.env` file:

```bash
# Copy the template
cp backend/.env.example backend/.env
```

Now open `backend/.env` in any text editor and replace the placeholder with your real key:

```bash
# Open with nano (Linux/macOS)
nano backend/.env

# Or open with TextEdit (macOS)
open -e backend/.env

# Or open with notepad (Windows)
notepad backend\.env
```

The file should look like this (one line):

```
OPENROUTER_API_KEY=sk-or-v1-your-actual-api-key-here
```

Save and close the file.

**Where to get the key:**
1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up / Log in
3. Go to [openrouter.ai/keys](https://openrouter.ai/keys)
4. Click "Create Key"
5. Copy the key (starts with `sk-or-v1-`)
6. Paste it in `backend/.env`

### Step 3: Start the application

```bash
# macOS / Linux
./start-docker.sh

# Windows (PowerShell)
docker-compose up -d --build
```

First run takes 3-5 minutes (downloads Python, installs dependencies). After that it starts in seconds.

### Step 4: Open the UI

```
http://localhost:8080
```

That's it. Upload a PDF and click "Run Job".

---

## File Structure

```
RO-ED-Lang/
|
|-- backend/
|   |-- .env.example          <-- TEMPLATE: copy this to .env
|   |-- .env                  <-- YOUR API KEY (create from .env.example)
|   |-- streamlit_app.py      <-- Web UI
|   |-- config.py             <-- Settings (models, thresholds)
|   |-- database.py           <-- SQLite database operations
|   |-- Dockerfile            <-- Container image definition
|   |-- requirements.txt      <-- Python packages
|   |
|   |-- step1_analyze_metadata.py
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
|       |-- uploads/           <-- Uploaded PDFs
|       |-- results/           <-- Extraction outputs
|       |-- extraction_history.db  <-- Job database
|
|-- docker-compose.yml         <-- Container config
|-- start-docker.sh            <-- One-command startup
|-- .gitignore                 <-- Protects .env from git
```

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

# Reset everything (delete all data)
docker-compose down
rm -rf backend/data/uploads/* backend/data/results/*
rm -f backend/data/extraction_history.db
docker-compose up -d --build
```

---

## Changing the Port

By default the app runs on port `8080`. To change it, edit `docker-compose.yml`:

```yaml
ports:
  - "3000:8080"    # Change 3000 to your desired port
```

Then access at `http://localhost:3000`.

---

## Changing the AI Model

By default the app uses `anthropic/claude-3-haiku` via OpenRouter. To use a different model, edit `backend/config.py`:

```python
OCR_MODEL = "anthropic/claude-3-haiku"          # For OCR
EXTRACTION_MODEL = "anthropic/claude-3-haiku"    # For data extraction
REVIEW_MODEL = "anthropic/claude-3-haiku"        # For self-review
```

Available models on OpenRouter: [openrouter.ai/models](https://openrouter.ai/models)

Then rebuild: `docker-compose up -d --build`

---

## Deploy on a Remote Server

### Linux Server (Ubuntu/Debian)

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and log back in

# 2. Install Docker Compose
sudo apt install docker-compose-plugin

# 3. Upload project to server
scp -r RO-ED-Lang/ user@server-ip:/home/user/

# 4. SSH into server
ssh user@server-ip
cd RO-ED-Lang

# 5. Create .env with your API key
cp backend/.env.example backend/.env
nano backend/.env
# Paste your key: OPENROUTER_API_KEY=sk-or-v1-...

# 6. Start
docker compose up -d --build

# 7. Access
# http://server-ip:8080
```

### Allow access from other machines on the network

The app listens on `0.0.0.0:8080` by default, so any machine on the same network can access it at:

```
http://<server-ip>:8080
```

If you have a firewall, open port 8080:
```bash
# Ubuntu/Debian
sudo ufw allow 8080

# CentOS/RHEL
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

### Run with HTTPS (optional)

For HTTPS, put nginx in front:

```bash
# Install nginx
sudo apt install nginx

# Create config
sudo nano /etc/nginx/sites-available/ro-ed-lang
```

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

```bash
sudo ln -s /etc/nginx/sites-available/ro-ed-lang /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## Troubleshooting

### "Docker is not running"

- macOS: Open Docker Desktop app from Applications
- Linux: `sudo systemctl start docker`
- Windows: Open Docker Desktop from Start Menu

### "API key not set"

Check your `.env` file:
```bash
cat backend/.env
```

Should show:
```
OPENROUTER_API_KEY=sk-or-v1-actual-key-here
```

NOT:
```
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key-here    <-- this is the placeholder
```

### "Port 8080 already in use"

```bash
# Find what's using it
lsof -ti:8080

# Kill it
kill $(lsof -ti:8080)

# Or use a different port in docker-compose.yml
```

### "Container won't start"

```bash
# Check logs for errors
docker-compose logs app

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### "Extraction takes too long" or "API timeout"

Edit `backend/config.py`:
```python
API_TIMEOUT = 300    # increase from 180 to 300 seconds
```

Then rebuild: `docker-compose up -d --build`

### "OCR quality is poor"

Edit `backend/config.py`:
```python
OCR_RESOLUTION = 4           # increase from 3
OCR_HIRES_RESOLUTION = 6     # increase from 5
```

Then rebuild: `docker-compose up -d --build`

### Reset all data

```bash
docker-compose down
rm -rf backend/data/uploads/* backend/data/results/*
rm -f backend/data/extraction_history.db
docker-compose up -d --build
```

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

## Pipeline (9 Steps)

```
Step 1: Classify pages (TEXT vs IMAGE)
Step 2: Extract text from text pages (PyMuPDF, no cost)
Step 3: OCR image pages (parallel, retry, adaptive resolution)
Step 4: AI structured extraction (with confidence scoring)
Step 5: Self-review agent (auto-corrects errors)
Step 6: Cross-validate (items + declaration rules)
Step 7: Decision gate (accept / fix fields / retry / escalate)
Step 8: Accuracy matrix
Step 9: Generate Excel report
```

### Cost per PDF: ~$0.012

---

## Security Notes

- The `.env` file contains your API key and is NOT committed to git (protected by `.gitignore`)
- Never share your `.env` file or commit it to a repository
- If your key is compromised, regenerate it at [openrouter.ai/keys](https://openrouter.ai/keys)
- The application stores data locally in SQLite — no external database required
- All processing happens between your server and OpenRouter API

---

Created by **City AI Team**
