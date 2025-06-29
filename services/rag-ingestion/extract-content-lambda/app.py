import os
import json
import logging
import boto3
import httpx

from common_utils.get_ssm import get_config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

LAMBDA_FUNCTION = get_config("VECTOR_SEARCH_FUNCTION") or os.environ.get("VECTOR_SEARCH_FUNCTION")
CONTENT_ENDPOINT = get_config("CONTENT_ENDPOINT") or os.environ.get("CONTENT_ENDPOINT")

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
