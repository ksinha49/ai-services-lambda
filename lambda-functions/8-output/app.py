# ------------------------------------------------------------------------------
# app.py
# ------------------------------------------------------------------------------
"""
Module: app.py
Description:
  Basic Lambda handler for 8-output.
Version: 1.0.0
"""

from __future__ import annotations
import json
import logging

__author__ = "Balakrishna"
__version__ = "1.0.0"
__modified_by__ = "Koushik Sinha"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%dT%H:%M:%S%z")
)
logger.addHandler(_handler)

def lambda_handler(event: dict, context: dict) -> dict:
    logger.info("Received event for 8-output: %s", event)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "8-output executed"})
    }
