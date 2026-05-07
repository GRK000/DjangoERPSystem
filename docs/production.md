# Production Notes

Aurora Ops ERP is safe to run locally with mock agent mode. Production requires explicit environment configuration.

## Required Environment

```text
DEBUG=false
SECRET_KEY=<strong-secret-from-env>
ALLOWED_HOSTS=your-domain.example
CSRF_COOKIE_SECURE=true
SESSION_COOKIE_SECURE=true
SECURE_SSL_REDIRECT=true
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
SECURE_HSTS_PRELOAD=true
SECURE_PROXY_SSL_HEADER=true
LOG_LEVEL=INFO
```

Agent mock mode:

```text
AI_PROVIDER=mock
AI_API_KEY=
AI_MODEL=mock
AGENT_ENABLE_REAL_LLM=false
```

OpenAI-compatible provider:

```text
AI_PROVIDER=openai_compatible
AI_API_KEY=<provider-key>
AI_BASE_URL=https://api.groq.com/openai/v1
AI_MODEL=llama-3.3-70b-versatile
AGENT_ENABLE_REAL_LLM=true
```

Never commit API keys. GitHub Secrets should only be used for future deploys or manual real-provider checks, not for mock CI.

## Build And Verify

```bash
cd frontend
npm ci
npm run build
cd ..
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check
python manage.py check --deploy
python manage.py test
python manage.py agent_eval --dataset aurora_agent/evals/smoke.json --mock
```

## Deploy Check

`python manage.py check --deploy` reviews critical deployment settings such as `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, HTTPS redirect, secure cookies and static files.

Warnings expected in local development:

- `DEBUG=true`
- `SECURE_SSL_REDIRECT=false`
- `SESSION_COOKIE_SECURE=false`
- `CSRF_COOKIE_SECURE=false`
- `SECURE_HSTS_SECONDS=0`

These should be fixed in production with environment variables.

## Static Files

`STATIC_ROOT=staticfiles` is configured for `collectstatic`.

Development serves compiled Vite assets from:

```text
frontend/dist
```

Run `npm run build` after frontend changes.

## Docker

```bash
docker compose config
docker compose build
docker compose up
```

The Dockerfile builds Vite assets, installs Python dependencies, runs migrations at startup and launches Gunicorn.

## CI

GitHub Actions uses mock mode:

```text
AI_PROVIDER=mock
AGENT_ENABLE_REAL_LLM=false
AI_API_KEY=
```

CI validates backend, agent evals, frontend build and Docker build without calling external LLM providers.
