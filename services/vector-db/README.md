# Vector DB Service

This service manages Milvus collections and provides simple search Lambdas. It consists of the following functions:

- **milvus-create-lambda/app.py** – create a Milvus collection if it does not exist
- **milvus-drop-lambda/app.py** – drop the current Milvus collection
- **milvus-insert-lambda/app.py** – insert embeddings into the collection
- **milvus-delete-lambda/app.py** – delete embeddings by ID
- **milvus-update-lambda/app.py** – update existing embeddings
- **vector-search-lambda/app.py** – query the collection by vector
- **hybrid-search-lambda/app.py** – vector search with optional keyword filtering

## Parameters and environment variables

`template.yaml` exposes three required parameters. Each one becomes an environment variable for all Lambdas in this stack:

| Parameter        | Environment variable | Description                  |
| ---------------- | -------------------- | ---------------------------- |
| `MilvusHost`     | `MILVUS_HOST`        | Milvus server hostname or IP |
| `MilvusPort`     | `MILVUS_PORT`        | Milvus service port          |
| `MilvusCollection` | `MILVUS_COLLECTION` | Target collection name       |

Values are typically stored in AWS Systems Manager Parameter Store and passed to `sam deploy`.

## Deployment

Deploy the stack with SAM:

```bash
sam deploy --template-file services/vector-db/template.yaml
```

## Outputs

The stack exports the ARNs of both search functions:

- `VectorSearchFunctionArn` – ARN of the vector search Lambda
- `HybridSearchFunctionArn` – ARN of the hybrid search Lambda

These values are referenced by other services. For example, `rag-retrieval`
sets the `VECTOR_SEARCH_FUNCTION` environment variable to one of these ARNs to
toggle between pure vector search and hybrid search.
