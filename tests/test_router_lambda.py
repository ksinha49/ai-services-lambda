import importlib.util
import json
import sys


def load_lambda(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_fake_post(calls):
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

        def raise_for_status(self):
            pass

    def fake_post(url, json=None, headers=None):
        payload = {"reply": "bedrock" if "bedrock" in url else "ollama"}
        calls.append((url, json, headers))
        return FakeResponse(payload)

    return fake_post


def test_choose_backend(monkeypatch):
    sys.modules["httpx"].HTTPStatusError = type("E", (Exception,), {})
    monkeypatch.setenv("PROMPT_COMPLEXITY_THRESHOLD", "3")
    module = load_lambda("router_app", "services/llm-router/router-lambda/app.py")
    assert module._choose_backend("a b") == "ollama"
    assert module._choose_backend("a b c d") == "bedrock"


def test_lambda_handler(monkeypatch):
    sys.modules["httpx"].HTTPStatusError = type("E", (Exception,), {})
    monkeypatch.setenv("BEDROCK_OPENAI_ENDPOINT", "http://bedrock")
    monkeypatch.setenv("BEDROCK_API_KEY", "key")
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://ollama")
    monkeypatch.setenv("OLLAMA_DEFAULT_MODEL", "phi")
    monkeypatch.setenv("PROMPT_COMPLEXITY_THRESHOLD", "3")

    module = load_lambda("router_lambda", "services/llm-router/router-lambda/app.py")
    calls = []
    monkeypatch.setattr(module.httpx, "post", _make_fake_post(calls))

    event1 = {"body": json.dumps({"prompt": "short"})}
    out1 = module.lambda_handler(event1, {})
    body1 = json.loads(out1["body"])
    assert body1["backend"] == "ollama"
    assert calls[0][0] == "http://ollama"

    event2 = {"body": json.dumps({"prompt": "one two three four"})}
    out2 = module.lambda_handler(event2, {})
    body2 = json.loads(out2["body"])
    assert body2["backend"] == "bedrock"
    assert calls[1][0] == "http://bedrock"


def test_lambda_handler_backend_override(monkeypatch):
    sys.modules["httpx"].HTTPStatusError = type("E", (Exception,), {})
    monkeypatch.setenv("BEDROCK_OPENAI_ENDPOINT", "http://bedrock")
    monkeypatch.setenv("BEDROCK_API_KEY", "key")
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://ollama")
    monkeypatch.setenv("OLLAMA_DEFAULT_MODEL", "phi")
    monkeypatch.setenv("PROMPT_COMPLEXITY_THRESHOLD", "3")

    module = load_lambda("router_lambda_override", "services/llm-router/router-lambda/app.py")
    calls = []
    monkeypatch.setattr(module.httpx, "post", _make_fake_post(calls))

    event = {"body": json.dumps({"prompt": "short", "backend": "bedrock"})}
    out = module.lambda_handler(event, {})
    body = json.loads(out["body"])
    assert body["backend"] == "bedrock"
    assert calls[0][0] == "http://bedrock"

    event2 = {"body": json.dumps({"prompt": "one two three four", "backend": "ollama"})}
    out2 = module.lambda_handler(event2, {})
    body2 = json.loads(out2["body"])
    assert body2["backend"] == "ollama"
    assert calls[1][0] == "http://ollama"


def test_lambda_handler_strategy(monkeypatch):
    sys.modules["httpx"].HTTPStatusError = type("E", (Exception,), {})
    monkeypatch.setenv("BEDROCK_OPENAI_ENDPOINT", "http://bedrock")
    monkeypatch.setenv("BEDROCK_API_KEY", "key")
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://ollama")
    monkeypatch.setenv("OLLAMA_DEFAULT_MODEL", "phi")
    monkeypatch.setenv("PROMPT_COMPLEXITY_THRESHOLD", "3")

    module = load_lambda("router_lambda_strategy", "services/llm-router/router-lambda/app.py")
    calls = []
    monkeypatch.setattr(module.httpx, "post", _make_fake_post(calls))

    event = {"body": json.dumps({"prompt": "short", "strategy": "complexity"})}
    out = module.lambda_handler(event, {})
    body = json.loads(out["body"])
    assert body["backend"] == "ollama"
    assert calls[0][0] == "http://ollama"
