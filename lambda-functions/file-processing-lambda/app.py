# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""
Module: app.py
Description:
  1. Retrieves SSM parameters using a proxy configuration.
  2. Gets an authentication token from Ameritas' API.
  3. Invokes the file processing API to upload files to Ameritas' system.

Version: 1.0.1
Created: 2025-05-05
Last Modified: 2025-05-06
"""

from __future__ import annotations
import boto3
import httpx
from httpx import Timeout, HTTPError, TimeoutException
import logging
from botocore.config import Config
import json 
from io import BytesIO

# ─── Logging Configuration ─────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

client_cert = "AMERITASISSUING1-CA.crt"
ssm = boto3.client('ssm')
_s3_client = boto3.client("s3")
def get_values_from_ssm(ssm_key: str) -> str:
    """
    Retrieves the value of an SSM parameter using the proxy configuration.

    Args:
        ssm_key (str): The name of the SSM parameter to retrieve.

    Returns:
        str: The value of the SSM parameter, or None if it's not found.
    """
    try:
        response = ssm.get_parameter(
            Name=ssm_key,
            WithDecryption=False
        )
        if response['Parameter']['Value']:
            logger.info(f"Parameter Value for {ssm_key}: {response['Parameter']['Value']}")
            return response['Parameter']['Value']
        else:
            logger.warning(f"No value found for parameter: {ssm_key}")
            return None
    except Exception as e:
        raise ValueError(f"Error occurred while retrieving parameter: {e}")

def get_environment_prefix() -> str:
    """
    Compute the SSM key prefix based on the SERVER_ENV parameter.

    Raises:
        RuntimeError: If SERVER_ENV is not set.
    """
    env = get_values_from_ssm("/parameters/aio/ameritasAI/SERVER_ENV")
    if not env:
        raise RuntimeError("SERVER_ENV not set in SSM")
    return f"/parameters/aio/ameritasAI/{env}"

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

def parse_s3_uri(s3_uri):
    """
    Utility function to parse the S3 URI into bucket name and file key.

    Args:
        s3_uri (str): The S3 URI to parse.

    Returns:
        tuple: A tuple containing the bucket name and file key.
    """
    assert s3_uri.startswith("s3://"), "Invalid S3 URI"
    parts = s3_uri[5:].split("/", 1)
    bucket_name = parts[0]
    file_key = parts[1]
    return bucket_name, file_key

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
        task_id = file_upload_resp["task_id"]
        status = file_upload_resp["file_status"]
        file_id = file_upload_resp["file_id"]
        return {
            "task_id" : task_id,
            "fileupload_status" : status,
            "fileid" : file_id,
            "organic_bucket" : bucket_name,
            "organic_bucket_key" : bucket_key,
            "statusCode": 200,
            "statusMessage":"File processing is in progress",
        }
    except HTTPError as e:
        logger.error(f"HTTP error occurred while waiting for API response: {e}")
        raise
    except TimeoutException as e:
        logger.error(f"Timeout occurred while waiting for API response: {e}")
        raise

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
        return final_response
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        logger.error(error_message)
        response_body = f"error occurred: {error_message}"
        return {
            "statusCode": 500,
            "body": response_body,
            "headers": {"Content-Type": "application/json"},
        }