-- 3. Raw Tables Setup
-- Creates tables to store the raw JSON content using VARIANT

USE DATABASE HEALTH_PLATFORM_DB;
USE SCHEMA RAW;

-- Patients Table
CREATE OR REPLACE TABLE PATIENTS (
    RECORD_CONTENT VARIANT COMMENT 'Full JSON content of the FHIR Patient resource',
    INGESTION_TIME TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP() COMMENT 'Time when row was inserted into Snowflake',
    SOURCE_FILE VARCHAR(16777216) COMMENT 'Name of the source file in S3',
    SOURCE_FILE_ROW_NUMBER NUMBER(38,0) COMMENT 'Row number in the source file'
);
