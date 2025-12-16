import json
import logging
import os

import boto3

from .validator import ValidationError, validate_ndjson

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")

PROCESSED_PREFIX = os.environ.get("PROCESSED_PREFIX", "processed/")


def lambda_handler(event, context):
    """
    S3 Event Handler for FHIR Ingestion.
    Triggered by ObjectCreated events.
    """
    for record in event.get("Records", []):
        try:
            source_bucket = record["s3"]["bucket"]["name"]
            source_key = record["s3"]["object"]["key"]

            logger.info(f"Processing file: s3://{source_bucket}/{source_key}")

            # Download file
            response = s3_client.get_object(Bucket=source_bucket, Key=source_key)
            content = response["Body"].read().decode("utf-8")

            # Validate
            valid_records = validate_ndjson(content)
            logger.info(f"Successfully validated {len(valid_records)} records")

            # Prepare output (add ingestion metadata)
            output_content = ""
            for rec in valid_records:
                output_content += json.dumps(rec) + "\n"

            # Define destination key
            # landing/file.ndjson -> processed/file.ndjson
            filename = source_key.split("/")[-1]
            dest_key = f"{PROCESSED_PREFIX}{filename}"

            # Upload processed file
            s3_client.put_object(
                Bucket=source_bucket,  # Using same bucket for simplicity now
                Key=dest_key,
                Body=output_content.encode("utf-8"),
                ContentType="application/x-ndjson",
            )

            logger.info(f"Uploaded processed file to: s3://{source_bucket}/{dest_key}")

            # Optional: Move/Delete original (implementation depends on retention policy)
            # For now, we leave it in landing but might set a lifecycle policy later

        except ValidationError as e:
            logger.error(f"Validation failed for {source_key}: {str(e)}")
            # In a real system, move to 'failed/' prefix
            raise e
        except Exception as e:
            logger.error(f"Error processing {source_key}: {str(e)}")
            raise e

    return {"statusCode": 200, "body": json.dumps("Ingestion complete")}
