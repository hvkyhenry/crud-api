import json
import os
import uuid
import boto3                    # AWS SDK for Python, pre-installed in Lambda

# Connect to DynamoDB using the table name passed in as an environment variable.
# CDK sets this variable when it creates the Lambda function (you'll see how in Part 4).
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

def handler(event, context):
    """
    Main entry point for the Lambda function.
    API Gateway sends an 'event' dict containing the HTTP method, path,
    body, and any path parameters. This function routes to the right
    operation based on the HTTP method.
    """
    http_method = event["httpMethod"]       # "GET", "POST", "PUT", or "DELETE"
    path = event.get("resource", "")        # "/items" or "/items/{id}"

    try:
        # Route to the correct handler based on HTTP method and path
        if http_method == "GET" and path == "/items":
            return get_all_items()

        elif http_method == "GET" and path == "/items/{id}":
            item_id = event["pathParameters"]["id"]
            return get_item(item_id)

        elif http_method == "POST" and path == "/items":
            body = json.loads(event["body"])
            return create_item(body)

        elif http_method == "PUT" and path == "/items/{id}":
            item_id = event["pathParameters"]["id"]
            body = json.loads(event["body"])
            return update_item(item_id, body)

        elif http_method == "DELETE" and path == "/items/{id}":
            item_id = event["pathParameters"]["id"]
            return delete_item(item_id)

        # If none of the routes matched, return 400
        return api_response(400, {"error": "Unsupported route"})

    except Exception as e:
        # Catch-all for unexpected errors. In production you'd log more detail.
        return api_response(500, {"error": str(e)})

def get_all_items():
    """Scan the table and return all items."""
    result = table.scan()
    return api_response(200, result["Items"])

def get_item(item_id):
    """Fetch a single item by its id."""
    result = table.get_item(Key={"id": item_id})
    if "Item" not in result:
        return api_response(404, {"error": f"Item {item_id} not found"})
    return api_response(200, result["Item"])

def create_item(body):
    """Create a new item with a generated UUID."""
    item = {
        "id": str(uuid.uuid4()),    # Generate a unique id for the new item
        "name": body.get("name", ""),
        "description": body.get("description", ""),
    }
    table.put_item(Item=item)
    return api_response(201, item)

def update_item(item_id, body):
    """Update an existing item's name and description."""
    result = table.update_item(
        Key={"id": item_id},
        # UpdateExpression is DynamoDB's syntax for partial updates.
        # SET means "change these fields." The :n and :d are placeholders
        # that map to ExpressionAttributeValues below.
        UpdateExpression="SET #n = :n, description = :d",
        # "name" is a reserved word in DynamoDB, so we use #n as an alias
        ExpressionAttributeNames={"#n": "name"},
        ExpressionAttributeValues={
            ":n": body.get("name", ""),
            ":d": body.get("description", ""),
        },
        ReturnValues="ALL_NEW",     # Return the full item after the update
    )
    return api_response(200, result["Attributes"])

def delete_item(item_id):
    """Delete an item by its id."""
    table.delete_item(Key={"id": item_id})
    return api_response(200, {"message": f"Deleted {item_id}"})

def api_response(status_code, body):
    """
    Build the response dict that API Gateway expects.
    API Gateway requires this exact format: statusCode, headers, and body.
    The body must be a JSON string, not a dict.
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            # Allow requests from any origin (fine for a tutorial,
            # restrict this in production)
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),  # default=str handles Decimal types from DynamoDB
    }