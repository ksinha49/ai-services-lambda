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

## Queue visibility timeout and DLQ

The SQS queue ``IngestionQueue`` defined in ``template.yaml`` uses a
``VisibilityTimeout`` of **300 seconds**. When a message is delivered to the
worker Lambda it remains invisible to other consumers for five minutes. If the
Lambda fails or times out the message becomes visible again after this period
and is retried.  The stack does not configure a dead-letter queue by default, so
messages that repeatedly fail stay on the main queue until they are processed or
expire.  Add a ``RedrivePolicy`` to ``IngestionQueue`` if you need a DLQ for
poison messages.

## Batch item failure handling

Messages are dequeued one at a time (``BatchSize: 1``).  The handler processes
each record and returns a JSON result. When the Lambda execution fails or raises
an exception the message is returned to the queue and retried after the
visibility timeout.  Because the current implementation catches exceptions and
returns a success response, failed Step Function starts are not automatically
retried. Modify the handler to raise an error or implement the SQS
``batchItemFailures`` response format if retries are required.

## Lambda scaling and environment variables

``STATE_MACHINE_ARN`` is the only environment variable exposed by the stack and
identifies the Step Function to invoke.  The Lambda scales automatically based
on the number of messages in the queue.  Throughput can be tuned by adjusting
the function's reserved concurrency or the queue event source configuration in
``template.yaml``.
