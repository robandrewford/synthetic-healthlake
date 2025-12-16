def lambda_handler(event, context):
    """
    Simple Lambda Authorizer for HTTP API.
    """
    # Look for 'authorization' header (case insensitive usually, but HTTP API V2 payloads normalize headers)
    headers = event.get("headers", {})
    token = headers.get("authorization", "")

    # Simple check: Token must equal 'secret-token'
    is_authorized = token == "secret-token"

    response = {
        "isAuthorized": is_authorized,
        "context": {"user": "test-user-id", "scope": "read:patient"},
    }

    return response
