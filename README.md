# Aurora Ops ERP

![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.0-0C4B33?logo=django&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=111111)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)

Modern ERP with Django, Aurora UI and a read-only AI operations agent.

Aurora Ops ERP manages customers, product catalog, delivery notes, preparation queues, warehouse stock and sales analytics. The UI is designed as an operational command center with Night Ops and Day Ops themes plus Command and Operator density modes.

## Screenshots

Screenshots to be added after final visual pass.

- `docs/assets/night-ops-dashboard.png`
- `docs/assets/day-ops-dashboard.png`
- `docs/assets/aurora-operator.png`
- `docs/assets/agent-runs.png`

## Highlights

- Delivery notes and inventory management.
- Atomic stock operations with `transaction.atomic()` and row locking in preparation flows.
- Command / Operator density modes.
- Night Ops and Day Ops themes.
- Aurora Operator read-only AI agent.
- Semantic query layer for Spanish ERP questions.
- Safe router for ERP, app-help, date/time, unsafe and out-of-scope requests.
- Tool call tracing, Agent Runs panel and feedback.
- Mock and OpenAI-compatible LLM providers.
- Reproducible demo data command.
- Docker and GitHub Actions CI.

## Modules

- Customers: active/inactive customer registry.
- Catalog: products, categories and stock totals.
- Delivery notes: lifecycle, line items and totals.
- Preparation: pending queue and stock blockers.
- Stock: warehouse positions, low-stock detection and replenishment.
- Analytics: delivered sales, tax base, VAT, top products and customers.
- Aurora Operator: read-only assistant for operational questions.
- Agent Runs: staff-only traceability for agent behavior.

## Quick Demo

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data --reset
cd frontend
npm install
npm run build
cd ..
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Windows PowerShell activation:

```powershell
.\.venv\Scripts\Activate.ps1
```

If activation is unavailable, run Django through the venv executable:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

## Demo Data

Create a reproducible portfolio demo:

```bash
python manage.py seed_demo_data --reset
```

The command creates demo customers, products, warehouses, stock positions, movements and delivery notes including preparable, blocked, in-preparation and delivered examples. It is idempotent and only resets records with demo prefixes.

## Agent Demo

```bash
python manage.py agent_smoke_test --mock "Qué albaranes puedo preparar hoy?"
python manage.py agent_smoke_test --mock "Qué productos tienen stock bajo?"
python manage.py agent_eval --dataset aurora_agent/evals/smoke.json --mock
```

Useful demo prompts:

- `Cuantos clientes no activos hay?`
- `Que productos tienen stock bajo?`
- `Que productos estan sin stock?`
- `Que albaranes puedo preparar hoy?`
- `Que albaranes estan bloqueados?`
- `Resume la operacion de hoy`
- `Explicame React`

## Environment

Copy `.env.example` to `.env`. Mock mode is the safe default:

```text
AI_PROVIDER=mock
AGENT_ENABLE_REAL_LLM=false
```

For an OpenAI-compatible provider:

```text
AI_PROVIDER=openai_compatible
AI_API_KEY=your_api_key_here
AI_BASE_URL=https://api.groq.com/openai/v1
AI_MODEL=llama-3.3-70b-versatile
AGENT_ENABLE_REAL_LLM=true
```

Do not commit API keys. CI runs in mock mode and does not require `AI_API_KEY`.

## CI

GitHub Actions validates:

- Django migrations, `check`, tests and demo seeding.
- Aurora Operator evals in mock mode.
- Frontend dependency install and `npm run build`.
- Optional frontend lint/test scripts if they exist.
- Docker Compose config and Docker build.

CI does not publish images and does not deploy.

## Docker

```bash
docker compose config
docker compose build
docker compose up
```

## Production Notes

Before production, run:

```bash
python manage.py check --deploy
```

Review `docs/production.md` for environment variables, HTTPS/cookie settings, static files, Docker commands and CI notes.

## Documentation

- Agent architecture: `docs/agent.md`
- Production checklist: `docs/production.md`
- UI modes and visual checklist: `docs/ui.md`
- Screenshot placeholders: `docs/assets/README.md`

## Roadmap

- Write actions with human approval.
- Document RAG for SOPs and customer-specific constraints.
- Demand forecasting and supplier analysis.
- Expanded customer/product profitability dashboards.
