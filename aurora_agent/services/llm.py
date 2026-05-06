import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from django.conf import settings


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


def agent_status():
    provider = getattr(settings, "AI_PROVIDER", "mock")
    api_key = getattr(settings, "AI_API_KEY", "")
    real_enabled = getattr(settings, "AGENT_ENABLE_REAL_LLM", False)
    mock_mode = provider == "mock" or not real_enabled
    missing_api_key = provider != "mock" and not bool(api_key)
    return {
        "available": mock_mode or (provider == "openai_compatible" and bool(api_key) and real_enabled),
        "provider": provider,
        "model": getattr(settings, "AI_MODEL", ""),
        "missing_api_key": missing_api_key,
        "mock_mode": mock_mode,
        "real_llm_enabled": bool(real_enabled),
    }


class MockLLMClient:
    provider = "mock"
    model = "aurora-mock"

    def chat(self, messages, temperature=None, max_tokens=None):
        last = messages[-1]["content"] if messages else ""
        if "JSON" in last or "tools" in last:
            return LLMResponse('{"tools":[{"name":"summarize_daily_operations","arguments":{}}]}')
        return LLMResponse("Respuesta generada en modo mock con datos devueltos por tools.")


class OpenAICompatibleClient:
    provider = "openai_compatible"

    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.base_url = settings.AI_BASE_URL.rstrip("/")
        self.model = settings.AI_MODEL
        self.timeout = settings.AI_TIMEOUT_SECONDS

    def chat(self, messages, temperature=None, max_tokens=None):
        if not self.api_key:
            raise RuntimeError("AI_API_KEY no configurada.")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": settings.AI_TEMPERATURE if temperature is None else temperature,
            "max_tokens": settings.AI_MAX_OUTPUT_TOKENS if max_tokens is None else max_tokens,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as error:
            raise RuntimeError(f"Error llamando al proveedor LLM: {error}") from error
        choice = (data.get("choices") or [{}])[0]
        usage = data.get("usage") or {}
        return LLMResponse(
            content=(choice.get("message") or {}).get("content", ""),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )


def get_llm_client(force_mock=False):
    status = agent_status()
    if force_mock or status["mock_mode"]:
        return MockLLMClient()
    if settings.AI_PROVIDER == "openai_compatible":
        return OpenAICompatibleClient()
    return MockLLMClient()
