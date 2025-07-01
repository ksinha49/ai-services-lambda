# Knowledge Base Service

This service provides simple endpoints to ingest text documents into the vector
database and query them using the retrieval stack. It relies on the existing
RAG ingestion and retrieval components. When ingesting documents you may include
metadata fields such as department, team and user. These values are stored with
each chunk and can be used to filter queries.

## Lambdas and API Endpoints

- **ingest-lambda/app.py** – invoked manually or via an API to start the
  ingestion Step Function.
- **query-lambda/app.py** – `/kb/query` endpoint forwarding queries to the
  summarization with context Lambda.

## Parameters

- `IngestionStateMachineArn` – ARN of the ingestion workflow from the
  `rag-ingestion` stack.
- `SummarizeFunctionArn` – ARN of the summary Lambda from the
  `rag-retrieval` stack.
- `KnowledgeBaseName` – optional name tag for the knowledge base.
- Additional request fields include `department`, `team` and `user` which help
  isolate knowledge by organizational unit.

## Deployment

Deploy with SAM:

```bash
sam deploy \
  --template-file services/knowledge-base/template.yaml \
  --stack-name knowledge-base \
  --parameter-overrides \
    IngestionStateMachineArn=<arn> \
    SummarizeFunctionArn=<arn>
```
