# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""
Module: app.py
Description:
  1. Retrieves SSM parameters using a proxy configuration.
  2. Starts an execution of a Step Function state machine.


Version: 1.0.1
Created: 2025-05-05
Last Modified: 2025-05-06
"""

from __future__ import annotations

import logging
import boto3
import json
from botocore.config import Config

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
    'http': 'http://proxy.ameritas.com:8080',
    'https': 'http://proxy.ameritas.com:8080'
}

proxy_config = Config(
    proxies=proxy_definitions
)

# Create a new client for Step Functions
#step_functions = boto3.client('stepfunctions', config=proxy_config)
step_functions = boto3.client('stepfunctions')
#ssm = boto3.client('ssm', config=proxy_config)
ssm = boto3.client('ssm')

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
        logger.error(f"Error occurred while retrieving parameter: {e}")
        raise


# Get the environment variable from SSM
environment_value = get_values_from_ssm("/parameters/aio/ameritasAI/SERVER_ENV")

ssm_key  = f"/parameters/aio/ameritasAI/{environment_value}"


def lambda_handler(event: dict, context) -> dict:
    """
    The main Lambda handler.

    Args:
        event (dict): The Lambda event.
        context: The Lambda context.

    Returns:
        dict: A dictionary containing the result of the execution start operation.
    """

    input_json = json.dumps(event)
    state_machine_arn = get_values_from_ssm(f"{ssm_key}/STEP_FUNCTION_ARN")
    #state_machine_arn ="arn:aws:states:us-east-2:528757830986:stateMachine:zip-processing-sf"
    # Start the task execution using the Lambda function as a trigger
    try:
         response = step_functions.start_execution(
         stateMachineArn=state_machine_arn,
         input=input_json
         )

         logger.info(f"response: {response}")

         if 'error' in response:
           logger.error(response['error'])
    except Exception as e:
        logger.error(f"Error occurred while retrieving parameter: {e}")
    return {"status":"Success"}
