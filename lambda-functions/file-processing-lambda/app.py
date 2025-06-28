# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""
Module: app.py
Description:
  1. Retrieves SSM parameters using a proxy configuration.
  2. Gets an authentication token from Ameritas' API.
  3. Invokes the file processing API to upload files to Ameritas' system.

Version: 1.0.2
Created: 2025-05-05
Last Modified: 2025-06-28
Modified By: Koushik Sinha
"""

from __future__ import annotations
import boto3
import httpx
from httpx import Timeout, HTTPError, TimeoutException
import logging
from botocore.config import Config
import json
from io import BytesIO
from common_utils.get_ssm import (
    get_values_from_ssm,
    get_environment_prefix,
    parse_s3_uri,
)

# Module Metadata
__author__ = "Balakrishna"
__version__ = "1.0.2"
__modified_by__ = "Koushik Sinha"

# ─── Logging Configuration ─────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

client_cert = "AMERITASISSUING1-CA.crt"
_s3_client = boto3.client("s3")

def get_token() -> dict:
    """
    Retrieves an authentication token from Ameritas' API.

    Returns:
        dict: The JSON response from the API, or an empty dictionary if it fails.
    """
    timeout = Timeout(timeout=10)
    headers = {'Content-type': 'application/json'}
    functional_user = get_values_from_ssm(f"{get_environment_prefix()}/FILE_PROCESSING_FUNCTIONAL_USER")
    try:
        # Construct the token URL
        token_url = get_values_from_ssm(f"{get_environment_prefix()}/AMERITAS_CHAT_TOKEN_URL")
        token_url = f"{token_url}?userId={functional_user}"
        headers = {'Content-type': 'application/json'}
        response = httpx.post(
            token_url,
            json={},
            timeout=timeout,                              
            headers=headers,
            verify=client_cert
        )
        if response.status_code == 200:
            logger.info("Success!")
            return response.json()
        else:
            raise HTTPError(f"HTTP error: {response.status_code}")
    except TimeoutException as e:
        logger.error(f"Timeout occurred while waiting for API response: {e}")
        raise
    except HTTPError as e:
        logger.error(f"HTTP error occurred while waiting for API response: {e}")
        raise

def invoke_file_process_api(api_token: str, file_stream: bytes, bucket_key: str) -> dict:
    """
    Invokes the file processing API to upload files to Ameritas' system.

    Args:
        api_token (str): The authentication token from Ameritas' API.
        file_stream (bytes): The contents of the file to be uploaded.
        bucket_key (str): The key of the S3 bucket where the file is stored.

    Returns:
        dict: The JSON response from the API, or an empty dictionary if it fails.
    """
    try:
        headers = {
            "Authorization": f"Bearer {api_token}"
          
        }
        
        files = {
            "file": (bucket_key, file_stream, "application/octet-stream")
        }
        with httpx.Client(verify="AMERITASISSUING1-CA.crt",timeout=None) as client:
            file_upload_url = get_values_from_ssm(f"{get_environment_prefix()}/AMERITAS_CHAT_FILE_UPLOAD_URL")
            response = client.post(file_upload_url,
                              files=files,                          
                              headers=headers,
                              )
            response.raise_for_status()
            return response.json()
    except HTTPError as e:
        logger.error(f"HTTP error occurred while waiting for API response: {e}")
        raise
    except TimeoutException as e:
        logger.error(f"Timeout occurred while waiting for API response: {e}")
        raise


def process_files(event: dict, context) -> dict:
    """
    Processes files uploaded to S3 by invoking the file processing API.

    Args:
        event (dict): The Lambda event.
        context: The Lambda context.

    Returns:
        dict: The final response with the task ID, file upload status, and file ID.
    """
    token = get_token()
    logger.info("invoking the file upload")
    try:
        #req_body = json.loads(event['Records'][0]['body'])
        #req_detail = req_body['detail']
        bucket_name, bucket_key=parse_s3_uri(event['pdffile'])
        logger.info("[getting file details from the S3]")
        response = _s3_client.get_object(Bucket=bucket_name, Key=bucket_key)
        logger.info("[got the file details form the S3]")
        file_content = response['Body'].read()
        #logger.info(f"[file_content length is:{len(file_content)} ]")
        file_upload_resp = invoke_file_process_api(token ,file_content, bucket_key)
        return {
            "task_id": file_upload_resp["task_id"],
            "fileupload_status": file_upload_resp["file_status"],
            "fileid": file_upload_resp["file_id"],
            "organic_bucket": bucket_name,
            "organic_bucket_key": bucket_key,
            "statusMessage": "File processing is in progress",
        }
    except HTTPError as e:
        logger.error(f"HTTP error occurred while waiting for API response: {e}")
        raise
    except TimeoutException as e:
        logger.error(f"Timeout occurred while waiting for API response: {e}")
        raise

def _response(status: int, body: dict) -> dict:
    """Helper to build a consistent Lambda response."""
    return {"statusCode": status, "body": body}


def lambda_handler(event: dict, context) -> dict:
    """
    The main Lambda handler.

    Args:
        event (dict): The Lambda event.
        context: The Lambda context.

    Returns:
        dict: A dictionary containing the result of the assembly operation. 
              If an error occurs, returns a suitable response for the caller.
    """

    logger.info("Starting Lambda function...")
    try:
        final_response = process_files(event, context)
        return _response(200, final_response)
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        logger.error(error_message)
        return _response(500, {"error": error_message})
