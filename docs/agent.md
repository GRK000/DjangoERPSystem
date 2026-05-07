# Aurora Operator

Aurora Operator is the read-only operations agent integrated into Aurora Ops ERP.

## Architecture

Frontend `/consulta/` -> `/api/agent/run/` -> Django orchestrator -> request router -> semantic query -> whitelisted read-only tools -> Django ORM -> formatter -> grounded answer.

The LLM never receives database access. It can only work with compact JSON results returned by registered tools.

## Request Router

The router classifies messages before planning:

- `erp_query`: use semantic query and read-only ERP tools.
- `app_help`: answer capabilities without ERP tools.
- `utility_date_time`: answer server local date/time without ERP tools.
- `unsafe`: block secret, prompt injection or write requests.
- `out_of_scope`: redirect to ERP domain without ERP tools.

## Semantic Query

The parser extracts:

- `intent`: `count`, `list`, `summarize`, `prioritize`, `analyze`, `blockers`, `help`, `unsafe`, `out_of_scope`.
- `entity`: `customers`, `products`, `delivery_notes`, `stock`, `sales`, `operations`.
- `filters`: active/inactive, low stock, out of stock, pending, delivered, blocked, preparable, period.
- minimal follow-up context: last entity, intent, metric and filters.

Supported examples:

- `Cuantos clientes no activos hay?`
- `Que productos estan sin stock?`
- `Que albaranes son preparables?`
- `Que producto bloquea la preparacion?`
- `Cual es la base imponible?`

## Tools

All tools are read-only and return:

```json
{
  "status": "ok",
  "summary": {},
  "records": [],
  "evidence": [],
  "message": ""
}
```

Main tools:

- `count_customers`, `list_customers`
- `count_products`, `list_products`, `list_low_stock_products`, `list_out_of_stock_products`
- `count_delivery_notes`, `list_delivery_notes`, `check_delivery_note_stock`, `analyze_stock_blockers`, `prioritize_delivery_notes`
- `get_sales_statistics`, `get_top_products`, `get_top_customers`
- `summarize_daily_operations`

## Tracing

Every run stores:

- input and final answer;
- semantic query and route category in message metadata;
- provider/model and latency;
- tool calls with arguments, status, result summary and latency;
- feedback.

Staff users can inspect traces at `/agent-runs/` and through:

- `GET /api/agent/runs/`
- `GET /api/agent/runs/<id>/`

Secrets and API keys are not serialized.

## CLI

```bash
python manage.py agent_smoke_test --mock "Que albaranes puedo preparar hoy?"
python manage.py agent_eval --dataset aurora_agent/evals/smoke.json --mock
```

## Security

- V1 is read-only.
- Write/destructive requests are blocked.
- Prompt injection and secret requests are blocked.
- Out-of-scope requests do not execute ERP tools.
- Tool results are capped by `AGENT_MAX_TOOL_RESULTS`.
- Normal users cannot list global runs.

## Limitations

- No write actions.
- No streaming.
- No document RAG.
- The deterministic router handles the portfolio demo; the LLM planner is optional and bounded by the same registry.
