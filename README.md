# Enterprise AI Services

**Enterprise AI Services** provides a suite of reusable, modular AWS Lambda microservices for a fully serverless AI stack. Each microservice encapsulates a discrete file-centric task—assembling, classifying, processing, compressing, or extracting files—so you can:

- **Rapidly compose** end-to-end AI workflows by wiring together independent Lambda functions  
- **Scale transparently** under variable loads without provisioning or managing servers  
- **Reuse common components** across projects to accelerate development and enforce consistency  
- **Maintain clear separation of concerns**, making each microservice easier to test, update, and deploy  

Whether you’re building on-demand OCR pipelines, metadata-driven classification, vector embedding generators, or ZIP-based packaging utilities, this repository gives you production-ready, serverless building blocks for any AI-powered file workflow.  .

## Overview

The **Enterprise AI Services** project provides a suite of AWS Lambda functions to handle various file-related operations:

- **Assemble** summary and original files  
- **Process** files via OCR and vector embeddings  
- **Classify** files based on metadata or content  
- **Compress** and **extract** ZIP archives  
- **Track** processing status  

Each capability lives in its own directory, fostering a clean, modular structure that’s easy to extend and maintain.

---

## Folder Structure

- **aio-enterprise-ai-services/**
  - **lambda/**
    - **file-assemble/**
      - **app/**  
        - `*.py`  
    - **file-classification/**
      - **app/**  
        - `*.py`  
    - **file-processing-status/**
      - **app/**  
        - `*.py`  
    - **file-processing/**
      - **app/**
        - `*.py`  
    - **zip-processing/**
      - **zip-creation-lambda/app.py**
      - **zip-extract-lambda/app.py**
  - **.github/**
    - **workflows/**
      - `deploy.yml`  
  - `requirements.txt`  
  - `README.md`  
  - …other config files…

---

## Key Features

### 1. File Assembly 
- Combine summary and original PDF files  
- Organize directory structure for downstream processing  

### 2. File Classification 
- Analyze metadata or content fields  
- Trigger AWS Step Functions based on classification rules  

### 3. Processing Status 
- Track workflows: pending → in-progress → completed  
- Emit status updates for monitoring  

### 4. File Processing 
- Extract text from PDFs via OCR  
- Generate embeddings  
- Store embeddings in a vector database  

### 5. ZIP Assembly
- Bundle merged PDFs and metadata into ZIP files for transfer  

### 6. ZIP Extraction
- Unpack ZIP archives
- Save individual files to Amazon S3

### 7. Docling Processing
- Send combined text or PDFs to an external Docling service
- Store structured JSON results for downstream use

### 8. RAG Ingestion & Retrieval
- Chunk text into configurable sizes and overlaps
- Generate embeddings with selectable models
- Store and search embeddings in Milvus
- API endpoints expose summarization and extraction using retrieved context

### 9. Summarization
- Generate context-aware summaries using retrieved text chunks
- Merge the summary pages with the original PDF

---

## Installation 

1. **Clone** the repository  
   ```bash
   git clone https://github.com/ameritascorp/aio-enterprise-ai-services.git
   cd aio-enterprise-ai-services
2. **Install** dependencies
   ```bash
   pip install -r requirements.txt
   
---

## Configuration
### AWS Parameter Store
Open AWS Systems Manager → Parameter Store and create parameters for each
module using the path format:

```
/parameters/aio/ameritasAI/<ENV>/<NAME>
```

where ``<ENV>`` comes from the ``SERVER_ENV`` parameter. Lambdas read their
configuration from these paths at runtime. Ensure the functions have IAM
policies allowing ``ssm:GetParameter``.

### Object Tag Overrides
Configuration values may be overridden per-object by attaching S3 tags. Tags
use the same keys as the Parameter Store names, for example ``OCR_ENGINE`` or
``TEXT_PAGE_PREFIX``. When processing an S3 event the Lambda checks the uploaded
object’s tags first; if no relevant tag is found the value is loaded from
Parameter Store.

…etc.

### OCR Engine Configuration
The PDF OCR extractor supports EasyOCR, PaddleOCR, a remote TrOCR
service and a remote Docling service. Set the ``OCR_ENGINE`` environment
variable to ``"easyocr"`` (default), ``"paddleocr"``, ``"trocr"`` or
``"docling"``. When using TrOCR, specify the endpoint URL via
``TROCR_ENDPOINT``. The Docling engine requires ``DOCLING_ENDPOINT``.  
PaddleOCR may offer better accuracy for some documents but increases
package size.

---

## Git Workflow
   Cloning the Repository
   git clone https://github.com/ameritascorp/aio-enterprise-ai-services.git

### Branch Strategy
- Main (main)
     - Production-ready code only

- Feature Branches
     - Naming: feature/<feature-name>

git checkout -b feature/add-zip-logging 

### Pull Requests
1. Push your feature branch to origin.
2. Open a PR targeting main.
3. Ensure at least one code review approval before merging.

---

## Deployment
This project uses GitHub Actions for CI/CD:

1. **Workflow file**: .github/workflows/deploy.yml

2. On push to main:

- Packages each Lambda function
- Deploys to the configured AWS environment
  - Simply merge your changes into main—the pipeline takes care of the rest.

### Example SAM Deployment

When deploying manually you can point the Lambdas to an EC2 instance running
the TrOCR or Docling services. Pass the URLs as parameter overrides or
environment variables:

```bash
sam deploy \
  --parameter-overrides TROCR_ENDPOINT=http://<EC2-IP>:8000/trocr \
  --stack-name ai-services
```

Set ``DOCLING_ENDPOINT`` in the console or via `sam deploy` to the Docling
service URL, e.g. ``http://<EC2-IP>:8001``.

### Deploying the Vector DB Service
This stack contains the Milvus management and search Lambdas. Provide the
Milvus connection details when deploying:

```bash
sam deploy \
  --template-file services/vector-db/template.yaml \
  --stack-name vector-db \
  --parameter-overrides MilvusHost=<host> MilvusPort=<port> MilvusCollection=<collection>
```

### Deploying the RAG Ingestion Service
The ingestion stack now includes a Step Function that orchestrates `TextChunkFunction`,
`EmbedFunction`, and `MilvusInsertFunction`. New JSON documents emitted by the
IDP pipeline under `TEXT_DOC_PREFIX` trigger this state machine automatically.
The root template passes the IDP bucket name and prefix to the stack. Provide
the ARNs of the vector-db Lambdas when deploying manually:

```bash
sam deploy \
  --template-file services/rag-ingestion/template.yaml \
  --stack-name rag-ingestion \
  --parameter-overrides \ 
    MilvusInsertFunctionArn=<arn> \ 
    MilvusDeleteFunctionArn=<arn> \ 
    MilvusUpdateFunctionArn=<arn> \ 
    MilvusCreateCollectionFunctionArn=<arn> \ 
    MilvusDropCollectionFunctionArn=<arn>
```
If deploying the template by itself, also pass `BucketName` and `TextDocPrefix`
to match your IDP stack.

Configure ``CHUNK_SIZE``, ``CHUNK_OVERLAP`` and ``EMBED_MODEL`` via environment
variables or Parameter Store as needed. ``EMBED_MODEL`` specifies the default
embedding provider (``"sbert"``). Use ``EMBED_MODEL_MAP`` to map document types
to specific models, e.g. ``{"pdf": "openai", "pptx": "cohere"}``.

Set ``SBERT_MODEL`` (via Parameter Store or environment variable) to the
SentenceTransformer model name or path. If the value starts with ``s3://`` it
will be downloaded to ``/tmp`` before loading.

When invoking the embed Lambda include a ``docType`` field in the payload or in
each chunk's metadata so the function can select the appropriate model. Example:

```json
{
  "docType": "pdf",
  "chunks": ["some text"]
}
```

### Deploying the RAG Retrieval Service
Deploy the retrieval Lambdas separately. Provide the ARN of the vector search
Lambda along with the optional API endpoints for summarization and extraction:

```bash
sam deploy \
  --template-file services/rag-retrieval/template.yaml \
  --stack-name rag-retrieval \
  --parameter-overrides VectorSearchFunctionArn=<arn>
```

### Deploying the Summarization Service
This stack orchestrates the end‑to‑end summary workflow:
1. `file-processing` copies PDFs to `IDP_BUCKET/RAW_PREFIX`.
2. The IDP pipeline extracts text to `TEXT_DOC_PREFIX`.
3. New text files start the ingestion state machine (`IngestionStateMachineArn`) to chunk and embed the pages.
4. Once ingestion completes, the summarization state machine calls the RAG retrieval summary Lambda (`RAG_SUMMARY_FUNCTION_ARN`) and merges the output with the original PDF.

Deploy with the required parameters:

```bash
sam deploy \
  --template-file services/summarization/template.yaml \
  --stack-name summarization \
  --parameter-overrides \
    IDPBucketName=<bucket> \
    IDPRawPrefix=<prefix> \
    IngestionStateMachineArn=<arn> \
    RagSummaryFunctionArn=<arn>
```

Ensure Parameter Store keys `IDP_BUCKET`, `RAW_PREFIX` and `TEXT_DOC_PREFIX` exist so the Lambdas can locate the IDP resources.

## LLM Router Service

The router Lambda directs prompts to different Large Language Model back‑ends. It typically sits in front of Amazon Bedrock and a local Ollama instance, choosing a destination based on the prompt length.

### Required environment variables

- `BEDROCK_OPENAI_ENDPOINT` – URL of the Bedrock OpenAI‑compatible endpoint.
- `BEDROCK_API_KEY` – API key used when calling Bedrock.
- `OLLAMA_ENDPOINT` – URL of the local Ollama service.
- `OLLAMA_DEFAULT_MODEL` – model name passed to Ollama when one is not supplied.
- `PROMPT_COMPLEXITY_THRESHOLD` – word count used by the router to decide when to switch from Ollama to Bedrock (defaults to `20`).
- `ROUTELLM_ENDPOINT` – optional URL for forwarding requests to an external RouteLLM router.
- `LLM_INVOCATION_FUNCTION` – name of the Lambda used for actual model invocation.

### Example invocation

```bash
aws lambda invoke \
  --function-name llm-router \
  --payload '{"prompt": "Write a short poem"}' out.json
```

The router counts the words in the prompt. If the count meets or exceeds `PROMPT_COMPLEXITY_THRESHOLD` the request goes to Bedrock, otherwise it is sent to Ollama. Requests may optionally include a `backend` field to force a specific destination (``bedrock`` or ``ollama``). A ``strategy`` field can also be provided for future routing modes. When ``backend`` is not supplied the router falls back to the complexity-based logic. The response always includes a `backend` field indicating which service handled the prompt.

## Documentation

For details on how extracted text should be structured, see [docs/idp_output_format.md](docs/idp_output_format.md).
Additional configuration guidance for the router can be found in [docs/router_configuration.md](docs/router_configuration.md).


   
