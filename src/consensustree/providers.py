"""Zero-third-party-dependency integrations with four LLM APIs.

Requests are sent only to fixed, documented provider endpoints, except the
local Ollama endpoint configured by the user. No API keys are logged.
"""

from __future__ import annotations

import json
import os
import re
import math
import ipaddress
import urllib.parse
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_MODELS = {
    "openai": "gpt-4.1-mini",
    "gemini": "gemini-2.5-flash",
    "anthropic": "claude-sonnet-4-5",
    "ollama": "llama3.2",
}
KEY_VARS = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Prevent leaking provider credentials to redirect destinations."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,110}$")


MAX_COMPLETION_CHARS = 64_000


def _bounded_completion(text: str) -> str:
    """Reject blank or unexpectedly large provider output, never silently truncate reasoning."""
    if not isinstance(text, str) or not text.strip():
        raise ProviderError("Provider returned empty model text")
    if len(text) > MAX_COMPLETION_CHARS:
        raise ProviderError("Provider completion exceeds the 64,000-character safety limit")
    return text


def _safe_ollama_endpoint(value: str) -> str:
    """Avoid plaintext transmission of code to remote, user-configured inference hosts."""
    if not isinstance(value, str) or len(value) > 400:
        raise ValueError("Invalid Ollama endpoint URL")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("Ollama endpoint must be a plain HTTP(S) server origin")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid Ollama endpoint port") from exc
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Invalid Ollama endpoint port")
    try:
        is_loopback = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        is_loopback = parsed.hostname.casefold() == "localhost"
    if parsed.scheme == "http" and not is_loopback:
        raise ValueError("Remote Ollama URLs must use HTTPS to protect transmitted source")
    return value.rstrip("/")


class ProviderError(RuntimeError):
    """Raised when configuration or an LLM request fails."""


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str

    def __post_init__(self) -> None:
        if self.provider not in DEFAULT_MODELS:
            raise ValueError("Unsupported model provider")
        if (not isinstance(self.model, str) or not _MODEL_PATTERN.fullmatch(self.model) or
            any(p in {".", ".."} for p in self.model.split("/"))):
            raise ValueError("Invalid model name")

    @classmethod
    def parse(cls, value: str) -> "ModelSpec":
        if ":" not in value:
            raise ValueError("Use provider:model, e.g. openai:gpt-4.1-mini")
        provider, model = value.split(":", 1)
        if provider not in DEFAULT_MODELS or not model.strip():
            raise ValueError("Unsupported provider or empty model name: " + value)
        return cls(provider=provider, model=model.strip())

    def __str__(self) -> str:
        return f"{self.provider}:{self.model}"


def _post_json(url: str, headers: dict[str, str], data: dict[str, Any], timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            payload = response.read(4_000_001)
        if len(payload) > 4_000_000:
            raise ProviderError("Provider response exceeds the 4 MB safety limit")
        result = json.loads(payload)
        if not isinstance(result, dict):
            raise ProviderError("Provider returned an unexpected JSON response")
        return result
    except urllib.error.HTTPError as exc:
        # Intentionally never echo the URL (could include config) or raw response.
        code = exc.code
        message = {
            400: "Invalid request or unsupported model",
            401: "Authentication failed; verify your API key",
            402: "Provider billing/credit issue",
            403: "Access denied for your API key or model",
            404: "Model or endpoint unavailable",
            429: "Rate limit or quota reached",
        }.get(code, "Provider server or request error")
        raise ProviderError(f"HTTP {code}: {message}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ProviderError("Cannot reach provider (network, connection, or timeout)") from exc
    except (ValueError, UnicodeError) as exc:
        raise ProviderError("Provider returned an invalid JSON response") from exc


def _extract_openai(data: dict) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            text = "\n".join(item["text"] for item in content if isinstance(item, dict)
                             and isinstance(item.get("text"), str))
            if text.strip():
                return text.strip()
    except (KeyError, IndexError, TypeError):
        pass
    raise ProviderError("OpenAI response contained no text")


def _extract_anthropic(data: dict) -> str:
    chunks = data.get("content")
    if not isinstance(chunks, list):
        raise ProviderError("Claude response contained no content")
    text = "\n".join(x["text"] for x in chunks if isinstance(x, dict)
                     and x.get("type") == "text" and isinstance(x.get("text"), str))
    if not text.strip():
        raise ProviderError("Claude response contained no text")
    return text.strip()


def _extract_gemini(data: dict) -> str:
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "\n".join(item["text"] for item in parts if isinstance(item, dict)
                         and isinstance(item.get("text"), str))
        if text.strip():
            return text.strip()
    except (KeyError, TypeError, IndexError):
        pass
    raise ProviderError("Gemini response contained no text (possibly blocked)")


def _extract_ollama(data: dict) -> str:
    message = data.get("message", {})
    if not isinstance(message, dict):
        raise ProviderError("Ollama response contained no text")
    text = message.get("content", "")
    if not isinstance(text, str) or not text.strip():
        raise ProviderError("Ollama response contained no text")
    return text.strip()



def provider_usage(provider: str, data: dict) -> dict | None:
    """Normalize token counts returned by model backends; never estimate or bill.

    The numbers are provider-reported usage, not an invoice. Missing fields
    remain missing. Never infer tokens from response length.
    """
    try:
        if provider == "openai":
            raw = data.get("usage", {})
            inp, out = raw.get("prompt_tokens"), raw.get("completion_tokens")
        elif provider == "anthropic":
            raw = data.get("usage", {})
            inp, out = raw.get("input_tokens"), raw.get("output_tokens")
        elif provider == "gemini":
            raw = data.get("usageMetadata", {})
            inp, out = raw.get("promptTokenCount"), raw.get("candidatesTokenCount")
        elif provider == "ollama":
            inp, out = data.get("prompt_eval_count"), data.get("eval_count")
        else:
            return None
        if not all(type(n) is int and 0 <= n <= 100_000_000 for n in (inp, out)):
            return None
        return {"source": "provider_reported", "input_tokens": inp,
                "output_tokens": out, "total_tokens": inp + out}
    except (AttributeError, TypeError):
        return None

class LLMClient:
    """Simple transport for OpenAI, Google Gemini, Anthropic, and local Ollama."""

    def __init__(self, *, timeout: float = 120.0, ollama_url: str = "http://localhost:11434") -> None:
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 600:
            raise ValueError("Model timeout must be a finite number in (0,600]")
        self.timeout = timeout
        self.ollama_url = _safe_ollama_endpoint(ollama_url)
        self.last_usage: dict | None = None

    def complete(self, spec: ModelSpec, system: str, user: str) -> str:
        self.last_usage = None  # Do not carry stale metrics across failures.
        provider, model = spec.provider, spec.model
        if provider not in DEFAULT_MODELS:
            raise ProviderError(f"Unknown provider: {provider}")
        if provider in KEY_VARS:
            key = os.getenv(KEY_VARS[provider], "").strip()
            if not key:
                raise ProviderError(f"Missing {KEY_VARS[provider]} environment variable")

        if provider == "openai":
            response = _post_json(
                "https://api.openai.com/v1/chat/completions",
                {"Authorization": f"Bearer {key}"},
                {"model": model, "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ]},
                self.timeout,
            )
            content = _bounded_completion(_extract_openai(response))
            self.last_usage = provider_usage("openai", response)
            return content
        if provider == "anthropic":
            response = _post_json(
                "https://api.anthropic.com/v1/messages",
                {"x-api-key": key, "anthropic-version": "2023-06-01"},
                {"model": model, "max_tokens": 1600, "system": system,
                 "messages": [{"role": "user", "content": user}]},
                self.timeout,
            )
            content = _bounded_completion(_extract_anthropic(response))
            self.last_usage = provider_usage("anthropic", response)
            return content
        if provider == "gemini":
            response = _post_json(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                {"x-goog-api-key": key},
                {"systemInstruction": {"parts": [{"text": system}]},
                 "contents": [{"role": "user", "parts": [{"text": user}]}],
                 "generationConfig": {"maxOutputTokens": 1700}},
                self.timeout,
            )
            content = _bounded_completion(_extract_gemini(response))
            self.last_usage = provider_usage("gemini", response)
            return content
        response = _post_json(
            f"{self.ollama_url}/api/chat",
            {},
            {"model": model, "stream": False,
             "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            self.timeout,
        )
        content = _bounded_completion(_extract_ollama(response))
        self.last_usage = provider_usage("ollama", response)
        return content
