# RAG Ingestion Worker

This service provisions an SQS queue and a Lambda function that dequeues
messages to start the RAG ingestion workflow. Each message body is passed
unchanged to the Step Function identified by the ``STATE_MACHINE_ARN``
environment variable.

## Parameters

- ``StateMachineArn`` – ARN of the ingestion Step Function. This value becomes
the ``STATE_MACHINE_ARN`` environment variable for the worker.

## Deployment

Deploy with SAM:

```bash
sam deploy \
  --template-file services/rag-ingestion-worker/template.yaml \
  --stack-name rag-ingestion-worker \
  --parameter-overrides \
    StateMachineArn=<arn>
```
