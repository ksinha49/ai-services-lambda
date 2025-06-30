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
    module = load_lambda('invoke', 'services/llm-invocation/invoke-lambda/app.py')

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload
        def json(self):
            return self._payload
        def raise_for_status(self):
            pass

    monkeypatch.setattr(module.httpx, 'post', lambda url, json=None: FakeResponse({'reply': 'ok', 'model': json.get('model')}))
    out = module.lambda_handler({'backend': 'ollama', 'prompt': 'hi'}, {})
    assert out['reply'] == 'ok'
    assert out['model'] == 'phi'


def test_invoke_bedrock_runtime(monkeypatch):
    sys.modules['httpx'].HTTPStatusError = type('E', (Exception,), {})
    monkeypatch.delenv('BEDROCK_OPENAI_ENDPOINT', raising=False)
    module = load_lambda('invoke', 'services/llm-invocation/invoke-lambda/app.py')

    class FakeRuntime:
        def invoke_model(self, body=None, modelId=None):
            data = {'content': {'text': 'resp'}}
            return {'body': io.BytesIO(json.dumps(data).encode())}

    monkeypatch.setattr(module.boto3, 'client', lambda name: FakeRuntime())
    out = module.lambda_handler({'backend': 'bedrock', 'prompt': 'hi', 'model': 'm'}, {})
    assert out['reply'] == 'resp'
