# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""
Module: app.py
Description:
  1. Retrieves SSM parameters using a proxy configuration.
  2. Starts an execution of a Step Function state machine.


Version: 1.0.2
Created: 2025-05-05
Last Modified: 2025-06-28
Modified By: Koushik Sinha
"""

from __future__ import annotations

import logging
import boto3
import json
from common_utils.get_ssm import (
    get_values_from_ssm,
    get_environment_prefix,
)

# Module Metadata
__author__ = "Balakrishna"  # Author name (please fill this in)
__version__ = "1.0.2"  # Version number of the module
__modified_by__ = "Koushik Sinha"


# ─── Logging Configuration ─────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
if not logger.handlers:
    logger.addHandler(_handler)


# Create a new client for Step Functions
step_functions = boto3.client('stepfunctions')
ssm = boto3.client('ssm')



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
    prefix = get_environment_prefix()
    state_machine_arn = get_values_from_ssm(f"{prefix}/STEP_FUNCTION_ARN")
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
