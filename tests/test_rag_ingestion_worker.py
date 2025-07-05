import importlib.util
import json
import sys
import types


def _stub_botocore(monkeypatch):
    botocore = types.ModuleType("botocore")
    exc_mod = types.ModuleType("botocore.exceptions")

    class ClientError(Exception):
        pass

    exc_mod.ClientError = ClientError
    botocore.exceptions = exc_mod
    monkeypatch.setitem(sys.modules, "botocore", botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", exc_mod)
    return ClientError


def load_lambda(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_worker_triggers_step_function(monkeypatch, config):
    calls = {}

    _stub_botocore(monkeypatch)

    class FakeSFN:
        def start_execution(self, stateMachineArn=None, input=None):
            calls['arn'] = stateMachineArn
            calls['input'] = json.loads(input)
            return {}

    import boto3
    monkeypatch.setattr(boto3, 'client', lambda name: FakeSFN())
    monkeypatch.setenv('STATE_MACHINE_ARN', 'arn')

    module = load_lambda('worker', 'services/rag-ingestion-worker/worker-lambda/app.py')
    module.sfn = FakeSFN()

    event = {'Records': [{'body': json.dumps({'foo': 'bar'})}]}
    out = module.lambda_handler(event, {})
    assert out['started'] is True
    assert calls['arn'] == 'arn'
    assert calls['input'] == {'foo': 'bar'}
