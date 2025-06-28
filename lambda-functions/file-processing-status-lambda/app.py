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
import logging
from common_utils.get_ssm import (
    get_values_from_ssm,
    get_environment_prefix,
)

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

# No proxy configuration is required for SSM access when running within AWS.


def get_token() -> dict:
    """
    Retrieves an authentication token from Ameritas' API.

    Returns:
        dict: The JSON response from the API, or an empty dictionary if it fails.
    """

    headers = {"Content-type": "application/json"}
    prefix = get_environment_prefix()
    functional_user = get_values_from_ssm(f"{prefix}/FILE_PROCESSING_FUNCTIONAL_USER")

    try:
        # Construct the token URL
        token_url = get_values_from_ssm(f"{prefix}/AMERITAS_CHAT_TOKEN_URL")
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

    prefix = get_environment_prefix()
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json"
    }

    status_url = get_values_from_ssm(f"{prefix}/AMERITAS_CHAT_FILESTTAUS_URL") + input_data["task_id"] + "?fileid=" + input_data["fileid"]
    
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
