import json
import os
import boto3
import httpx
import logging

logger = logging.getLogger(__name__)

s3_client = boto3.client("s3")

BUCKET_NAME = os.environ.get("BUCKET_NAME")
TEXT_DOC_PREFIX = os.environ.get("TEXT_DOC_PREFIX", "text-docs/")
DOCLING_ENDPOINT = os.environ.get("DOCLING_ENDPOINT")

if TEXT_DOC_PREFIX and not TEXT_DOC_PREFIX.endswith("/"):
    TEXT_DOC_PREFIX += "/"


def lambda_handler(event, context):
    for rec in event.get("Records", []):
        bucket = rec.get("s3", {}).get("bucket", {}).get("name")
        key = rec.get("s3", {}).get("object", {}).get("key")
        if bucket != BUCKET_NAME or not key or not key.startswith(TEXT_DOC_PREFIX):
            continue
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        resp = httpx.post(DOCLING_ENDPOINT, content=obj["Body"].read())
        resp.raise_for_status()
        out_key = "docling-results/" + os.path.basename(key)
        s3_client.put_object(
            Bucket=bucket,
            Key=out_key,
            Body=json.dumps(resp.json()).encode("utf-8"),
            ContentType="application/json",
        )
    return {"statusCode": 200, "body": json.dumps({"message": "docling-processor executed"})}
