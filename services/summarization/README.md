# Summarization Service

This service provides an end‑to‑end workflow that copies a file to the IDP bucket, waits for text extraction, generates summaries and finally merges them back with the original PDF.

The workflow is orchestrated by an AWS Step Function defined in `template.yaml`.  It invokes three Lambdas in this package:

- **file-processing** – copies the uploaded document to `IDP_BUCKET/RAW_PREFIX` so the IDP pipeline can ingest it.
- **file-processing-status** – polls for the text document produced by the IDP pipeline and updates `fileupload_status` in the state machine.
- **file-summary** – receives pre-generated summaries, creates a summary PDF and uploads the merged result to S3.

Details of the state machine, including the parallel `run_prompts` map state, are documented in [docs/summarization_workflow.md](../../docs/summarization_workflow.md).

## Environment variables

The SAM template exposes a few parameters which become environment variables for the Lambdas:

- `IDPBucketName` – name of the IDP bucket.
- `IDPRawPrefix` – prefix within that bucket where the uploaded file is copied.
- `IngestionStateMachineArn` – ARN of the RAG ingestion state machine invoked after the file is available.
- `RagSummaryFunctionArn` – ARN of the RAG retrieval summary Lambda used by `file-summary`.
- `RunPromptsConcurrency` – number of prompts processed in parallel by the `run_prompts` map state.
- `StatusPollSeconds` – number of seconds the Step Function waits before polling for upload status again.
- The service now provisions an SQS queue consumed by a worker Lambda. `RunPromptsConcurrency` controls how many messages are sent in parallel.

Tuning `StatusPollSeconds` controls how frequently the workflow checks for IDP completion.  Lower values reduce latency but increase state machine executions.

## Deployment

Deploy the stack with SAM:

```bash
sam deploy \
  --template-file services/summarization/template.yaml \
  --stack-name summarization \
  --parameter-overrides \
    IDPBucketName=<bucket> \
    IDPRawPrefix=<prefix> \
    IngestionStateMachineArn=<arn> \
    RagSummaryFunctionArn=<arn> \
    RunPromptsConcurrency=10 \
    StatusPollSeconds=200
```

The Step Function definition and Lambda code are located in this directory.  See the root `README.md` for additional context.

## Scaling the Worker

Queued messages are processed by `summarize-worker-lambda`. To increase
throughput raise the Lambda's reserved concurrency or adjust the queue event
batch size in `template.yaml`. Lowering these values reduces concurrency and
costs.

## `collection_name`

Execution inputs must include a ``collection_name`` value when invoking the
summarization service. The state machine propagates this value through each
step so the retrieval service can search the specified Milvus collection.
If ``collection_name`` is omitted, the file-processing Lambda returns a
``400`` response and the Step Function execution fails.
