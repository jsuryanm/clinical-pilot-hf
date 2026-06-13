# CliniqAI — Setup & Run Instructions

> Complete guide for **Windows (WSL2)** and **macOS** (Intel + Apple Silicon).

---

## Table of Contents

1. [How the application runs](#1-how-the-application-runs)
2. [Prerequisites by operating system](#2-prerequisites-by-operating-system)
   - [Windows — install WSL2 first](#21-windows--install-wsl2-first)
   - [macOS](#22-macos)
3. [Get the code](#3-get-the-code)
4. [Install Python tooling with uv](#4-install-python-tooling-with-uv)
5. [Configure environment variables](#5-configure-environment-variables)
   - [Required — LLM provider](#51-required--llm-provider)
   - [Optional integrations](#52-optional-integrations)
6. [Start infrastructure (Docker)](#6-start-infrastructure-docker)
7. [Apply the database schema](#7-apply-the-database-schema)
8. [Run the application](#8-run-the-application)
   - [Minimal mode (no Celery)](#81-minimal-mode-no-celery)
   - [Full mode (all processes)](#82-full-mode-all-processes)
9. [Verify everything is working](#9-verify-everything-is-working)
10. [Stopping the application](#10-stopping-the-application)
11. [Hugging Face Spaces deployment](#11-hugging-face-spaces-deployment)
12. [Troubleshooting by OS](#12-troubleshooting-by-os)

---

## 1. How the application runs

CliniqAI consists of several cooperating processes. Understanding what each one does prevents confusion when something stops working.

| Process | Command | Port | What it does | Required for |
|---|---|---|---|---|
| PostgreSQL | `make up` | 5432 | Stores appointments, staff, SOAP drafts, audit log | Everything |
| Redis | `make up` | 6379 | Celery task broker + result backend | Scheduled reminders |
| Langfuse | `make up` | 3001 | LLM call observability dashboard | Observability (optional) |
| FastAPI backend | `make api` | 8000 | All agent HTTP endpoints | Everything |
| Gradio UI | `make ui` | 7860 | Doctor / Patient / Nurse tabs | The web interface |
| Celery worker | `make worker` | — | Executes scheduled reminder tasks | T-24h / T-3h / T-2h reminders |
| Celery beat | `make beat` | — | Triggers the 6-hour sweep cron | Post-discharge sweep |

**Minimum to run the demo:** Docker (PostgreSQL + Redis), FastAPI, and Gradio.
The Celery worker and beat are only needed for timed notifications and scheduled sweeps.

---

## 2. Prerequisites by operating system

### 2.1 Windows — install WSL2 first

Native Windows is not supported. All development happens inside WSL2 (Windows Subsystem for Linux). Docker Desktop runs on Windows but mounts into WSL2.

#### Step 1 — Enable WSL2

Open PowerShell **as Administrator** and run:

```powershell
wsl --install
```

This installs WSL2 and Ubuntu by default. If you already have WSL1, upgrade:

```powershell
wsl --set-default-version 2
wsl --install -d Ubuntu-24.04
```

Restart your machine when prompted.

#### Step 2 — Verify WSL2 is running

```powershell
wsl --list --verbose
```

The `VERSION` column must show `2`. If it shows `1`, run:

```powershell
wsl --set-version Ubuntu-24.04 2
```

#### Step 3 — Install Docker Desktop for Windows

Download from: https://www.docker.com/products/docker-desktop

During installation, on the **Configuration** screen, make sure **"Use WSL 2 instead of Hyper-V"** is checked.

After installation:
1. Open Docker Desktop → Settings → Resources → WSL Integration
2. Enable integration for your Ubuntu distribution
3. Click **Apply & Restart**

Verify inside WSL:

```bash
# Open Ubuntu from the Start menu, then:
docker --version
docker compose version
```

Both commands must work inside the WSL terminal. If `docker` is not found inside WSL, go back to Docker Desktop → WSL Integration and re-enable your distro.

#### Step 4 — Install build tools inside WSL

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git curl wget make python3-dev
```

#### Step 5 — Verify Make is available

```bash
make --version
```

If missing: `sudo apt install -y make`

---

### 2.2 macOS

macOS works natively — no virtualization layer needed.

#### Step 1 — Install Xcode Command Line Tools

This provides `git`, `make`, and the C compiler:

```bash
xcode-select --install
```

Click Install in the dialog that appears. This takes a few minutes.

#### Step 2 — Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After installation, follow the instructions in the terminal to add Homebrew to your PATH. For Apple Silicon Macs, this is usually:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

For Intel Macs, Homebrew installs to `/usr/local` which is already on PATH.

Verify:

```bash
brew --version
```

#### Step 3 — Install Docker Desktop for macOS

Download the correct version for your chip:
- **Apple Silicon (M1/M2/M3/M4):** https://docs.docker.com/desktop/install/mac-install/ — choose **Apple Chip**
- **Intel:** same page — choose **Intel Chip**

After installation, open Docker Desktop from Applications and wait for the whale icon in the menu bar to stop animating (means Docker engine is ready).

Verify:

```bash
docker --version
docker compose version
```

---

## 3. Get the code

**Windows users:** Clone inside WSL, not on the Windows filesystem (`/mnt/c/...`). The Windows filesystem is mounted via 9P protocol and causes dramatic slowdowns with Python tooling.

```bash
# Good — inside WSL home directory
cd ~
git clone https://github.com/your-org/clinical-pilot-hf.git
cd clinical-pilot-hf

# Bad — this is slow
# cd /mnt/c/Users/yourname/projects
```

**macOS users:** Clone anywhere in your home directory.

```bash
cd ~/projects   # or wherever you keep code
git clone https://github.com/your-org/clinical-pilot-hf.git
cd clinical-pilot-hf
```

---

## 4. Install Python tooling with uv

`uv` is the package manager used by this project. It is faster than pip and manages Python versions automatically.

### Install uv

**WSL (Ubuntu) and macOS:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation, reload your shell:

```bash
source ~/.bashrc       # WSL / bash users
source ~/.zshrc        # macOS zsh users (default since macOS Catalina)
```

Verify:

```bash
uv --version
```

### Install Python 3.12 and all project dependencies

From the project root directory:

```bash
make install
```

This runs `uv sync` under the hood, which:
1. Downloads Python 3.12 if not present on your machine
2. Creates a virtual environment at `.venv/`
3. Installs all packages from `pyproject.toml`

> **Note on `torch` and `transformers`:** These are large packages (torch alone is ~2 GB). The first `make install` will take several minutes while they download. Subsequent installs are cached.

> **Apple Silicon note:** `torch` ships with Metal (MPS) support on Apple Silicon. No special flags needed — the package auto-detects the chip.

Verify the virtual environment was created:

```bash
ls .venv/
```

You should see `bin/`, `lib/`, and `pyvenv.cfg`.

---

## 5. Configure environment variables

Copy the template to a local file that is gitignored:

```bash
cp .env.example .env.local
```

Now edit `.env.local`. The sections below explain every variable.

```bash
# WSL / macOS — use any editor
nano .env.local
# or
code .env.local    # VS Code (works in both WSL and macOS)
```

### 5.1 Required — LLM provider

The application needs **at least one** LLM provider key to run real agent calls. Without any key the app falls back to mock responses, which is fine for UI testing but means no real SOAP notes, routing, or appointment confirmation messages will be generated.

#### Option A — Groq (recommended, free, no credit card)

1. Go to https://console.groq.com
2. Sign up or log in
3. Click **API Keys** in the left sidebar
4. Click **Create API Key**
5. Copy the key (it starts with `gsk_`)

Set in `.env.local`:

```env
GROQ_API_KEY=gsk_your_key_here
```

Groq gives you free access to Qwen3-32B (used for SOAP notes and handovers) and Llama 3.1 8B (used for routing and reminders). No billing required.

#### Option B — OpenRouter (free tier fallback)

1. Go to https://openrouter.ai
2. Create an account
3. Go to **Keys** → **Create Key**
4. Copy the key (it starts with `sk-or-`)

Set in `.env.local`:

```env
OPENROUTER_API_KEY=sk-or-your_key_here
```

Free models on OpenRouter have a limit of 20 requests per minute and 200 per day. Use this as a backup when Groq rate limits.

#### Option C — Ollama (offline, no API key needed)

For fully offline operation, install Ollama:

**macOS:**

```bash
brew install ollama
ollama serve &          # starts the Ollama daemon in background
ollama pull qwen2.5:32b # downloads the model (~20 GB — do this once)
```

**WSL:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull qwen2.5:32b
```

Set in `.env.local`:

```env
OLLAMA_BASE_URL=http://localhost:11434
```

> **Disk requirement:** Qwen2.5 32B requires approximately 20 GB of free disk space. The model downloads once and is cached at `~/.ollama/models/`.

### 5.2 Optional integrations

These are all optional. The application runs and demos without any of them.

#### Telegram notifications

Required if you want instant push notifications when appointments are booked or cancelled.

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Follow the prompts to choose a name and username for your bot
4. Copy the HTTP API token BotFather gives you (format: `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ`)
5. Add your bot to a group or channel, or start a direct chat with it and send a message
6. Fetch `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser
7. Copy the `chat.id` value from the response (negative number for groups, positive for DMs)

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_CHAT_ID=-1001234567890
```

#### Langfuse observability (optional but useful)

Langfuse is already included in the Docker stack. It runs at http://localhost:3001.

1. Open http://localhost:3001 in your browser (after `make up`)
2. Create an account (local — not sent anywhere)
3. Create a project called `cliniqai`
4. Go to Settings → API Keys
5. Copy the public key and secret key

```env
LANGFUSE_HOST=http://localhost:3001
LANGFUSE_PUBLIC_KEY=pk-lf-your_public_key
LANGFUSE_SECRET_KEY=sk-lf-your_secret_key
```

#### WhatsApp via Twilio (optional — for production)

The demo uses Gradio's chat widget instead of WhatsApp. WhatsApp requires Meta approval which takes days, so it is a post-hackathon integration.

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

#### Google Calendar and Gmail MCP (optional)

Required only if you want real Google Calendar slot checking instead of the local Postgres calendar backend (which is the default). The local backend works for demos without any Google credentials.

The calendar backend is controlled by:

```env
CALENDAR_BACKEND=local   # default — uses Postgres, no Google needed
# CALENDAR_BACKEND=google  # uncomment to use Google Calendar MCP
```

### 5.3 Complete .env.local reference

Below is a fully annotated `.env.local` with every field explained. Copy this and fill in the values you have.

```env
# ============================================================
# DATABASE — do not change these for local dev
# They match what docker-compose.dev.yml creates
# ============================================================
POSTGRES_USER=cliniq
POSTGRES_PASSWORD=cliniq
POSTGRES_DB=cliniq
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://cliniq:cliniq@localhost:5432/cliniq

# ============================================================
# REDIS — do not change for local dev
# ============================================================
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ============================================================
# LLM PROVIDERS — set at least one
# ============================================================
GROQ_API_KEY=           # https://console.groq.com — free, no card
OPENROUTER_API_KEY=     # https://openrouter.ai — free fallback
OLLAMA_BASE_URL=http://localhost:11434   # local offline option

# ============================================================
# WHISPER TRANSCRIPTION
# groq  — uses Groq API (fast, needs GROQ_API_KEY)
# local — uses local transformers pipeline (slow first run, offline)
# auto  — tries groq, falls back to local if GROQ_API_KEY unset
# ============================================================
WHISPER_MODEL=openai/whisper-large-v3-turbo
WHISPER_BACKEND=groq

# ============================================================
# TELEGRAM (optional — for instant push notifications)
# ============================================================
TELEGRAM_BOT_TOKEN=     # from @BotFather
TELEGRAM_CHAT_ID=       # numeric id from getUpdates

# ============================================================
# CALENDAR BACKEND
# local  — Postgres-backed mini calendar (default, no Google needed)
# google — Google Calendar MCP (requires OAuth token)
# ============================================================
CALENDAR_BACKEND=local

# ============================================================
# LANGFUSE OBSERVABILITY (optional)
# Runs locally at :3001 after `make up`
# ============================================================
LANGFUSE_HOST=http://localhost:3001
LANGFUSE_PUBLIC_KEY=    # from http://localhost:3001 after first login
LANGFUSE_SECRET_KEY=

# ============================================================
# TWILIO WHATSAPP (optional — production only)
# Demo uses Gradio chat widget on the same code path
# ============================================================
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# ============================================================
# GOOGLE MCP URLS — leave as-is unless changing backends
# ============================================================
GOOGLE_CALENDAR_MCP_URL=https://calendarmcp.googleapis.com
GMAIL_MCP_URL=https://gmailmcp.googleapis.com
GOOGLE_DRIVE_MCP_URL=https://drivemcp.googleapis.com

# ============================================================
# APP
# ============================================================
CLINIQ_ENV=dev
CLINIQ_API_KEY=dev-local-key
HF_SPACE_BACKEND_URL=http://localhost:8000
```

---

## 6. Start infrastructure (Docker)

Make sure Docker Desktop is running (the whale icon in the system tray / menu bar is active and not animating).

From the project root:

```bash
make up
```

This starts three containers:
- `cliniqai-postgres` — PostgreSQL 16 on port 5432
- `cliniqai-redis` — Redis 7 on port 6379
- `cliniqai-langfuse` — Langfuse on port 3001

Verify all three containers are healthy:

```bash
docker compose ps
```

Expected output:

```
NAME                 STATUS
cliniqai-postgres    Up (healthy)
cliniqai-redis       Up (healthy)
cliniqai-langfuse    Up (healthy)
```

If any container shows `unhealthy` or `Exiting`, check logs:

```bash
docker compose logs postgres
docker compose logs redis
docker compose logs langfuse
```

---

## 7. Apply the database schema

This creates all tables (patients, appointments, staff, shifts, soap_drafts, audit_log, etc.):

```bash
make migrate
```

You should see Alembic output ending with:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_init, initial schema
```

If you see `connection refused` errors, Docker has not finished starting yet. Wait 10 seconds and retry.

Verify tables were created:

```bash
docker exec -it cliniqai-postgres psql -U cliniq -d cliniq -c "\dt"
```

Expected output lists: `appointments`, `audit_log`, `discharges`, `messages`, `patients`, `shifts`, `soap_drafts`, `staff`.

---

## 8. Run the application

Each process below needs its own terminal window. Open new terminals before running each command. In VS Code you can use the split terminal button (`Ctrl+Shift+5` / `Cmd+Shift+5`) to open multiple panes.

### 8.1 Minimal mode (no Celery)

This is sufficient for the demo — UI works, agents work, mocks work. Timed reminders (T-3h, T-24h) will not fire, but instant Telegram notifications still work.

**Terminal 1 — FastAPI backend:**

```bash
make api
```

Wait until you see:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2 — Gradio UI:**

```bash
make ui
```

Wait until you see:

```
Running on local URL:  http://127.0.0.1:7860
```

Open http://localhost:7860 in your browser. You should see the CliniqAI tabs: Doctor, Patient, Nurse & Admin.

### 8.2 Full mode (all processes)

Open five separate terminals from the project root.

**Terminal 1 — Infrastructure (if not already running):**

```bash
make up
```

**Terminal 2 — FastAPI backend:**

```bash
make api
```

**Terminal 3 — Gradio UI:**

```bash
make ui
```

**Terminal 4 — Celery worker:**

```bash
make worker
```

Wait until you see:

```
[tasks] Registered: appointment.send_reminder
[tasks] Registered: appointment.check_no_show
celery@hostname ready.
```

**Terminal 5 — Celery beat (cron scheduler):**

```bash
make beat
```

Wait until you see:

```
beat: Starting...
Scheduler: PersistentScheduler
```

#### Terminal layout reference

```
┌─────────────────────┬─────────────────────┐
│  Terminal 1         │  Terminal 2         │
│  make up            │  make api           │
│  (infrastructure)   │  (FastAPI :8000)    │
├─────────────────────┼─────────────────────┤
│  Terminal 3         │  Terminal 4         │
│  make ui            │  make worker        │
│  (Gradio :7860)     │  (Celery worker)    │
├─────────────────────┴─────────────────────┤
│  Terminal 5                               │
│  make beat  (Celery beat / cron)          │
└───────────────────────────────────────────┘
```

---

## 9. Verify everything is working

Run these checks after starting all processes. Each check is independent — run them in any free terminal.

### Check 1 — Health endpoint

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status": "ok", "env": "dev", "service": "cliniqai-backend"}
```

### Check 2 — Orchestrator routing

```bash
curl -s -X POST http://localhost:8000/orchestrate \
  -H "content-type: application/json" \
  -d '{"utterance": "book me an appointment"}' | python3 -m json.tool
```

Expected: a JSON object with `current_agent: "appointment"` and a `communication` field containing an appointment reply draft.

### Check 3 — SOAP note mock

```bash
curl -s -X POST http://localhost:8000/documentation/draft \
  -H "content-type: application/json" \
  -d '{"patient_id": "p-001"}' | python3 -m json.tool
```

Expected: a JSON object with `draft_id`, `soap` (subjective/objective/assessment/plan), `icd10_suggestions`, and `sources`.

### Check 4 — Roster generation (mock data)

```bash
curl -s -X POST http://localhost:8000/roster/generate \
  -H "content-type: application/json" \
  -d '{}' | python3 -m json.tool
```

Expected: a JSON object with `roster_id`, `assignments` (array of shift objects), and `fairness_score`.

### Check 5 — Handover brief

```bash
curl -s -X POST http://localhost:8000/handover/generate \
  -H "content-type: application/json" \
  -d '{"ward_id": "ward-A"}' | python3 -m json.tool
```

Expected: a JSON object with `brief_id`, `patients` array ordered urgent → watch → stable.

### Check 6 — Database connectivity

```bash
curl -s -X POST http://localhost:8000/appointment/book \
  -H "content-type: application/json" \
  -d '{"patient_id": "p-test-001"}' | python3 -m json.tool
```

Expected: a `BookingResult` with `appointment_id`, `slot_iso`, and `status: "confirmed"`. If you see `connection refused` or a 500 error mentioning PostgreSQL, the database container is not running.

### Check 7 — Full test suite

```bash
make test
```

Expected: all tests pass. Contract tests and routing smoke tests run without any external keys.

### Check 8 — Linter

```bash
make lint
```

Expected: no output (clean). Warnings are acceptable, errors mean something changed in contracts.

### Check 9 — OpenAPI docs

Open http://localhost:8000/docs in your browser. You should see the Swagger UI with all agent endpoints grouped by tag: documentation, appointment, clerical, discharge, roster, handover.

### Check 10 — Telegram (if configured)

```bash
python3 -c "
from dotenv import load_dotenv
load_dotenv('.env.local')
from app.integrations.telegram import send
result = send('CliniqAI test message — setup complete')
print(result)
"
```

Expected: `{'status': 'sent', 'chat_id': '-100...', 'message_id': 123}` and a message appearing in your Telegram.

If you see `{'status': 'stub', ...}`, the token or chat ID is not set in `.env.local`. See section 5.2.

---

## 10. Stopping the application

### Stop individual processes

Press `Ctrl+C` in each terminal. Gradio, FastAPI, Celery worker, and beat all respond to `Ctrl+C`.

### Stop Docker containers

```bash
make down
```

This stops and removes the containers but **preserves data**. PostgreSQL data persists in a Docker volume named `cliniqai_postgres_data`. Your appointments, staff records, and SOAP drafts survive a `make down`.

### Stop Docker containers and wipe all data

Use this when you want a completely clean slate (e.g., schema changes require recreating the database):

```bash
docker compose down -v
```

The `-v` flag removes the volumes. Run `make migrate` again after this to recreate the schema.

---

## 11. Hugging Face Spaces deployment

The Gradio UI is designed to deploy to Hugging Face Spaces. The FastAPI backend must be deployed separately (e.g., on a cloud VM) because Spaces runs only the Gradio process.

### Step 1 — Push to Hugging Face Spaces

1. Create a Space at https://huggingface.co/spaces
2. Choose **Gradio** as the SDK
3. Choose **Python 3.12** as the runtime
4. Set the Space as **private** (HIPAA considerations)

```bash
# Add the HF Space as a remote
git remote add space https://huggingface.co/spaces/your-username/cliniqai

# Push the deploy folder
git subtree push --prefix deploy/hf_space space main
```

### Step 2 — Configure Secrets in the Space

In your Space → Settings → Repository secrets, add:

| Secret | Value |
|---|---|
| `HF_SPACE_BACKEND_URL` | `https://your-backend-api.example.com` |
| `GROQ_API_KEY` | Your Groq key |
| `TELEGRAM_BOT_TOKEN` | Your bot token |
| `TELEGRAM_CHAT_ID` | Your chat ID |

The Space reads secrets as environment variables at runtime. Never commit secrets to git.

### Step 3 — Verify Space deployment

After the Space builds (watch the build logs in the Spaces UI), open the Space URL and confirm all three tabs load and the backend URL shown at the top matches your deployed API.

---

## 12. Troubleshooting by OS

### Windows / WSL

---

**Problem:** `make: command not found` inside WSL

```bash
sudo apt install -y make
```

---

**Problem:** `docker: command not found` inside WSL even though Docker Desktop is installed

Open Docker Desktop → Settings → Resources → WSL Integration. Toggle off, save, toggle on, save again. Then restart the WSL terminal:

```bash
wsl --shutdown       # run this in PowerShell
# Then reopen Ubuntu
```

---

**Problem:** `curl` to `localhost:8000` times out from inside WSL

FastAPI binds to `0.0.0.0:8000` which is accessible from inside WSL as `localhost`. If it still times out, check that FastAPI started without errors and that Windows Firewall is not blocking port 8000. Try from a Windows browser using the IP shown in `ip addr show eth0` inside WSL.

---

**Problem:** Files cloned on `/mnt/c/` cause very slow `uv sync`

Move the project into the WSL filesystem:

```bash
cp -r /mnt/c/Users/yourname/clinical-pilot-hf ~/clinical-pilot-hf
cd ~/clinical-pilot-hf
```

---

**Problem:** `psycopg` fails with `library not found for -lssl`

```bash
sudo apt install -y libpq-dev libssl-dev
make install    # reinstall dependencies
```

---

**Problem:** `torch` install fails or takes forever in WSL

`torch` is large (~2 GB download). If it hangs, check your WSL memory limit. Create `%USERPROFILE%\.wslconfig` on Windows with:

```ini
[wsl2]
memory=8GB
processors=4
```

Then restart WSL: `wsl --shutdown` in PowerShell.

---

### macOS

---

**Problem:** `make install` fails with `error: externally-managed-environment`

This means system Python is being used instead of uv's managed Python. Make sure you installed uv and that `~/.local/bin` (or `~/.cargo/bin`) is on your PATH:

```bash
echo $PATH   # should include ~/.local/bin
source ~/.zshrc
uv --version
```

---

**Problem:** `psycopg[binary]` install fails on Apple Silicon

The binary wheel for `psycopg` may not build without libpq. Install it via Homebrew:

```bash
brew install libpq
export LDFLAGS="-L/opt/homebrew/opt/libpq/lib"
export CPPFLAGS="-I/opt/homebrew/opt/libpq/include"
make install
```

---

**Problem:** `torch` install is very slow on Apple Silicon

This is expected on first install — PyTorch for Apple Silicon is about 700 MB. Let it complete. Subsequent installs use the uv cache and are instant.

---

**Problem:** Docker Desktop is not starting on macOS

1. Open Activity Monitor and search for `Docker`
2. If it is running but unresponsive, force quit it
3. Restart Docker Desktop from Applications
4. If it still fails, reset to factory defaults: Docker menu → Troubleshoot → Reset to factory defaults

---

**Problem:** Port 5432 already in use

You have a local PostgreSQL installation running alongside the Docker one. Stop it:

```bash
# macOS native Postgres (if installed via Homebrew)
brew services stop postgresql@16
# or
pg_ctl stop -D /opt/homebrew/var/postgresql@16
```

Then re-run `make up`.

---

**Problem:** Port 6379 already in use

You have a local Redis running:

```bash
brew services stop redis
```

Then re-run `make up`.

---

### Both platforms

---

**Problem:** `RuntimeError: router: all models in chain for task=... failed`

No LLM provider key is configured or all are rate-limited. Check:

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('.env.local')
print('GROQ:', bool(os.getenv('GROQ_API_KEY')))
print('OPENROUTER:', bool(os.getenv('OPENROUTER_API_KEY')))
print('OLLAMA:', bool(os.getenv('OLLAMA_BASE_URL')))
"
```

At least one must print `True`. If all print `False`, your `.env.local` is not being found or the keys are empty.

---

**Problem:** `connection refused` on port 5432

PostgreSQL container is not running. Check:

```bash
docker compose ps
docker compose logs postgres
```

Common causes: Docker Desktop is not running, or a previous `docker compose down -v` wiped the data and `make migrate` has not been re-run.

---

**Problem:** Alembic migration fails with `relation already exists`

The schema was partially applied. Run a full reset:

```bash
docker compose down -v
make up
# wait 10 seconds for postgres to become ready
make migrate
```

---

**Problem:** `ModuleNotFoundError: No module named 'app'`

The virtual environment is not activated or the package is not installed in editable mode. Run:

```bash
make install      # re-installs everything
```

Or manually activate:

```bash
source .venv/bin/activate
```

---

**Problem:** Gradio UI shows `ConnectionError — backend unreachable`

The FastAPI backend is not running. Make sure `make api` is running in a separate terminal and http://localhost:8000/health returns `{"status":"ok"}`.

---

**Problem:** `Telegram stub mode` — notifications not arriving

Either `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` is empty in `.env.local`. Both are required. See section 5.2 for how to obtain them. After setting them, restart FastAPI and the Celery worker.

---

**Problem:** Celery tasks are queued but never execute

The Celery worker is not running. Open a new terminal and run `make worker`. You should see tasks being picked up within seconds of the next appointment booking.

---

## Quick-reference cheat sheet

```bash
# First time only
make install          # install deps
cp .env.example .env.local && nano .env.local
make up               # start Docker (Postgres + Redis + Langfuse)
make migrate          # create DB tables

# Every day — open 4 terminals
make up               # terminal 1 (if not already running)
make api              # terminal 2
make ui               # terminal 3
make worker           # terminal 4 (only needed for reminders)

# Checks
curl localhost:8000/health
make test
make lint

# Reset everything
docker compose down -v && make up && make migrate

# Useful Docker commands
docker compose ps           # see container status
docker compose logs -f      # tail all logs
docker compose logs postgres # logs for one service
```