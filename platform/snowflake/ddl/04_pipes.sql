-- 4. Pipes Setup
-- Configures Snowpipe to auto-ingest data from S3 Stage to Raw Tables

USE DATABASE HEALTH_PLATFORM_DB;
USE SCHEMA RAW;

-- Create Pipe for Patients
CREATE OR REPLACE PIPE PIPE_PATIENTS
AUTO_INGEST = TRUE
COMMENT = 'Auto-ingest patient NDJSON files from S3 processed folder'
AS
COPY INTO PATIENTS (RECORD_CONTENT, SOURCE_FILE, SOURCE_FILE_ROW_NUMBER)
FROM (
    SELECT
        $1,
        METADATA$FILENAME,
        METADATA$FILE_ROW_NUMBER
    FROM @S3_PROCESSED_STAGE
)
-- Matches files like 'patients.ndjson' or 'patients_001.ndjson'
PATTERN = '.*patients.*\.ndjson';

-- Check Pipe Status
SELECT SYSTEM$PIPE_STATUS ('PIPE_PATIENTS');
