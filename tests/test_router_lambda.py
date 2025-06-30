import importlib.util
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

    out1 = module.lambda_handler({"prompt": "short"}, {})
    assert out1["backend"] == "ollama"
    assert calls[0][0] == "http://ollama"

    out2 = module.lambda_handler({"prompt": "one two three four"}, {})
    assert out2["backend"] == "bedrock"
    assert calls[1][0] == "http://bedrock"
