"""
Observation API Lambda handler.

Implements:
- GET /observation/{id} - Get single observation by ID
- GET /observation - Search observations with optional filters

Reference: docs/plan/step-10-fhir-api-implementation.md
"""

import json
import logging
from typing import Any

from health_platform.utils.db import execute_query

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context) -> dict[str, Any]:
    """
    Route observation requests to appropriate handler.
    """
    try:
        event.get("httpMethod", "GET")
        path_params = event.get("pathParameters") or {}
        query_params = event.get("queryStringParameters") or {}

        observation_id = path_params.get("observationId")

        if observation_id:
            # GET /observation/{id}
            return get_observation(observation_id)
        else:
            # GET /observation (search)
            return search_observations(query_params)

    except Exception as e:
        logger.exception(f"Error in observation handler: {e}")
        return error_response(500, "Internal Server Error")


def get_observation(observation_id: str) -> dict[str, Any]:
    """
    Retrieve a single observation by ID.

    Args:
        observation_id: The observation ID to fetch

    Returns:
        API Gateway response with observation data or error
    """
    logger.info(f"Fetching observation: {observation_id}")

    sql = """
    SELECT RECORD_CONTENT
    FROM RAW.OBSERVATIONS
    WHERE RECORD_CONTENT:id::string = %s
    LIMIT 1
    """

    try:
        results = execute_query(sql, (observation_id,))

        if not results:
            return error_response(404, "Observation not found")

        record = results[0]["RECORD_CONTENT"]
        response_body = parse_record(record)

        return success_response(response_body)

    except Exception as e:
        logger.error(f"Error fetching observation {observation_id}: {e}")
        raise


def search_observations(params: dict[str, str]) -> dict[str, Any]:
    """
    Search observations with FHIR-compatible parameters.

    Supported parameters:
    - patient: Patient ID to filter by
    - code: LOINC code(s) - comma-separated for multiple
    - date: Observation date (YYYY-MM-DD)
    - category: Observation category (vital-signs, laboratory, etc.)
    - status: Observation status (registered, preliminary, final, amended)
    - _count: Maximum results (default 100, max 1000)
    - _offset: Pagination offset

    Args:
        params: Query string parameters

    Returns:
        API Gateway response with FHIR Bundle
    """
    logger.info(f"Searching observations with params: {params}")

    # Extract and validate parameters
    patient_id = params.get("patient")
    code = params.get("code")
    date = params.get("date")
    category = params.get("category")
    status = params.get("status")

    # Pagination
    try:
        count = min(int(params.get("_count", 100)), 1000)
        offset = int(params.get("_offset", 0))
    except ValueError:
        return error_response(400, "Invalid pagination parameters")

    # Build query dynamically
    conditions = []
    query_params = []

    if patient_id:
        conditions.append("RECORD_CONTENT:subject.reference::string LIKE %s")
        query_params.append(f"%Patient/{patient_id}%")

    if code:
        # Support comma-separated LOINC codes
        codes = [c.strip() for c in code.split(",")]
        if len(codes) == 1:
            conditions.append("RECORD_CONTENT:code.coding[0].code::string = %s")
            query_params.append(codes[0])
        else:
            # For multiple codes, use OR conditions
            code_conditions = []
            for c in codes:
                code_conditions.append("RECORD_CONTENT:code.coding[0].code::string = %s")
                query_params.append(c)
            conditions.append(f"({' OR '.join(code_conditions)})")

    if date:
        # Search by date - match against effectiveDateTime
        conditions.append("RECORD_CONTENT:effectiveDateTime::string LIKE %s")
        query_params.append(f"{date}%")

    if category:
        conditions.append("RECORD_CONTENT:category[0].coding[0].code::string = %s")
        query_params.append(category)

    if status:
        conditions.append("RECORD_CONTENT:status::string = %s")
        query_params.append(status)

    # Build WHERE clause
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # Count total (for pagination info)
    count_sql = f"SELECT COUNT(*) as total FROM RAW.OBSERVATIONS {where_clause}"

    # Fetch results
    sql = f"""
    SELECT RECORD_CONTENT
    FROM RAW.OBSERVATIONS
    {where_clause}
    ORDER BY RECORD_CONTENT:effectiveDateTime::string DESC
    LIMIT %s OFFSET %s
    """

    query_params.extend([str(count), str(offset)])

    try:
        # Get total count
        count_results = execute_query(
            count_sql, tuple(query_params[:-2]) if query_params[:-2] else None
        )
        total = count_results[0]["TOTAL"] if count_results else 0

        # Get observations
        results = execute_query(sql, tuple(query_params))

        # Build FHIR Bundle response
        observations = []
        for row in results:
            record = parse_record(row["RECORD_CONTENT"])
            observations.append({"resource": record})

        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": total,
            "entry": observations,
        }

        return success_response(bundle)

    except Exception as e:
        logger.error(f"Error searching observations: {e}")
        raise


def get_patient_observations(
    patient_id: str, code: str | None = None, count: int = 100, offset: int = 0
) -> dict[str, Any]:
    """
    Convenience method to get observations for a specific patient.

    Args:
        patient_id: Patient ID
        code: Optional LOINC code filter
        count: Maximum results
        offset: Pagination offset

    Returns:
        API Gateway response with FHIR Bundle
    """
    params = {"patient": patient_id, "_count": str(count), "_offset": str(offset)}
    if code:
        params["code"] = code
    return search_observations(params)


def get_vital_signs(patient_id: str, count: int = 100, offset: int = 0) -> dict[str, Any]:
    """
    Convenience method to get vital signs for a patient.

    Args:
        patient_id: Patient ID
        count: Maximum results
        offset: Pagination offset

    Returns:
        API Gateway response with FHIR Bundle of vital signs
    """
    return search_observations(
        {
            "patient": patient_id,
            "category": "vital-signs",
            "_count": str(count),
            "_offset": str(offset),
        }
    )


def get_lab_results(patient_id: str, count: int = 100, offset: int = 0) -> dict[str, Any]:
    """
    Convenience method to get laboratory results for a patient.

    Args:
        patient_id: Patient ID
        count: Maximum results
        offset: Pagination offset

    Returns:
        API Gateway response with FHIR Bundle of lab results
    """
    return search_observations(
        {
            "patient": patient_id,
            "category": "laboratory",
            "_count": str(count),
            "_offset": str(offset),
        }
    )


def parse_record(record: Any) -> dict[str, Any]:
    """
    Parse a record from Snowflake, handling both string and dict formats.

    Args:
        record: Raw record from Snowflake (str or dict)

    Returns:
        Parsed dict
    """
    if isinstance(record, str):
        return json.loads(record)
    return record


def success_response(body: Any) -> dict[str, Any]:
    """
    Format a successful API response.

    Args:
        body: Response body (will be JSON serialized)

    Returns:
        API Gateway response dict
    """
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/fhir+json",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
        "body": json.dumps(body),
    }


def error_response(status_code: int, message: str) -> dict[str, Any]:
    """
    Format an error API response as FHIR OperationOutcome.

    Args:
        status_code: HTTP status code
        message: Error message

    Returns:
        API Gateway response dict with OperationOutcome
    """
    outcome = {
        "resourceType": "OperationOutcome",
        "issue": [
            {
                "severity": "error",
                "code": "processing"
                if status_code >= 500
                else "not-found"
                if status_code == 404
                else "invalid",
                "diagnostics": message,
            }
        ],
    }

    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/fhir+json"},
        "body": json.dumps(outcome),
    }
