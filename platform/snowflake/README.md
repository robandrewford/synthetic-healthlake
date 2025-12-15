# Snowflake Platform Setup

This directory contains the necessary resources to set up the Health Platform in Snowflake.

## DDL Scripts (`ddl/`)

Run these scripts sequentially in your Snowflake Worksheet to bootstrap the environment.

1.  **`01_database_setup.sql`**: Creates the `HEALTH_PLATFORM_DB` database, `RAW` and `ANALYTICS` schemas, and the `NDJSON_FORMAT` file format.
2.  **`02_storage_integration.sql`**: Sets up the connection to AWS S3.
    *   **ACTION REQUIRED**: You must update the `STORAGE_ALLOWED_LOCATIONS` with your actual S3 bucket name.
    *   **ACTION REQUIRED**: You must update `STORAGE_AWS_ROLE_ARN` with your IAM Role ARN.
    *   **ACTION REQUIRED**: After running this, execute `DESC STORAGE INTEGRATION S3_HEALTH_INT;` and update your AWS IAM Role Trust Policy with the `STORAGE_AWS_IAM_USER_ARN` and `STORAGE_AWS_EXTERNAL_ID`.
3.  **`03_raw_tables.sql`**: Creates the `RAW.PATIENTS` table using the `VARIANT` data type to store full JSON documents.
4.  **`04_pipes.sql`**: Defines the Snowpipe `PIPE_PATIENTS` to auto-ingest data from the S3 Stage into the raw table.

## dbt

The `dbt/` directory (located at the repo root `dbt/snowflake`) will contain the transformation logic to model this raw data into the `ANALYTICS` schema.
