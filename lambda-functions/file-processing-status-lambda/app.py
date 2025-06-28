# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""
Module: app.py
Description:
  1. Retrieves SSM parameters using a proxy configuration.
  2. Gets an authentication token from Ameritas' API.
  3. Checks the status of file uploads to Ameritas' API.

Version: 1.0.1
Created: 2025-05-05
Last Modified: 2025-05-06
"""
from __future__ import annotations
import boto3
import json
import requests
from botocore.config import Config
import logging

# Module Metadata
__author__ = "Balakrishna"  # Author name (please fill this in)
__version__ = "1.0.1"  # Version number of the module

# ─── Logging Configuration ─────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

# Proxy configuration for SSM
proxy_definitions = {
    "http": "http://proxy.ameritas.com:8080",
    "https": "http://proxy.ameritas.com:8080",
}

#ssm = boto3.client("ssm", config=proxy_config)

proxy_config = Config(proxies=proxy_definitions)

ssm = boto3.client("ssm")


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

        if response["Parameter"]["Value"]:
            logger.info(f"Parameter Value for {ssm_key}: {response['Parameter']['Value']}")
            return response["Parameter"]["Value"]
        else:
            logger.warning(f"No value found for parameter: {ssm_key}")
            return None

    except Exception as e:
        logger.error(f"Error occurred while retrieving parameter: {e}")
        return None


# Get the environment variable from SSM
environment_value = get_values_from_ssm("/parameters/aio/ameritasAI/SERVER_ENV")

# Construct the SSM key for the functional user and token URL
ssm_key = f"/parameters/aio/ameritasAI/{environment_value}"


def get_token() -> dict:
    """
    Retrieves an authentication token from Ameritas' API.

    Returns:
        dict: The JSON response from the API, or an empty dictionary if it fails.
    """

    headers = {"Content-type": "application/json"}

    functional_user = get_values_from_ssm(f"{ssm_key}/FILE_PROCESSING_FUNCTIONAL_USER")

    try:
        # Construct the token URL
        token_url = get_values_from_ssm(f"{ssm_key}/AMERITAS_CHAT_TOKEN_URL")
        token_url = f"{token_url}?userId={functional_user}"

        headers = {"Content-type": "application/json"}

        response = requests.post(
            token_url,
            json={},
            headers=headers,
            verify="AMERITASISSUING1-CA.crt"
        )

        if response.status_code == 200:
            logger.info("Success!")
            return response.json()
        else:
            logger.error(f"Error: {response.status_code}")
            return None

    except Exception as e:
        logger.error(e)
        raise


def check_file_upload_status(input_data: dict) -> dict:
    """
    Checks the status of a file upload to Ameritas' API.

    Args:
        input_data (dict): A dictionary containing the task ID and file ID for the upload.

    Returns:
        dict: The JSON response from the API, or an empty dictionary if it fails.
    """

    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json"
    }

    status_url = get_values_from_ssm(f"{ssm_key}/AMERITAS_CHAT_FILESTTAUS_URL") + input_data["task_id"] + "?fileid=" + input_data["fileid"]
    
    try:
       response = requests.get(status_url, headers=headers, verify="AMERITASISSUING1-CA.crt")

       return response.json()
    except Exception as e:
        logger.error(e)
        raise

def check_file_processing_status(event: dict, context) -> dict:
    """
    Checks the status of file processing for a given event.

    Args:
        event (dict): The Lambda event.
        context: The Lambda context.

    Returns:
        dict: The updated event with the file processing status and collection name.
    """

    event_body = event.get("body", event)
    task_id = event_body["task_id"]

    if task_id:

        response = check_file_upload_status(event_body)

        if "meta" in response:
            logger.info("File processing completed")
            collection_name = response['meta']["collection_name"]
            event_body["collection_name"] = collection_name
            event_body["fileupload_status"] = "COMPLETE"
            event_body["statusMessage"] = "File processing completed"

            return event_body

        else:
            event_body["fileupload_status"] = response['file_status']

            return event_body


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
        dict: The updated event with the file processing status and collection name.
    """

    logger.info("Starting Lambda function...")

    try:
        body = check_file_processing_status(event, context)
        logger.info(f"Returning final response: {body}")
        return _response(200, body)
    except Exception as e:
        logger.exception("lambda_handler failed")
        return _response(500, {"statusMessage": str(e)})
