import json
from typing import Any


class ValidationError(Exception):
    pass


def validate_ndjson(content: str) -> list[dict[str, Any]]:
    """
    Validate NDJSON content where each line must be a valid JSON object
    and contain a 'resourceType' field.

    Args:
        content (str): Raw string content of the NDJSON file

    Returns:
        List[Dict[str, Any]]: List of validated JSON objects with metadata added

    Raises:
        ValidationError: If any line is invalid JSON or missing resourceType
    """
    valid_records = []
    lines = content.strip().split("\n")

    for i, line in enumerate(lines):
        if not line.strip():
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON on line {i + 1}: {str(e)}") from e

        if not isinstance(record, dict):
            raise ValidationError(f"Line {i + 1} is not a JSON object")

        if "resourceType" not in record:
            raise ValidationError(f"Missing 'resourceType' on line {i + 1}")

        # Add metadata for ingestion tracking
        if "meta" not in record:
            record["meta"] = {}

        # Add ingestion timestamp if not present (don't overwrite source meta)
        # Note: In a real scenario we might append to a specific extension or tag
        # but for now we just verify it's a valid object

        valid_records.append(record)

    return valid_records
