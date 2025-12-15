import os
import json
import boto3
import logging
from moto import mock_aws
from pathlib import Path
from click.testing import CliRunner
from synthetic.generators.unified_generator import main as generator_main
from health_platform.ingestion.processor.handler import lambda_handler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_pipeline")

@mock_aws
def run_verification():
    logger.info(">>> Starting Local Verification of Ingestion Pipeline")

    # 1. Setup Mock AWS Environment
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "health-platform-bucket"
    s3.create_bucket(Bucket=bucket_name)
    os.environ["PROCESSED_PREFIX"] = "processed/"
    logger.info(f"Created mock S3 bucket: {bucket_name}")

    # 2. Generate Data via CLI
    logger.info("Generating synthetic data...")
    runner = CliRunner()
    output_dir = Path("output/verify_temp")
    fhir_dir = output_dir / "fhir"
    omop_dir = output_dir / "omop"
    
    result = runner.invoke(generator_main, [
        "--count", "3",
        "--fhir-dir", str(fhir_dir),
        "--omop-dir", str(omop_dir),
        "--format", "ndjson"
    ])
    
    if result.exit_code != 0:
        logger.error("Generator failed!")
        logger.error(result.output)
        return False
        
    ndjson_path = fhir_dir / "patients.ndjson"
    if not ndjson_path.exists():
        logger.error("NDJSON file not generated!")
        return False
        
    logger.info(f"Generated data at: {ndjson_path}")
    
    # 3. "Upload" to Landing Zone
    source_key = "landing/patients.ndjson"
    with open(ndjson_path, "rb") as f:
        s3.put_object(Bucket=bucket_name, Key=source_key, Body=f.read())
    logger.info(f"Uploaded to s3://{bucket_name}/{source_key}")
    
    # 4. Simulate S3 Event Trigger
    event = {
        "Records": [{
            "s3": {
                "bucket": {"name": bucket_name},
                "object": {"key": source_key}
            }
        }]
    }
    
    # 5. Invoke Lambda Handler
    logger.info("Invoking Lambda Handler...")
    try:
        lambda_handler(event, {})
    except Exception as e:
        logger.error(f"Lambda failed: {e}")
        return False
        
    # 6. Verify Output
    dest_key = "processed/patients.ndjson"
    logger.info(f"Checking for output at s3://{bucket_name}/{dest_key}")
    
    try:
        response = s3.get_object(Bucket=bucket_name, Key=dest_key)
        processed_content = response['Body'].read().decode('utf-8')
        
        # Validate processed content
        lines = processed_content.strip().split('\n')
        logger.info(f"Read {len(lines)} lines from processed file")
        
        first_rec = json.loads(lines[0])
        if 'meta' in first_rec:
             logger.info("Verification SUCCESS: Metadata present in processed file")
        else:
             logger.error("Verification FAILED: Metadata missing")
             return False

        if first_rec.get('resourceType') == 'Patient':
             logger.info("Verification SUCCESS: Resource is a Patient")
        else:
             logger.error(f"Verification FAILED: Unexpected resource type {first_rec.get('resourceType')}")
             return False
             
    except s3.exceptions.NoSuchKey:
        logger.error("Verification FAILED: Processed file not found!")
        return False
        
    return True

if __name__ == "__main__":
    success = run_verification()
    if success:
        print("\n✅ END-TO-END VERIFICATION PASSED")
        exit(0)
    else:
        print("\n❌ END-TO-END VERIFICATION FAILED")
        exit(1)
