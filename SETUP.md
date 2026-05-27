# SETUP — Day 0 foundation is live

The shared rails Person C is supposed to ship on Day 0 are in place. A, B, and
C can each run their own track without blocking on one another.

## First-time setup

```bash
# 1) Install deps (requires uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
make install

# 2) Copy env template, fill in keys you have
cp .env.example .env.local
# at minimum set GROQ_API_KEY or OPENROUTER_API_KEY for real LLM calls
# (the mocks below run without any keys)

# 3) Bring up Postgres + Redis + Langfuse
make up

# 4) Apply DB schema
make migrate

# 5) Smoke-test the orchestrator end-to-end (uses mocks if no keys present)
python -m app.orchestrator "please write today's SOAP note"

# 6) Run the API + UI
make api   # in one terminal — FastAPI on :8000
make ui    # in another terminal — Gradio on :7860
```

## Verify the foundation

```bash
make test     # contract + routing smoke tests
make lint     # ruff
curl localhost:8000/health
curl -X POST localhost:8000/orchestrate -d '{"utterance":"book me an appointment"}' -H 'content-type: application/json'
```

## Where each person starts

| You are… | Open this | First file you touch |
|---|---|---|
| **Person A** | `plans/PLAN_PERSON_A.md` | `app/agents/documentation/api.py` + `wiki/conditions/hypertension.md` |
| **Person B** | `plans/PLAN_PERSON_B.md` | `app/agents/appointment/api.py` + `app/integrations/whatsapp.py` |
| **Person C** | `plans/PLAN_PERSON_C.md` | `app/agents/roster/api.py` + `app/db/migrations/versions/` |

Every public agent function currently raises `NotImplementedError` with the
owner and target day. Every router endpoint returns the mock so the UI can be
driven end-to-end while the real agents are being built.

When you replace a `NotImplementedError`, also delete that agent's
`mocks.py` import from `app/orchestrator.py` and `app/api/routers/*.py` —
or leave the mocks as a fallback path, your call.
