import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Received event for 1-classifier: %s", event)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "1-classifier executed"})
    }
