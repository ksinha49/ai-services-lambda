import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Received event for 2-office-extractor: %s", event)
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "2-office-extractor executed"})
    }
