# RAG Retrieval Service

This service exposes three Lambda functions that retrieve text from a vector database and forward the results to downstream APIs for summarization or extraction.

## Lambdas and API Endpoints

- **summarize-with-context-lambda/app.py** – `/summarize`
  - Searches for relevant text, adds it to the prompt and forwards the request through the LLM router.
- **extract-content-lambda/app.py** – `/extract-content`
  - Calls an external content extraction service with the query and retrieved context.
- **extract-entities-lambda/app.py** – `/extract-entities`
  - Sends the query and context to an entity extraction API.

## Environment variables

- `VECTOR_SEARCH_FUNCTION` – ARN or name of the Lambda used for vector search.
- `SUMMARY_ENDPOINT` – optional HTTP endpoint for a summarization service.
- `CONTENT_ENDPOINT` – URL used by `extract-content`.
- `ENTITIES_ENDPOINT` – URL used by `extract-entities`.
- `ROUTELLM_ENDPOINT` – base URL for the LLM router.
- `EMBED_MODEL` – default embedding provider (`sbert` by default).
- `SBERT_MODEL` – SentenceTransformer model name or S3 path.
- `OPENAI_EMBED_MODEL` – embedding model name for OpenAI.
- `COHERE_API_KEY` – API key when using Cohere embeddings.

Values can be stored in Parameter Store and loaded with the shared `get_config` helper.

## Deployment

Deploy the stack with SAM:

```bash
sam deploy \
  --template-file services/rag-retrieval/template.yaml \
  --stack-name rag-retrieval \
  --parameter-overrides \
    VectorSearchFunctionArn=<arn> \
    RouteLlmEndpoint=<router-url> \
    SummaryEndpoint=<summary-url> \
    ContentEndpoint=<content-url> \
    EntitiesEndpoint=<entities-url>
```

The summarization Lambda forwards requests through the LLM router defined by
`ROUTELLM_ENDPOINT`. Configure any router specific variables as described in
[../../docs/router_configuration.md](../../docs/router_configuration.md).
