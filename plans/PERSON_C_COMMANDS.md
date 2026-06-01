### 1. Start infrastrucure

```docker compose -f infra/docker-compose.dev.yml up -d```

**check status**

```docker compose -f infra/docker-compose.dev.yml ps```

#### Expected services
- cliniq-postgres
- cliniq-redis
- cliniq-langfuse

### 2. Apply Migrations 

```
cd infra
alembic -c alembic.ini upgrade head
cd ..
```
### 3. Run Pytest
`uv run pytest`

### 4. Run fastapi 
`uv run uvicorn app.api.main:app --reload --port 8000`

### 5. Run Gradio 
`uv run python deploy/hf_space/app.py`

