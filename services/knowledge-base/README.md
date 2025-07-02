# Knowledge Base Service

This service provides simple endpoints to ingest text documents into the vector
database and query them using the retrieval stack. It relies on the existing
RAG ingestion and retrieval components. When ingesting documents you may include
 metadata fields such as department, team and user. These values are stored with
 each chunk and can be used to filter queries. When entity extraction is enabled
 during ingestion, the detected entities are indexed per chunk and can also be
 used as filters when querying.

## Lambdas and API Endpoints

- **ingest-lambda/app.py** – invoked manually or via an API to start the
  ingestion Step Function.
- **query-lambda/app.py** – `/kb/query` endpoint forwarding queries to the
  summarization with context Lambda.

## Parameters

- `IngestionStateMachineArn` – ARN of the ingestion workflow from the
  `rag-ingestion` stack.
- `SummarizeQueueUrl` – URL of the SQS queue consumed by the
  summarization Lambda from the `rag-retrieval` stack.
The query Lambda now publishes requests to this queue so processing happens asynchronously.
 - `KnowledgeBaseName` – optional name tag for the knowledge base.
 - Additional request fields include `department`, `team`, `user` and
   `entities`. These help isolate knowledge by organizational unit or only return
   chunks matching specific entities.

## Deployment

Deploy with SAM:

```bash
sam deploy \
  --template-file services/knowledge-base/template.yaml \
  --stack-name knowledge-base \
  --parameter-overrides \
    IngestionStateMachineArn=<arn> \
    SummarizeQueueUrl=<url>
```
