import importlib.util
import json
import io
import sys


def load_lambda(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_invoke_ollama(monkeypatch):
    sys.modules['httpx'].HTTPStatusError = type('E', (Exception,), {})
    monkeypatch.setenv('OLLAMA_ENDPOINT', 'http://ollama')
    monkeypatch.setenv('OLLAMA_DEFAULT_MODEL', 'phi')
    import importlib, llm_invocation.backends
    importlib.reload(llm_invocation.backends)
    module = load_lambda('invoke', 'services/llm-invocation/invoke-lambda/app.py')

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload
        def json(self):
            return self._payload
        def raise_for_status(self):
            pass

    import llm_invocation.backends as backends
    monkeypatch.setattr(backends.httpx, 'post', lambda url, json=None: FakeResponse({'reply': 'ok', 'model': json.get('model')}))
    out = module.lambda_handler({'backend': 'ollama', 'prompt': 'hi'}, {})
    assert out['reply'] == 'ok'
    assert out['model'] == 'phi'


def test_invoke_bedrock_runtime(monkeypatch):
    sys.modules['httpx'].HTTPStatusError = type('E', (Exception,), {})
    monkeypatch.delenv('BEDROCK_OPENAI_ENDPOINTS', raising=False)
    monkeypatch.delenv('BEDROCK_OPENAI_ENDPOINT', raising=False)
    import importlib, llm_invocation.backends
    importlib.reload(llm_invocation.backends)
    module = load_lambda('invoke', 'services/llm-invocation/invoke-lambda/app.py')

    class FakeRuntime:
        def invoke_model(self, body=None, modelId=None):
            data = {'content': {'text': 'resp'}}
            return {'body': io.BytesIO(json.dumps(data).encode())}

    import llm_invocation.backends as backends
    monkeypatch.setattr(backends.boto3, 'client', lambda name: FakeRuntime())
    out = module.lambda_handler({'backend': 'bedrock', 'prompt': 'hi', 'model': 'm'}, {})
    assert out['reply'] == 'resp'


def test_round_robin_ollama(monkeypatch):
    sys.modules['httpx'].HTTPStatusError = type('E', (Exception,), {})
    monkeypatch.setenv('OLLAMA_ENDPOINTS', 'http://o1,http://o2')
    import importlib, llm_invocation.backends
    importlib.reload(llm_invocation.backends)
    module = load_lambda('invoke', 'services/llm-invocation/invoke-lambda/app.py')

    calls = []

    class FakeResponse:
        def __init__(self, url):
            self.url = url
        def json(self):
            return {'endpoint': self.url}
        def raise_for_status(self):
            pass

    def fake_post(url, json=None):
        calls.append(url)
        return FakeResponse(url)

    import llm_invocation.backends as backends
    monkeypatch.setattr(backends.httpx, 'post', fake_post)
    module.lambda_handler({'backend': 'ollama', 'prompt': 'hi'}, {})
    module.lambda_handler({'backend': 'ollama', 'prompt': 'hi'}, {})
    assert calls[0] != calls[1]


def test_round_robin_bedrock_openai(monkeypatch):
    sys.modules['httpx'].HTTPStatusError = type('E', (Exception,), {})
    monkeypatch.setenv('BEDROCK_OPENAI_ENDPOINTS', 'http://b1,http://b2')
    import importlib, llm_invocation.backends
    importlib.reload(llm_invocation.backends)
    module = load_lambda('invoke', 'services/llm-invocation/invoke-lambda/app.py')

    calls = []

    class FakeResponse:
        def __init__(self, url):
            self.url = url
        def json(self):
            return {'endpoint': self.url}
        def raise_for_status(self):
            pass

    def fake_post(url, json=None, headers=None):
        calls.append(url)
        return FakeResponse(url)

    import llm_invocation.backends as backends2
    monkeypatch.setattr(backends2.httpx, 'post', fake_post)
    module.lambda_handler({'backend': 'bedrock', 'prompt': 'hi'}, {})
    module.lambda_handler({'backend': 'bedrock', 'prompt': 'hi'}, {})
    assert calls[0] != calls[1]
