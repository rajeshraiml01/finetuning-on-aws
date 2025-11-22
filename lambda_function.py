import json
import os
import time
import uuid
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

runtime = boto3.client("sagemaker-runtime")
dynamo = boto3.resource("dynamodb").Table(os.environ["LOG_TABLE"])
ENDPOINT = os.environ["SAGEMAKER_ENDPOINT"]

def safe_json(value):
    """Convert any Python object into DynamoDB-safe JSON-friendly string."""
    try:
        return json.dumps(value)
    except:
        return str(value)

def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    text = body.get("inputs", "")

    # ----- Call SageMaker endpoint -----
    resp = runtime.invoke_endpoint(
        EndpointName=ENDPOINT,
        ContentType="application/json",
        Body=json.dumps({"inputs": text})
    )
    result = json.loads(resp["Body"].read().decode())

    # ----- Build log item for DynamoDB -----
    request_id = context.aws_request_id  # always unique

    log_item = {
        "request_id": f"{int(time.time()*1000)}#{request_id}",  # Primary Key
        "prompt": text,
        "response": safe_json(result),                  # Convert result to string
        "timestamp": int(time.time())
    }

    # ----- Write to DynamoDB -----
    try:
        dynamo.put_item(Item=log_item)
    except ClientError as e:
        print("DynamoDB ERROR:", e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    # ----- Success Response -----
    return {
        "statusCode": 200,
        "body": json.dumps({"result": result})
    }
