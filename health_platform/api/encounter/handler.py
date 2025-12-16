"""
Encounter API Lambda handler.

Implements:
- GET /encounter/{id} - Get single encounter by ID
- GET /encounter - Search encounters with optional filters

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
    Route encounter requests to appropriate handler.
    """
    try:
        event.get("httpMethod", "GET")
        path_params = event.get("pathParameters") or {}
        query_params = event.get("queryStringParameters") or {}

        encounter_id = path_params.get("encounterId")

        if encounter_id:
            # GET /encounter/{id}
            return get_encounter(encounter_id)
        else:
            # GET /encounter (search)
            return search_encounters(query_params)

    except Exception as e:
        logger.exception(f"Error in encounter handler: {e}")
        return error_response(500, "Internal Server Error")


def get_encounter(encounter_id: str) -> dict[str, Any]:
    """
    Retrieve a single encounter by ID.

    Args:
        encounter_id: The encounter ID to fetch

    Returns:
        API Gateway response with encounter data or error
    """
    logger.info(f"Fetching encounter: {encounter_id}")

    sql = """
    SELECT RECORD_CONTENT
    FROM RAW.ENCOUNTERS
    WHERE RECORD_CONTENT:id::string = %s
    LIMIT 1
    """

    try:
        results = execute_query(sql, (encounter_id,))

        if not results:
            return error_response(404, "Encounter not found")

        record = results[0]["RECORD_CONTENT"]
        response_body = parse_record(record)

        return success_response(response_body)

    except Exception as e:
        logger.error(f"Error fetching encounter {encounter_id}: {e}")
        raise


def search_encounters(params: dict[str, str]) -> dict[str, Any]:
    """
    Search encounters with FHIR-compatible parameters.

    Supported parameters:
    - patient: Patient ID to filter by
    - status: Encounter status (planned, arrived, triaged, in-progress,
              onleave, finished, cancelled)
    - date: Encounter date (YYYY-MM-DD)
    - class: Encounter class code (AMB, EMER, IMP, etc.)
    - _count: Maximum results (default 100, max 1000)
    - _offset: Pagination offset

    Args:
        params: Query string parameters

    Returns:
        API Gateway response with FHIR Bundle
    """
    logger.info(f"Searching encounters with params: {params}")

    # Extract and validate parameters
    patient_id = params.get("patient")
    status = params.get("status")
    date = params.get("date")
    encounter_class = params.get("class")

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

    if status:
        conditions.append("RECORD_CONTENT:status::string = %s")
        query_params.append(status)

    if date:
        # Search by date - match against period.start
        conditions.append("RECORD_CONTENT:period.start::string LIKE %s")
        query_params.append(f"{date}%")

    if encounter_class:
        conditions.append("RECORD_CONTENT:class.code::string = %s")
        query_params.append(encounter_class)

    # Build WHERE clause
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # Count total (for pagination info)
    count_sql = f"SELECT COUNT(*) as total FROM RAW.ENCOUNTERS {where_clause}"

    # Fetch results
    sql = f"""
    SELECT RECORD_CONTENT
    FROM RAW.ENCOUNTERS
    {where_clause}
    ORDER BY RECORD_CONTENT:period.start::string DESC
    LIMIT %s OFFSET %s
    """

    query_params.extend([str(count), str(offset)])

    try:
        # Get total count
        count_results = execute_query(
            count_sql, tuple(query_params[:-2]) if query_params[:-2] else None
        )
        total = count_results[0]["TOTAL"] if count_results else 0

        # Get encounters
        results = execute_query(sql, tuple(query_params))

        # Build FHIR Bundle response
        encounters = []
        for row in results:
            record = parse_record(row["RECORD_CONTENT"])
            encounters.append({"resource": record})

        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": total,
            "entry": encounters,
        }

        return success_response(bundle)

    except Exception as e:
        logger.error(f"Error searching encounters: {e}")
        raise


def get_patient_encounters(patient_id: str, count: int = 100, offset: int = 0) -> dict[str, Any]:
    """
    Convenience method to get all encounters for a specific patient.

    Args:
        patient_id: Patient ID
        count: Maximum results
        offset: Pagination offset

    Returns:
        API Gateway response with FHIR Bundle
    """
    return search_encounters({"patient": patient_id, "_count": str(count), "_offset": str(offset)})


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
