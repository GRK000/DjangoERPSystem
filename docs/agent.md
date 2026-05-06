# Aurora Operator

Aurora Operator es el agente operativo read-only de Aurora Ops ERP. Consulta datos del ERP mediante tools whitelisted y responde con evidencia, tool calls y acciones sugeridas de navegacion.

## Que Hace

- Resume operaciones, albaranes, preparacion, stock, clientes y ventas.
- Prioriza albaranes pendientes.
- Detecta bloqueos de stock.
- Lista productos con stock bajo.
- Consulta rankings y estadisticas.

## Que No Hace

- No modifica datos.
- No prepara albaranes.
- No marca entregas.
- No cambia stock.
- No crea movimientos.
- No borra ni edita registros.

## Arquitectura

Frontend React -> `/api/agent/run/` -> Orquestador Django -> planner LLM o heuristico -> tools read-only -> ORM -> respuesta grounded.

El LLM no accede a la base de datos. Solo recibe resultados resumidos de tools.

## Variables de Entorno

Ver `.env.example`.

Modo mock seguro:

```bash
AI_PROVIDER=mock
AGENT_ENABLE_REAL_LLM=false
```

Modo OpenAI-compatible:

```bash
AI_PROVIDER=openai_compatible
AI_BASE_URL=https://api.groq.com/openai/v1
AI_MODEL=llama-3.3-70b-versatile
AI_API_KEY=your_api_key_here
AGENT_ENABLE_REAL_LLM=true
```

No se guardan ni se exponen API keys.

## Endpoints

- `GET /api/agent/status/`
- `GET /api/agent/suggestions/`
- `GET /api/agent/conversations/`
- `POST /api/agent/conversations/`
- `GET /api/agent/conversations/<id>/`
- `POST /api/agent/run/`
- `POST /api/agent/feedback/`

Todos requieren usuario autenticado.

## CLI

```bash
python manage.py agent_smoke_test --mock "Que albaranes puedo preparar hoy?"
python manage.py agent_eval --dataset aurora_agent/evals/smoke.json --mock
```

## UI

Abre `/consulta/` con sesion iniciada. La pantalla muestra estado del proveedor, sugerencias, historial, evidencia, tool calls, acciones sugeridas y feedback.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

## CI/CD

`.github/workflows/ci.yml` ejecuta checks de Django, tests, smoke/eval del agente, build de frontend y build Docker. En `main` prepara una imagen etiquetada para GHCR sin publicar secretos.

## Seguridad

- Tools read-only declaradas en registry.
- Guardrails bloquean escritura, prompts internos y secretos.
- Resultados de tools se limitan por `AGENT_MAX_TOOL_RESULTS`.
- Conversaciones y runs se aíslan por usuario.
- Suggested actions solo navegan, filtran o inspeccionan.

## Limitaciones

- V1 no ejecuta acciones de escritura.
- El planner LLM tiene fallback heuristico.
- No hay streaming.
- No hay busqueda semantica ni RAG documental.
