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
    - **zip-assemble/**
      - **app/**
        - `*.py`  
    - **zip-extract/**
      - **app/**
        - `*.py`  
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
Open AWS Systems Manager → Parameter Store.

Create parameters for each module (e.g., API keys, file paths).

Ensure Lambda functions have IAM policies granting ssm:GetParameter.

### Environment Variables
Configure each Lambda function’s environment variables via AWS Console or CLI:

- PARAM_STORE_KEY
- S3_BUCKET_NAME
- VECTOR_DB_ENDPOINT
- DOCLING_ENDPOINT
- TROCR_ENDPOINT

Set ``DOCLING_ENDPOINT`` to the HTTP endpoint of your Docling EC2 service so
that the ``docling-processor`` Lambda can forward documents for analysis or
for the ``docling`` OCR engine to perform recognition remotely.
When using the TrOCR OCR engine, ``TROCR_ENDPOINT`` must point to the remote
TrOCR service URL.

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

## Documentation

For details on how extracted text should be structured, see [docs/idp_output_format.md](docs/idp_output_format.md).


   
