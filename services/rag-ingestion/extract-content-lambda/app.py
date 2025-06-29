import os
import json
import boto3
import httpx

LAMBDA_FUNCTION = os.environ.get("VECTOR_SEARCH_FUNCTION")
CONTENT_ENDPOINT = os.environ.get("CONTENT_ENDPOINT")

lambda_client = boto3.client("lambda")


def lambda_handler(event, context):
    query = event.get("query")
    emb = event.get("embedding")
    resp = lambda_client.invoke(FunctionName=LAMBDA_FUNCTION, Payload=json.dumps({"embedding": emb}).encode("utf-8"))
    result = json.loads(resp["Payload"].read())
    context_text = " ".join(m.get("metadata", {}).get("text", "") for m in result.get("matches", []))
    r = httpx.post(CONTENT_ENDPOINT, json={"query": query, "context": context_text})
    r.raise_for_status()
    return {"content": r.json()}
