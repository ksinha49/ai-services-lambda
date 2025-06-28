# AI Services Lambdas

This repository contains a set of AWS Lambda functions, Step Functions and helper layers used to build PDF summaries for uploaded files. The infrastructure is defined using an AWS SAM template.

## Architecture Overview

1. **S3 File Uploads** – Files uploaded to the configured S3 bucket under `landing/ftp/` trigger an EventBridge rule.
2. **SQS Queue** – The rule places a message on a FIFO queue. The `file-classification-lambda` consumes messages from this queue.
3. **Step Functions** – The classification function starts one of two state machines, depending on the uploaded file type:
   - **FileProcessingStepFunction** – Processes a single PDF.
   - **ZipFileProcessingStepFunction** – Extracts PDFs from a ZIP and processes each file.
4. **Processing Lambdas** – The state machines orchestrate the following Lambdas:
   - `file-processing-lambda` – Uploads a PDF to the Ameritas API for processing.
   - `file-processing-status-lambda` – Polls the API until the processing status is complete.
   - `file-summary-lambda` – Calls the summarization service and creates the PDF summary.
   - `file-assemble-lambda` – Merges the summary pages with the original PDF.
   - `zip-extract-lambda` – Extracts PDFs and XML from an uploaded ZIP file.
   - `zip-creation-lambda` – Re‑packages processed files and metadata into a new ZIP.
5. **Notifications** – Failures generate a message via an SNS topic to the email address provided during deployment.

The Lambda code under `lambda-functions/` contains the handlers and each Lambda has its own layer inside `layers/` for dependencies.

## Prerequisites

- **AWS account and credentials** with permission to deploy SAM applications.
- **AWS CLI** and **AWS SAM CLI** installed.
- **Python 3.13** – All functions run on Python 3.13 as defined in the SAM template.

Configure your AWS credentials in the environment (via `aws configure` or environment variables) before running the deployment commands below.

## Deployment

1. Install the required Python packages for each layer:
   ```bash
   sam build
   ```
   This installs dependencies into the layer directories and packages the Lambdas.
2. Deploy the stack using the provided `template.yaml`:
   ```bash
   sam deploy --guided
   ```
   During the guided deployment you will be prompted for parameter values such as subnet IDs, security groups, IAM role ARNs and an email address for notifications. The stack name defaults to `aicoe-ai-services` (see `samconfig.toml`).

After a successful deployment the stack creates the Lambda functions, layers, SQS queue, SNS topic, and the two Step Functions.

## Setting Environment Parameters in SSM

Several Lambdas read configuration values from AWS Systems Manager Parameter Store. Before running the workflow you must populate these parameters. The general pattern is:

1. Set the environment name used by all functions:
   ```bash
   aws ssm put-parameter --name /parameters/aio/ameritasAI/SERVER_ENV --value dev --type String
   ```
   Replace `dev` with your environment identifier (for example `prod`).
2. Create parameters under `/parameters/aio/ameritasAI/<ENV>` for API endpoints and credentials. Example:
   ```bash
   PREFIX=/parameters/aio/ameritasAI/dev
   aws ssm put-parameter --name "$PREFIX/STEP_FUNCTION_ARN" --value <state-machine-arn> --type String
   aws ssm put-parameter --name "$PREFIX/FILE_PROCESSING_FUNCTIONAL_USER" --value <username> --type String
   aws ssm put-parameter --name "$PREFIX/AMERITAS_CHAT_TOKEN_URL" --value <token-url> --type String
   aws ssm put-parameter --name "$PREFIX/AMERITAS_CHAT_FILE_UPLOAD_URL" --value <upload-url> --type String
   aws ssm put-parameter --name "$PREFIX/AMERITAS_CHAT_FILESTTAUS_URL" --value <status-url> --type String
   aws ssm put-parameter --name "$PREFIX/AMERITAS_CHAT_SUMMARIZATION_URL" --value <summary-url> --type String
   aws ssm put-parameter --name "$PREFIX/AMERITAS_CHAT_SUMMARY_MODEL" --value <model-id> --type String
   aws ssm put-parameter --name "$PREFIX/SUMMARY_PDF_FONT_SIZE" --value "10" --type String
   aws ssm put-parameter --name "$PREFIX/SUMMARY_PDF_FONT_SIZE_BOLD" --value "12" --type String
   ```
   Provide values appropriate for your environment. These parameters are read by the Lambdas at runtime.

Once the parameters are in place and the SAM stack is deployed, uploading a PDF or ZIP file to the configured S3 location will start the processing workflow automatically.

