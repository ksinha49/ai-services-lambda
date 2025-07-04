# Summarization Step Function Workflow

This document describes the multi-step AWS Step Functions state machine that orchestrates the summarization pipeline. The workflow ingests a document, runs a series of prompts in parallel, and generates a merged PDF containing the summaries and original file.

## Map State

The `run_prompts` state uses the [Map](https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-map-state.html) state type to send each prompt to an SQS queue. Worker Lambdas consume these messages, invoke the summarization logic and return the results using task tokens. The summaries are collected in `$.run_prompts`.

Concurrency is controlled via the `MaxConcurrency` field in `template.yaml`:

```yaml
run_prompts:
  Type: Map
  ItemsPath: $.body.prompts
  ResultPath: $.run_prompts
  MaxConcurrency: 10
  Iterator:
    StartAt: summarize
    States:
      summarize:
        Type: Task
        Resource: arn:aws:states:::sqs:sendMessage.waitForTaskToken
        Parameters:
          QueueUrl: <queue-url>
          MessageBody:
            token.$: $$.Task.Token
            query.$: $$Map.Item.Value.query
            Title.$: $$Map.Item.Value.Title
        Next: add_title
      add_title:
        Type: Pass
        Parameters:
          Title.$: $.Title
          content.$: $.summary
        End: true
```

Change the value of `MaxConcurrency` to adjust how many prompts are processed in parallel.

## Providing the Prompts List

The Step Function expects a list of prompt objects under `body.prompts` when the execution starts. Each object should contain at least a `query` string and optional `Title` used by later steps. The list can be supplied in two ways:

1. **Execution input** – Pass the `prompts` array directly in the `StartExecution` payload.
2. **S3 object** – Store the prompts JSON in S3 and include the bucket/key in the input. A Lambda (not shown here) can load the file and inject the array into `body.prompts` before the `Map` state runs.

## Role of `file-summary-lambda`

Previously this Lambda generated the summaries itself. The revised workflow delegates summarization to the `run_prompts` `Map` state. `file-summary-lambda` now receives the pre-generated summaries, builds a summary PDF, and uploads the merged file back to S3.
