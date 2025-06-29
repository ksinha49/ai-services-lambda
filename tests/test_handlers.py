import json
import importlib.util
import os
import pytest


def load_lambda(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_office_extractor(monkeypatch, s3_stub, validate_schema):
    monkeypatch.setenv('BUCKET_NAME', 'bucket')
    monkeypatch.setenv('OFFICE_PREFIX', 'office-docs/')
    monkeypatch.setenv('TEXT_DOC_PREFIX', 'text-docs/')
    module = load_lambda('office', 'lambda-functions/2-office-extractor/app.py')

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


def test_pdf_text_extractor(monkeypatch, s3_stub, validate_schema):
    monkeypatch.setenv('BUCKET_NAME', 'bucket')
    monkeypatch.setenv('PDF_TEXT_PAGE_PREFIX', 'text-pages/')
    monkeypatch.setenv('TEXT_PAGE_PREFIX', 'text-pages/')
    module = load_lambda('pdf_text', 'lambda-functions/5-pdf-text-extractor/app.py')

    s3_stub.objects[('bucket', 'text-pages/doc1/page_001.pdf')] = b'data'

    monkeypatch.setattr(module, '_extract_text', lambda b: '## Page 1\n\nhello\n')

    event = {'Records': [{'s3': {'bucket': {'name': 'bucket'}, 'object': {'key': 'text-pages/doc1/page_001.pdf'}}}]}
    module.lambda_handler(event, {})

    md = s3_stub.objects[('bucket', 'text-pages/doc1/page_001.md')].decode()
    schema = {'documentId': 'doc1', 'pageNumber': 1, 'content': md}
    validate_schema(schema)


def test_pdf_ocr_extractor(monkeypatch, s3_stub, validate_schema):
    monkeypatch.setenv('BUCKET_NAME', 'bucket')
    monkeypatch.setenv('PDF_SCAN_PAGE_PREFIX', 'scan-pages/')
    monkeypatch.setenv('TEXT_PAGE_PREFIX', 'text-pages/')
    module = load_lambda('ocr', 'lambda-functions/6-pdf-ocr-extractor/app.py')

    s3_stub.objects[('bucket', 'scan-pages/doc1/page_001.pdf')] = b'data'

    monkeypatch.setattr(module, '_rasterize_page', lambda b, dpi: object())
    monkeypatch.setattr(module, '_ocr_image', lambda img: '## Page 1\n\nocr\n')

    event = {'Records': [{'s3': {'bucket': {'name': 'bucket'}, 'object': {'key': 'scan-pages/doc1/page_001.pdf'}}}]}
    module.lambda_handler(event, {})

    md = s3_stub.objects[('bucket', 'text-pages/doc1/page_001.md')].decode()
    schema = {'documentId': 'doc1', 'pageNumber': 1, 'content': md}
    validate_schema(schema)


def test_combine(monkeypatch, s3_stub, validate_schema):
    monkeypatch.setenv('BUCKET_NAME', 'bucket')
    monkeypatch.setenv('PDF_PAGE_PREFIX', 'pdf-pages/')
    monkeypatch.setenv('TEXT_PAGE_PREFIX', 'text-pages/')
    monkeypatch.setenv('TEXT_DOC_PREFIX', 'text-docs/')
    module = load_lambda('combine', 'lambda-functions/7-combine/app.py')

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


def test_output(monkeypatch, s3_stub, validate_schema):
    monkeypatch.setenv('BUCKET_NAME', 'bucket')
    monkeypatch.setenv('TEXT_DOC_PREFIX', 'text-docs/')
    monkeypatch.setenv('EDI_SEARCH_API_URL', 'http://example')
    monkeypatch.setenv('EDI_SEARCH_API_KEY', 'key')
    module = load_lambda('output', 'lambda-functions/8-output/app.py')

    payload = {'documentId': 'doc1', 'type': 'pdf', 'pageCount': 1, 'pages': ['## Page 1\n\nhi\n']}
    s3_stub.objects[('bucket', 'text-docs/doc1.json')] = json.dumps(payload).encode()

    sent = {}
    monkeypatch.setattr(module, '_post_to_api', lambda data: sent.setdefault('payload', data) or True)

    event = {'Records': [{'s3': {'bucket': {'name': 'bucket'}, 'object': {'key': 'text-docs/doc1.json'}}}]}
    module.lambda_handler(event, {})

    posted = sent['payload']
    assert posted['documentId'] == 'doc1'
    for i, page in enumerate(posted['pages'], start=1):
        validate_schema({'documentId': posted['documentId'], 'pageNumber': i, 'content': page})


def test_ocr_image_engines(monkeypatch):
    monkeypatch.setenv('OCR_ENGINE', 'easyocr')
    monkeypatch.setenv('BUCKET_NAME', 'bucket')
    module = load_lambda('ocr_easy', 'lambda-functions/6-pdf-ocr-extractor/app.py')
    module.easyocr = __import__('easyocr')
    called = {}
    def fake(r, e, b):
        called['engine'] = e
        called['cls'] = r.__class__.__name__
        return 't', 0
    monkeypatch.setattr(module, '_perform_ocr', fake)
    module._ocr_image(object())
    assert called['engine'] == 'easyocr'
    assert called['cls'] == 'DummyReader'

    import types, sys
    class DummyPaddle:
        def __init__(self, *a, **k):
            pass
    sys.modules['paddleocr'] = types.ModuleType('paddleocr')
    sys.modules['paddleocr'].PaddleOCR = DummyPaddle

    monkeypatch.setenv('OCR_ENGINE', 'paddleocr')
    monkeypatch.setenv('BUCKET_NAME', 'bucket')
    module = load_lambda('ocr_paddle', 'lambda-functions/6-pdf-ocr-extractor/app.py')
    module.easyocr = __import__('easyocr')
    called = {}
    def fake2(r, e, b):
        called['engine'] = e
        called['cls'] = r.__class__.__name__
        return 't', 0
    monkeypatch.setattr(module, '_perform_ocr', fake2)
    module._ocr_image(object())
    assert called['engine'] == 'paddleocr'
    assert called['cls'] == 'DummyPaddle'


def test_perform_ocr(monkeypatch):
    import types, sys, importlib.util
    class DummyPaddle:
        def __init__(self, *a, **k):
            pass
        def ocr(self, img):
            return [([[0,0],[1,0],[1,1],[0,1]], ('pd', 0.8))]
    sys.modules['paddleocr'] = types.ModuleType('paddleocr')
    sys.modules['paddleocr'].PaddleOCR = DummyPaddle

    mod = load_lambda('ocr_real', 'layers/ocr_layer/python/ocr_module.py')
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

    with pytest.raises(ValueError):
        mod._perform_ocr(reader, 'other', b'1')
