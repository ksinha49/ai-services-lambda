import json
import importlib.util
import os
import pytest


def load_lambda(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_office_extractor(monkeypatch, s3_stub, validate_schema, config):
    prefix = '/parameters/aio/ameritasAI/dev'
    config['/parameters/aio/ameritasAI/SERVER_ENV'] = 'dev'
    config[f'{prefix}/BUCKET_NAME'] = 'bucket'
    config[f'{prefix}/OFFICE_PREFIX'] = 'office-docs/'
    config[f'{prefix}/TEXT_DOC_PREFIX'] = 'text-docs/'
    module = load_lambda('office', 'services/idp/2-office-extractor/app.py')

    s3_stub.objects[('bucket', 'office-docs/test.docx')] = b'data'

    monkeypatch.setattr(module, '_extract_docx', lambda b: ['## Page 1\n\ntext\n'])
    monkeypatch.setattr(module, '_extract_pptx', lambda b: ['## Page 1\n\ntext\n'])
    monkeypatch.setattr(module, '_extract_xlsx', lambda b: ['## Page 1\n\ntext\n'])

    event = {'Records': [{'s3': {'bucket': {'name': 'bucket'}, 'object': {'key': 'office-docs/test.docx'}}}]}
    module.lambda_handler(event, {})

    out_key = 'text-docs/test.json'
    payload = json.loads(s3_stub.objects[('bucket', out_key)].decode())
    assert payload['documentId'] == 'test'
    assert payload['pageCount'] == 1
    page = {'documentId': payload['documentId'], 'pageNumber': 1, 'content': payload['pages'][0]}
    validate_schema(page)


def test_pdf_text_extractor(monkeypatch, s3_stub, validate_schema, config):
    prefix = '/parameters/aio/ameritasAI/dev'
    config['/parameters/aio/ameritasAI/SERVER_ENV'] = 'dev'
    config[f'{prefix}/BUCKET_NAME'] = 'bucket'
    config[f'{prefix}/PDF_TEXT_PAGE_PREFIX'] = 'text-pages/'
    config[f'{prefix}/TEXT_PAGE_PREFIX'] = 'text-pages/'
    module = load_lambda('pdf_text', 'services/idp/5-pdf-text-extractor/app.py')

    s3_stub.objects[('bucket', 'text-pages/doc1/page_001.pdf')] = b'data'

    monkeypatch.setattr(module, '_extract_text', lambda b: '## Page 1\n\nhello\n')

    event = {'Records': [{'s3': {'bucket': {'name': 'bucket'}, 'object': {'key': 'text-pages/doc1/page_001.pdf'}}}]}
    module.lambda_handler(event, {})

    md = s3_stub.objects[('bucket', 'text-pages/doc1/page_001.md')].decode()
    schema = {'documentId': 'doc1', 'pageNumber': 1, 'content': md}
    validate_schema(schema)


def test_pdf_ocr_extractor(monkeypatch, s3_stub, validate_schema, config):
    prefix = '/parameters/aio/ameritasAI/dev'
    config['/parameters/aio/ameritasAI/SERVER_ENV'] = 'dev'
    config[f'{prefix}/BUCKET_NAME'] = 'bucket'
    config[f'{prefix}/PDF_SCAN_PAGE_PREFIX'] = 'scan-pages/'
    config[f'{prefix}/TEXT_PAGE_PREFIX'] = 'text-pages/'
    module = load_lambda('ocr', 'services/idp/6-pdf-ocr-extractor/app.py')

    s3_stub.objects[('bucket', 'scan-pages/doc1/page_001.pdf')] = b'data'

    monkeypatch.setattr(module, '_rasterize_page', lambda b, dpi: object())
    monkeypatch.setattr(module, '_ocr_image', lambda img, e, t, d: '## Page 1\n\nocr\n')

    event = {'Records': [{'s3': {'bucket': {'name': 'bucket'}, 'object': {'key': 'scan-pages/doc1/page_001.pdf'}}}]}
    module.lambda_handler(event, {})

    md = s3_stub.objects[('bucket', 'text-pages/doc1/page_001.md')].decode()
    schema = {'documentId': 'doc1', 'pageNumber': 1, 'content': md}
    validate_schema(schema)


def test_pdf_ocr_extractor_trocr(monkeypatch, s3_stub, validate_schema, config):
    prefix = '/parameters/aio/ameritasAI/dev'
    config['/parameters/aio/ameritasAI/SERVER_ENV'] = 'dev'
    config[f'{prefix}/BUCKET_NAME'] = 'bucket'
    config[f'{prefix}/PDF_SCAN_PAGE_PREFIX'] = 'scan-pages/'
    config[f'{prefix}/TEXT_PAGE_PREFIX'] = 'text-pages/'
    config[f'{prefix}/OCR_ENGINE'] = 'trocr'
    config[f'{prefix}/TROCR_ENDPOINT'] = 'http://example'
    module = load_lambda('ocr_trocr', 'services/idp/6-pdf-ocr-extractor/app.py')

    s3_stub.objects[('bucket', 'scan-pages/doc1/page_001.pdf')] = b'data'

    monkeypatch.setattr(module, '_rasterize_page', lambda b, dpi: object())
    called = {}
    def fake(reader, engine, img):
        called['engine'] = engine
        return 'ocr', 0.9
    monkeypatch.setattr(module, '_perform_ocr', fake)

    event = {'Records': [{'s3': {'bucket': {'name': 'bucket'}, 'object': {'key': 'scan-pages/doc1/page_001.pdf'}}}]}
    module.lambda_handler(event, {})

    md = s3_stub.objects[('bucket', 'text-pages/doc1/page_001.md')].decode()
    assert called['engine'] == 'trocr'
    schema = {'documentId': 'doc1', 'pageNumber': 1, 'content': md}
    validate_schema(schema)


def test_pdf_ocr_extractor_docling(monkeypatch, s3_stub, validate_schema, config):
    prefix = '/parameters/aio/ameritasAI/dev'
    config['/parameters/aio/ameritasAI/SERVER_ENV'] = 'dev'
    config[f'{prefix}/BUCKET_NAME'] = 'bucket'
    config[f'{prefix}/PDF_SCAN_PAGE_PREFIX'] = 'scan-pages/'
    config[f'{prefix}/TEXT_PAGE_PREFIX'] = 'text-pages/'
    config[f'{prefix}/OCR_ENGINE'] = 'docling'
    config[f'{prefix}/DOCLING_ENDPOINT'] = 'http://example'
    module = load_lambda('ocr_docling', 'services/idp/6-pdf-ocr-extractor/app.py')

    s3_stub.objects[('bucket', 'scan-pages/doc1/page_001.pdf')] = b'data'

    monkeypatch.setattr(module, '_rasterize_page', lambda b, dpi: object())
    called = {}
    def fake(reader, engine, img):
        called['engine'] = engine
        return 'ocr', 0.9
    monkeypatch.setattr(module, '_perform_ocr', fake)

    event = {'Records': [{'s3': {'bucket': {'name': 'bucket'}, 'object': {'key': 'scan-pages/doc1/page_001.pdf'}}}]}
    module.lambda_handler(event, {})

    md = s3_stub.objects[('bucket', 'text-pages/doc1/page_001.md')].decode()
    assert called['engine'] == 'docling'
    schema = {'documentId': 'doc1', 'pageNumber': 1, 'content': md}
    validate_schema(schema)


def test_combine(monkeypatch, s3_stub, validate_schema, config):
    prefix = '/parameters/aio/ameritasAI/dev'
    config['/parameters/aio/ameritasAI/SERVER_ENV'] = 'dev'
    config[f'{prefix}/BUCKET_NAME'] = 'bucket'
    config[f'{prefix}/PDF_PAGE_PREFIX'] = 'pdf-pages/'
    config[f'{prefix}/TEXT_PAGE_PREFIX'] = 'text-pages/'
    config[f'{prefix}/TEXT_DOC_PREFIX'] = 'text-docs/'
    module = load_lambda('combine', 'services/idp/7-combine/app.py')

    s3_stub.objects[('bucket', 'pdf-pages/doc1/manifest.json')] = json.dumps({'documentId': 'doc1', 'pages': 2}).encode()
    s3_stub.objects[('bucket', 'text-pages/doc1/page_001.md')] = b'## Page 1\n\none\n'
    s3_stub.objects[('bucket', 'text-pages/doc1/page_002.md')] = b'## Page 2\n\ntwo\n'

    event = {'Records': [{'s3': {'bucket': {'name': 'bucket'}, 'object': {'key': 'text-pages/doc1/page_001.md'}}}]}
    module.lambda_handler(event, {})

    output = json.loads(s3_stub.objects[('bucket', 'text-docs/doc1.json')].decode())
    assert output['documentId'] == 'doc1'
    assert output['pageCount'] == 2
    for i, page in enumerate(output['pages'], start=1):
        validate_schema({'documentId': output['documentId'], 'pageNumber': i, 'content': page})


def test_output(monkeypatch, s3_stub, validate_schema, config):
    prefix = '/parameters/aio/ameritasAI/dev'
    config['/parameters/aio/ameritasAI/SERVER_ENV'] = 'dev'
    config[f'{prefix}/BUCKET_NAME'] = 'bucket'
    config[f'{prefix}/TEXT_DOC_PREFIX'] = 'text-docs/'
    config[f'{prefix}/EDI_SEARCH_API_URL'] = 'http://example'
    config[f'{prefix}/EDI_SEARCH_API_KEY'] = 'key'
    module = load_lambda('output', 'services/idp/8-output/app.py')

    payload = {'documentId': 'doc1', 'type': 'pdf', 'pageCount': 1, 'pages': ['## Page 1\n\nhi\n']}
    s3_stub.objects[('bucket', 'text-docs/doc1.json')] = json.dumps(payload).encode()

    sent = {}
    monkeypatch.setattr(module, '_post_to_api', lambda data, url, key: sent.setdefault('payload', data) or True)

    event = {'Records': [{'s3': {'bucket': {'name': 'bucket'}, 'object': {'key': 'text-docs/doc1.json'}}}]}
    module.lambda_handler(event, {})

    posted = sent['payload']
    assert posted['documentId'] == 'doc1'
    for i, page in enumerate(posted['pages'], start=1):
        validate_schema({'documentId': posted['documentId'], 'pageNumber': i, 'content': page})


def test_ocr_image_engines(monkeypatch, config):
    prefix = '/parameters/aio/ameritasAI/dev'
    config['/parameters/aio/ameritasAI/SERVER_ENV'] = 'dev'
    config[f'{prefix}/BUCKET_NAME'] = 'bucket'
    config[f'{prefix}/OCR_ENGINE'] = 'easyocr'
    module = load_lambda('ocr_easy', 'services/idp/6-pdf-ocr-extractor/app.py')
    module.easyocr = __import__('easyocr')
    called = {}
    def fake(r, e, b):
        called['engine'] = e
        called['cls'] = r.__class__.__name__
        return 't', 0
    monkeypatch.setattr(module, '_perform_ocr', fake)
    module._ocr_image(object(), 'easyocr', None, None)
    assert called['engine'] == 'easyocr'
    assert called['cls'] == 'DummyReader'

    import types, sys
    class DummyPaddle:
        def __init__(self, *a, **k):
            pass
    sys.modules['paddleocr'] = types.ModuleType('paddleocr')
    sys.modules['paddleocr'].PaddleOCR = DummyPaddle

    config[f'{prefix}/OCR_ENGINE'] = 'paddleocr'
    module = load_lambda('ocr_paddle', 'services/idp/6-pdf-ocr-extractor/app.py')
    module.easyocr = __import__('easyocr')
    called = {}
    def fake2(r, e, b):
        called['engine'] = e
        called['cls'] = r.__class__.__name__
        return 't', 0
    monkeypatch.setattr(module, '_perform_ocr', fake2)
    module._ocr_image(object(), 'paddleocr', None, None)
    assert called['engine'] == 'paddleocr'
    assert called['cls'] == 'DummyPaddle'

    config[f'{prefix}/OCR_ENGINE'] = 'trocr'
    config[f'{prefix}/TROCR_ENDPOINT'] = 'http://example'
    module = load_lambda('ocr_trocr_engine', 'services/idp/6-pdf-ocr-extractor/app.py')
    called = {}
    def fake3(r, e, b):
        called['engine'] = e
        called['ctx'] = r
        return 't', 0
    monkeypatch.setattr(module, '_perform_ocr', fake3)
    module._ocr_image(object(), 'trocr', 'http://example', None)
    assert called['engine'] == 'trocr'
    assert called['ctx'] == 'http://example'

    config[f'{prefix}/OCR_ENGINE'] = 'docling'
    config[f'{prefix}/DOCLING_ENDPOINT'] = 'http://example'
    module = load_lambda('ocr_docling_engine', 'services/idp/6-pdf-ocr-extractor/app.py')
    called = {}
    def fake4(r, e, b):
        called['engine'] = e
        called['ctx'] = r
        return 't', 0
    monkeypatch.setattr(module, '_perform_ocr', fake4)
    module._ocr_image(object(), 'docling', None, 'http://example')
    assert called['engine'] == 'docling'
    assert called['ctx'] == 'http://example'


def test_perform_ocr(monkeypatch):
    import types, sys, importlib.util
    class DummyPaddle:
        def __init__(self, *a, **k):
            pass
        def ocr(self, img):
            return [([[0,0],[1,0],[1,1],[0,1]], ('pd', 0.8))]
    sys.modules['paddleocr'] = types.ModuleType('paddleocr')
    sys.modules['paddleocr'].PaddleOCR = DummyPaddle

    mod = load_lambda('ocr_real', 'common/layers/ocr_layer/python/ocr_module.py')
    monkeypatch.setattr(mod, 'preprocess_image_cv2', lambda b: 'img')
    monkeypatch.setattr(mod, '_results_to_layout_text', lambda res: 'layout')
    monkeypatch.setattr(mod.np, 'mean', lambda x: sum(x)/len(x))

    reader = mod.easyocr.Reader()
    text, conf = mod._perform_ocr(reader, 'easyocr', b'1')
    assert text == 'layout'
    assert conf == 0.9

    pd = DummyPaddle()
    text, conf = mod._perform_ocr(pd, 'paddleocr', b'1')
    assert text == 'layout'
    assert conf == 0.8

    monkeypatch.setattr(mod, '_remote_trocr', lambda b, url: ('layout', 0.7))
    monkeypatch.setenv('TROCR_ENDPOINT', 'http://example')
    text, conf = mod._perform_ocr(None, 'trocr', b'1')
    assert text == 'layout'
    assert conf == 0.7

    monkeypatch.setattr(mod, '_remote_docling', lambda b, url: ('layout', 0.6))
    monkeypatch.setenv('DOCLING_ENDPOINT', 'http://example')
    text, conf = mod._perform_ocr(None, 'docling', b'1')
    assert text == 'layout'
    assert conf == 0.6

    with pytest.raises(ValueError):
        mod._perform_ocr(reader, 'other', b'1')



def test_embed_model_map_event(monkeypatch, config):
    monkeypatch.setenv('EMBED_MODEL', 'sbert')
    monkeypatch.setenv('EMBED_MODEL_MAP', '{"pdf": "openai"}')
    config['/parameters/aio/ameritasAI/SERVER_ENV'] = 'dev'
    module = load_lambda('embed_event', 'services/rag-ingestion/embed-lambda/app.py')
    monkeypatch.setattr(module, '_openai_embed', lambda t: [42])
    module._MODEL_MAP['openai'] = module._openai_embed
    out = module.lambda_handler({'chunks': ['t'], 'docType': 'pdf'}, {})
    assert out['embeddings'] == [[42]]


def test_embed_model_map_chunk(monkeypatch, config):
    monkeypatch.setenv('EMBED_MODEL', 'sbert')
    monkeypatch.setenv('EMBED_MODEL_MAP', '{"pptx": "cohere"}')
    config['/parameters/aio/ameritasAI/SERVER_ENV'] = 'dev'
    module = load_lambda('embed_chunk', 'services/rag-ingestion/embed-lambda/app.py')
    monkeypatch.setattr(module, '_cohere_embed', lambda t: [24])
    module._MODEL_MAP['cohere'] = module._cohere_embed
    chunk = {'text': 'hi', 'metadata': {'docType': 'pptx'}}
    out = module.lambda_handler({'chunks': [chunk]}, {})
    assert out['embeddings'] == [[24]]


def test_embed_model_default(monkeypatch, config):
    monkeypatch.setenv('EMBED_MODEL', 'cohere')
    monkeypatch.setenv('EMBED_MODEL_MAP', '{"pdf": "openai"}')
    config['/parameters/aio/ameritasAI/SERVER_ENV'] = 'dev'
    module = load_lambda('embed_default', 'services/rag-ingestion/embed-lambda/app.py')
    monkeypatch.setattr(module, '_cohere_embed', lambda t: [7])
    module._MODEL_MAP['cohere'] = module._cohere_embed
    out = module.lambda_handler({'chunks': ['x'], 'docType': 'txt'}, {})
    assert out['embeddings'] == [[7]]


def test_text_chunk_doc_type(monkeypatch, config):
    config['/parameters/aio/ameritasAI/SERVER_ENV'] = 'dev'
    module = load_lambda('chunk', 'services/rag-ingestion/text-chunk-lambda/app.py')
    event = {'text': 'abcdef', 'docType': 'pdf'}
    result = module.lambda_handler(event, {})
    assert result['docType'] == 'pdf'
    assert result['chunks']


def test_milvus_delete_lambda(monkeypatch):
    import types, sys
    dummy = types.ModuleType('pymilvus')
    dummy.Collection = type('Coll', (), {'__init__': lambda self, *a, **k: None, 'delete': lambda self, expr: types.SimpleNamespace(delete_count=2)})
    dummy.connections = types.SimpleNamespace(connect=lambda alias, host, port: None)
    monkeypatch.setitem(sys.modules, 'pymilvus', dummy)
    import common_utils.milvus_client as mc
    monkeypatch.setattr(mc, 'Collection', dummy.Collection, raising=False)
    monkeypatch.setattr(mc, 'connections', dummy.connections, raising=False)

    module = load_lambda('milvus_delete', 'services/vector-db/milvus-delete-lambda/app.py')
    called = {}
    def fake_delete(self, ids):
        called['ids'] = list(ids)
        return len(called['ids'])

    monkeypatch.setattr(module, 'client', type('C', (), {'delete': fake_delete})())
    res = module.lambda_handler({'ids': [1, 2]}, {})
    assert called['ids'] == [1, 2]
    assert res['deleted'] == 2


def test_milvus_update_lambda(monkeypatch):
    import types, sys
    dummy = types.ModuleType('pymilvus')
    dummy.Collection = type('Coll', (), {'__init__': lambda self, *a, **k: None})
    dummy.connections = types.SimpleNamespace(connect=lambda alias, host, port: None)
    monkeypatch.setitem(sys.modules, 'pymilvus', dummy)
    import common_utils.milvus_client as mc
    monkeypatch.setattr(mc, 'Collection', dummy.Collection, raising=False)
    monkeypatch.setattr(mc, 'connections', dummy.connections, raising=False)

    module = load_lambda('milvus_update', 'services/vector-db/milvus-update-lambda/app.py')
    received = {}

    def fake_update(items):
        received['items'] = items
        return len(items)

    monkeypatch.setattr(module, 'client', type('C', (), {'update': lambda self, items: fake_update(items)})())
    event = {'embeddings': [[0.1, 0.2]], 'metadatas': [{'a': 1}], 'ids': [5]}
    res = module.lambda_handler(event, {})
    assert len(received['items']) == 1
    item = received['items'][0]
    assert item.embedding == [0.1, 0.2]
    assert item.metadata == {'a': 1}
    assert item.id == 5
    assert res['updated'] == 1


def test_milvus_create_lambda(monkeypatch):
    import types, sys
    dummy = types.ModuleType('pymilvus')
    dummy.FieldSchema = lambda *a, **k: None
    dummy.CollectionSchema = lambda *a, **k: None
    dummy.DataType = types.SimpleNamespace(INT64=0, FLOAT_VECTOR=1, JSON=2)
    dummy.Collection = type('Coll', (), {'__init__': lambda self, *a, **k: None, 'create_index': lambda *a, **k: None})
    dummy.connections = types.SimpleNamespace(connect=lambda alias, host, port: None)
    monkeypatch.setitem(sys.modules, 'pymilvus', dummy)
    import common_utils.milvus_client as mc
    monkeypatch.setattr(mc, 'Collection', dummy.Collection, raising=False)
    monkeypatch.setattr(mc, 'connections', dummy.connections, raising=False)
    monkeypatch.setattr(mc, 'FieldSchema', dummy.FieldSchema, raising=False)
    monkeypatch.setattr(mc, 'CollectionSchema', dummy.CollectionSchema, raising=False)
    monkeypatch.setattr(mc, 'DataType', dummy.DataType, raising=False)

    module = load_lambda('milvus_create', 'services/vector-db/milvus-create-lambda/app.py')
    called = {}
    monkeypatch.setattr(module, 'client', type('C', (), {'create_collection': lambda self, dimension=768: called.setdefault('dimension', dimension)})())
    res = module.lambda_handler({'dimension': 42}, {})
    assert called['dimension'] == 42
    assert res['created'] is True


def test_milvus_drop_lambda(monkeypatch):
    import types, sys
    dummy = types.ModuleType('pymilvus')
    dummy.Collection = type('Coll', (), {'__init__': lambda self, *a, **k: None, 'drop': lambda self: None})
    dummy.connections = types.SimpleNamespace(connect=lambda alias, host, port: None)
    monkeypatch.setitem(sys.modules, 'pymilvus', dummy)
    import common_utils.milvus_client as mc
    monkeypatch.setattr(mc, 'Collection', dummy.Collection, raising=False)
    monkeypatch.setattr(mc, 'connections', dummy.connections, raising=False)

    module = load_lambda('milvus_drop', 'services/vector-db/milvus-drop-lambda/app.py')
    called = {'dropped': False}

    def fake_drop():
        called['dropped'] = True

    monkeypatch.setattr(module, 'client', type('C', (), {'drop_collection': lambda self: fake_drop()})())
    res = module.lambda_handler({}, {})
    assert called['dropped'] is True
    assert res['dropped'] is True

import sys

def test_llm_router_choose_backend(monkeypatch):
    import sys
    sys.modules["httpx"].HTTPStatusError = type("E", (Exception,), {})
    monkeypatch.setenv("PROMPT_COMPLEXITY_THRESHOLD", "3")
    module = load_lambda('llm_router_app', 'services/llm-router/router-lambda/app.py')
    assert module._choose_backend('one two') == 'ollama'
    assert module._choose_backend('one two three four') == 'bedrock'


def test_llm_router_lambda_handler(monkeypatch):
    import sys
    sys.modules["httpx"].HTTPStatusError = type("E", (Exception,), {})
    monkeypatch.setenv('BEDROCK_OPENAI_ENDPOINT', 'http://bedrock')
    monkeypatch.setenv('BEDROCK_API_KEY', 'key')
    monkeypatch.setenv('OLLAMA_ENDPOINT', 'http://ollama')
    monkeypatch.setenv('OLLAMA_DEFAULT_MODEL', 'phi')
    monkeypatch.setenv('PROMPT_COMPLEXITY_THRESHOLD', '3')
    module = load_lambda('llm_router_lambda', 'services/llm-router/router-lambda/app.py')

    class FakeResponse:
        def __init__(self, data):
            self._data = data
        def json(self):
            return self._data
        def raise_for_status(self):
            pass

    calls = []
    def fake_post(url, json=None, headers=None):
        calls.append((url, json, headers))
        if url == 'http://bedrock':
            return FakeResponse({'reply': 'bedrock'})
        elif url == 'http://ollama':
            return FakeResponse({'reply': 'ollama'})
        raise ValueError('unexpected url')

    monkeypatch.setattr(module.httpx, 'post', fake_post)

    out1 = module.lambda_handler({'prompt': 'short text'}, {})
    assert out1['backend'] == 'ollama'
    assert out1['reply'] == 'ollama'
    assert calls[0][0] == 'http://ollama'
    assert calls[0][1]['model'] == 'phi'
    assert 'Authorization' not in calls[0][2]

    out2 = module.lambda_handler({'prompt': 'one two three four'}, {})
    assert out2['backend'] == 'bedrock'
    assert out2['reply'] == 'bedrock'
    assert calls[1][0] == 'http://bedrock'
    assert 'model' not in calls[1][1]
    assert calls[1][2]['Authorization'] == 'Bearer key'


def test_llm_router_choose_backend_default(monkeypatch):
    import sys
    sys.modules["httpx"].HTTPStatusError = type("E", (Exception,), {})
    monkeypatch.delenv("PROMPT_COMPLEXITY_THRESHOLD", raising=False)
    module = load_lambda('llm_router_app_default', 'services/llm-router/router-lambda/app.py')
    short_prompt = ' '.join(['w'] * 5)
    long_prompt = ' '.join(['w'] * 25)
    assert module._choose_backend(short_prompt) == 'ollama'
    assert module._choose_backend(long_prompt) == 'bedrock'


def test_llm_router_lambda_handler_default(monkeypatch):
    import sys
    sys.modules["httpx"].HTTPStatusError = type("E", (Exception,), {})
    monkeypatch.setenv('BEDROCK_OPENAI_ENDPOINT', 'http://bedrock')
    monkeypatch.setenv('BEDROCK_API_KEY', 'key')
    monkeypatch.setenv('OLLAMA_ENDPOINT', 'http://ollama')
    monkeypatch.setenv('OLLAMA_DEFAULT_MODEL', 'phi')
    monkeypatch.delenv('PROMPT_COMPLEXITY_THRESHOLD', raising=False)
    module = load_lambda('llm_router_lambda_default', 'services/llm-router/router-lambda/app.py')

    class FakeResponse:
        def __init__(self, data):
            self._data = data
        def json(self):
            return self._data
        def raise_for_status(self):
            pass

    calls = []
    def fake_post(url, json=None, headers=None):
        calls.append((url, json, headers))
        if url == 'http://bedrock':
            return FakeResponse({'reply': 'bedrock'})
        elif url == 'http://ollama':
            return FakeResponse({'reply': 'ollama'})
        raise ValueError('unexpected url')

    monkeypatch.setattr(module.httpx, 'post', fake_post)

    out1 = module.lambda_handler({'prompt': 'short text'}, {})
    assert out1['backend'] == 'ollama'
    assert calls[0][0] == 'http://ollama'

    long_prompt = ' '.join(['w'] * 25)
    out2 = module.lambda_handler({'prompt': long_prompt}, {})
    assert out2['backend'] == 'bedrock'
    assert calls[1][0] == 'http://bedrock'
