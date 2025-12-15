-- 2. Storage Integration Setup
-- WARNING: Requires ACCOUNTADMIN privileges
-- Replace bucket name with actual bucket name from CDK output

USE DATABASE HEALTH_PLATFORM_DB;
USE SCHEMA RAW;

-- Create Storage Integration
-- NOTE: Update allowed_locations with your actual S3 bucket ARN
CREATE OR REPLACE STORAGE INTEGRATION S3_HEALTH_INT
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'S3'
    ENABLED = TRUE
    STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::YOUR_ACCOUNT_ID:role/YOUR_SNOWFLAKE_ROLE' -- Placeholder: Update this!
    STORAGE_ALLOWED_LOCATIONS = ('s3://health-platform-bucket-PLACEHOLDER/processed/');

-- Describe integration to retrieve IAM User and External ID for AWS Trust Policy
DESC STORAGE INTEGRATION S3_HEALTH_INT;

-- Create External Stage
CREATE OR REPLACE STAGE S3_PROCESSED_STAGE
    STORAGE_INTEGRATION = S3_HEALTH_INT
    URL = 's3://health-platform-bucket-PLACEHOLDER/processed/'
    FILE_FORMAT = RAW.NDJSON_FORMAT;
