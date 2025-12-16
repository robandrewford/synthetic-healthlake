# Step 11: API SAM Template and Snowflake RBAC

## Overview

SAM template for deploying API Gateway with Lambda functions, and Snowflake RBAC configuration for least-privilege API access.

---

## template-api.yaml

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: |
  FHIR API Service Layer
  Bezos Mandate compliant: All data access via service interfaces

Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]

  JwksUrl:
    Type: String
    Description: JWKS endpoint for token validation
    Default: ''

  TokenIssuer:
    Type: String
    Description: Expected token issuer
    Default: ''

  ApiAudience:
    Type: String
    Description: Expected API audience claim
    Default: ''

  SnowflakeSecretArn:
    Type: String
    Description: ARN of Snowflake credentials secret

  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: VPC for Lambda functions

  PrivateSubnet1:
    Type: AWS::EC2::Subnet::Id
    Description: Private subnet 1

  PrivateSubnet2:
    Type: AWS::EC2::Subnet::Id
    Description: Private subnet 2

Globals:
  Function:
    Timeout: 30
    MemorySize: 512
    Runtime: python3.11
    Architectures: [arm64]
    Environment:
      Variables:
        LOG_LEVEL: INFO
        ENVIRONMENT: !Ref Environment

Resources:
  #############################################
  # NETWORKING
  #############################################

  ApiSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupName: !Sub healthtech-api-sg-${Environment}
      GroupDescription: Security group for API Lambda functions
      VpcId: !Ref VpcId
      SecurityGroupEgress:
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0
          Description: HTTPS outbound for Snowflake and Secrets Manager

  #############################################
  # API GATEWAY
  #############################################

  FhirApi:
    Type: AWS::Serverless::Api
    Properties:
      Name: !Sub healthtech-fhir-api-${Environment}
      StageName: !Ref Environment
      Description: FHIR-compliant API for healthcare data access

      # Authentication
      Auth:
        DefaultAuthorizer: TokenAuthorizer
        Authorizers:
          TokenAuthorizer:
            FunctionArn: !GetAtt AuthorizerFunction.Arn
            Identity:
              Header: Authorization
              ReauthorizeEvery: 300  # Cache auth for 5 minutes

      # Access logging
      AccessLogSetting:
        DestinationArn: !GetAtt ApiAccessLogGroup.Arn
        Format: >-
          {
            "requestId": "$context.requestId",
            "ip": "$context.identity.sourceIp",
            "caller": "$context.identity.caller",
            "user": "$context.identity.user",
            "requestTime": "$context.requestTime",
            "httpMethod": "$context.httpMethod",
            "resourcePath": "$context.resourcePath",
            "status": "$context.status",
            "protocol": "$context.protocol",
            "responseLength": "$context.responseLength",
            "organizationId": "$context.authorizer.organization_id",
            "latency": "$context.responseLatency"
          }

      # Throttling
      MethodSettings:
        - ResourcePath: '/*'
          HttpMethod: '*'
          ThrottlingBurstLimit: 100
          ThrottlingRateLimit: 50
          LoggingLevel: INFO
          DataTraceEnabled: false  # Don't log request/response bodies (PHI)
          MetricsEnabled: true

      # CORS
      Cors:
        AllowMethods: "'GET,POST,OPTIONS'"
        AllowHeaders: "'Content-Type,Authorization,X-Request-Id'"
        AllowOrigin: "'*'"  # Restrict in production

      # OpenAPI spec
      DefinitionBody:
        openapi: '3.0.1'
        info:
          title: !Sub Healthtech FHIR API (${Environment})
          version: '1.0.0'
        paths:
          /v1/fhir/Patient/{id}:
            get:
              summary: Get Patient by ID
              parameters:
                - name: id
                  in: path
                  required: true
                  schema:
                    type: string
              x-amazon-apigateway-integration:
                type: aws_proxy
                httpMethod: POST
                uri: !Sub arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${FhirApiFunction.Arn}/invocations
          /v1/fhir/Patient:
            get:
              summary: Search Patients
              parameters:
                - name: identifier
                  in: query
                  schema:
                    type: string
                - name: gender
                  in: query
                  schema:
                    type: string
                - name: birthdate
                  in: query
                  schema:
                    type: string
                - name: _count
                  in: query
                  schema:
                    type: integer
                    default: 100
              x-amazon-apigateway-integration:
                type: aws_proxy
                httpMethod: POST
                uri: !Sub arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${FhirApiFunction.Arn}/invocations

  #############################################
  # LAMBDA AUTHORIZER
  #############################################

  AuthorizerFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub fhir-api-authorizer-${Environment}
      Handler: handler.lambda_handler
      CodeUri: api_authorizer/
      Description: JWT token validation and organization context extraction
      MemorySize: 256
      Timeout: 10
      Environment:
        Variables:
          JWKS_URL: !Ref JwksUrl
          TOKEN_ISSUER: !Ref TokenIssuer
          API_AUDIENCE: !Ref ApiAudience
      # No VPC needed for authorizer (faster cold start)

  AuthorizerFunctionPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref AuthorizerFunction
      Action: lambda:InvokeFunction
      Principal: apigateway.amazonaws.com
      SourceArn: !Sub arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${FhirApi}/authorizers/*

  #############################################
  # FHIR API LAMBDA
  #############################################

  FhirApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub fhir-api-handler-${Environment}
      Handler: handler.lambda_handler
      CodeUri: fhir_api/
      Description: FHIR resource endpoints (Patient, Encounter, Observation)
      Timeout: 30
      MemorySize: 1024

      # VPC configuration for Snowflake access
      VpcConfig:
        SecurityGroupIds:
          - !Ref ApiSecurityGroup
        SubnetIds:
          - !Ref PrivateSubnet1
          - !Ref PrivateSubnet2

      Environment:
        Variables:
          SNOWFLAKE_SECRET_ARN: !Ref SnowflakeSecretArn
          SNOWFLAKE_WAREHOUSE: API_WH
          SNOWFLAKE_DATABASE: HEALTHTECH
          SNOWFLAKE_SCHEMA: ANALYTICS
          SNOWFLAKE_ROLE: API_READER

      Policies:
        - Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - secretsmanager:GetSecretValue
              Resource: !Ref SnowflakeSecretArn
            - Effect: Allow
              Action:
                - ec2:CreateNetworkInterface
                - ec2:DescribeNetworkInterfaces
                - ec2:DeleteNetworkInterface
              Resource: '*'

      Events:
        PatientGet:
          Type: Api
          Properties:
            RestApiId: !Ref FhirApi
            Path: /v1/fhir/Patient/{id}
            Method: GET
        PatientSearch:
          Type: Api
          Properties:
            RestApiId: !Ref FhirApi
            Path: /v1/fhir/Patient
            Method: GET
        EncounterGet:
          Type: Api
          Properties:
            RestApiId: !Ref FhirApi
            Path: /v1/fhir/Encounter/{id}
            Method: GET
        EncounterSearch:
          Type: Api
          Properties:
            RestApiId: !Ref FhirApi
            Path: /v1/fhir/Encounter
            Method: GET
        ObservationGet:
          Type: Api
          Properties:
            RestApiId: !Ref FhirApi
            Path: /v1/fhir/Observation/{id}
            Method: GET
        ObservationSearch:
          Type: Api
          Properties:
            RestApiId: !Ref FhirApi
            Path: /v1/fhir/Observation
            Method: GET

  #############################################
  # INGESTION API LAMBDA
  #############################################

  IngestionApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub ingestion-api-handler-${Environment}
      Handler: handler.lambda_handler
      CodeUri: ingestion_api/
      Description: Webhook receiver and presigned URL generator
      Timeout: 30
      MemorySize: 512

      Environment:
        Variables:
          INGESTION_QUEUE_URL: !Ref IngestionQueue
          UPLOAD_BUCKET: !Sub healthtech-data-lake-${Environment}
          UPLOAD_PREFIX: incoming/fhir

      Policies:
        - SQSSendMessagePolicy:
            QueueName: !GetAtt IngestionQueue.QueueName
        - S3CrudPolicy:
            BucketName: !Sub healthtech-data-lake-${Environment}

      Events:
        ReceiveBundle:
          Type: Api
          Properties:
            RestApiId: !Ref FhirApi
            Path: /v1/ingestion/fhir/Bundle
            Method: POST
        GetUploadUrl:
          Type: Api
          Properties:
            RestApiId: !Ref FhirApi
            Path: /v1/ingestion/upload-url
            Method: POST
        GetJobStatus:
          Type: Api
          Properties:
            RestApiId: !Ref FhirApi
            Path: /v1/ingestion/jobs/{jobId}
            Method: GET

  #############################################
  # SQS QUEUE FOR ASYNC INGESTION
  #############################################

  IngestionQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub fhir-ingestion-queue-${Environment}
      VisibilityTimeout: 900
      MessageRetentionPeriod: 1209600  # 14 days
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt IngestionDLQ.Arn
        maxReceiveCount: 3

  IngestionDLQ:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub fhir-ingestion-dlq-${Environment}
      MessageRetentionPeriod: 1209600

  #############################################
  # CLOUDWATCH LOGS
  #############################################

  ApiAccessLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub /aws/apigateway/healthtech-fhir-api-${Environment}
      RetentionInDays: 90

  AuthorizerLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub /aws/lambda/fhir-api-authorizer-${Environment}
      RetentionInDays: 30

  FhirApiLogGroup:
    Type: AWS::Logs::LogGroup
    Properties:
      LogGroupName: !Sub /aws/lambda/fhir-api-handler-${Environment}
      RetentionInDays: 30

  #############################################
  # WAF WEB ACL
  #############################################

  ApiWafAcl:
    Type: AWS::WAFv2::WebACL
    Properties:
      Name: !Sub healthtech-api-waf-${Environment}
      Scope: REGIONAL
      DefaultAction:
        Allow: {}
      VisibilityConfig:
        SampledRequestsEnabled: true
        CloudWatchMetricsEnabled: true
        MetricName: !Sub healthtech-api-waf-${Environment}
      Rules:
        # Rate limiting
        - Name: RateLimitPerIP
          Priority: 1
          Statement:
            RateBasedStatement:
              Limit: 2000  # Requests per 5 minutes
              AggregateKeyType: IP
          Action:
            Block: {}
          VisibilityConfig:
            SampledRequestsEnabled: true
            CloudWatchMetricsEnabled: true
            MetricName: RateLimitPerIP

        # AWS managed rules
        - Name: AWSManagedRulesCommonRuleSet
          Priority: 2
          Statement:
            ManagedRuleGroupStatement:
              VendorName: AWS
              Name: AWSManagedRulesCommonRuleSet
          OverrideAction:
            None: {}
          VisibilityConfig:
            SampledRequestsEnabled: true
            CloudWatchMetricsEnabled: true
            MetricName: CommonRuleSet

        # SQL injection protection
        - Name: AWSManagedRulesSQLiRuleSet
          Priority: 3
          Statement:
            ManagedRuleGroupStatement:
              VendorName: AWS
              Name: AWSManagedRulesSQLiRuleSet
          OverrideAction:
            None: {}
          VisibilityConfig:
            SampledRequestsEnabled: true
            CloudWatchMetricsEnabled: true
            MetricName: SQLiRuleSet

  ApiWafAssociation:
    Type: AWS::WAFv2::WebACLAssociation
    Properties:
      ResourceArn: !Sub arn:aws:apigateway:${AWS::Region}::/restapis/${FhirApi}/stages/${Environment}
      WebACLArn: !GetAtt ApiWafAcl.Arn

  #############################################
  # CLOUDWATCH ALARMS
  #############################################

  Api5xxAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub healthtech-api-5xx-${Environment}
      AlarmDescription: API Gateway 5xx errors
      MetricName: 5XXError
      Namespace: AWS/ApiGateway
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 1
      Threshold: 10
      ComparisonOperator: GreaterThanThreshold
      Dimensions:
        - Name: ApiName
          Value: !Sub healthtech-fhir-api-${Environment}
      AlarmActions:
        - !Ref AlertTopic

  ApiLatencyAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub healthtech-api-latency-${Environment}
      AlarmDescription: API Gateway high latency
      MetricName: Latency
      Namespace: AWS/ApiGateway
      Statistic: p95
      Period: 300
      EvaluationPeriods: 2
      Threshold: 5000  # 5 seconds
      ComparisonOperator: GreaterThanThreshold
      Dimensions:
        - Name: ApiName
          Value: !Sub healthtech-fhir-api-${Environment}
      AlarmActions:
        - !Ref AlertTopic

  AlertTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: !Sub healthtech-api-alerts-${Environment}

Outputs:
  ApiEndpoint:
    Description: API Gateway endpoint URL
    Value: !Sub https://${FhirApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}
    Export:
      Name: !Sub ${AWS::StackName}-ApiEndpoint

  ApiId:
    Description: API Gateway ID
    Value: !Ref FhirApi
    Export:
      Name: !Sub ${AWS::StackName}-ApiId

  IngestionQueueUrl:
    Description: SQS queue URL for async ingestion
    Value: !Ref IngestionQueue
    Export:
      Name: !Sub ${AWS::StackName}-IngestionQueueUrl

  AlertTopicArn:
    Description: SNS topic for alerts
    Value: !Ref AlertTopic
```

---

## Snowflake RBAC Configuration

### snowflake/rbac_setup.sql

```sql
-- ============================================
-- SNOWFLAKE RBAC FOR API ACCESS
-- Bezos Mandate: Least-privilege access
-- ============================================

USE ROLE SECURITYADMIN;

-- ============================================
-- 1. CREATE API_READER ROLE
-- ============================================

CREATE ROLE IF NOT EXISTS API_READER
    COMMENT = 'Read-only access to analytics schema for FHIR API';

-- ============================================
-- 2. GRANT DATABASE AND SCHEMA ACCESS
-- ============================================

-- Grant access to database
GRANT USAGE ON DATABASE HEALTHTECH TO ROLE API_READER;

-- Grant access ONLY to analytics schema (de-identified data)
GRANT USAGE ON SCHEMA HEALTHTECH.ANALYTICS TO ROLE API_READER;

-- Grant SELECT on all current tables
GRANT SELECT ON ALL TABLES IN SCHEMA HEALTHTECH.ANALYTICS TO ROLE API_READER;

-- Grant SELECT on future tables (for new dbt models)
GRANT SELECT ON FUTURE TABLES IN SCHEMA HEALTHTECH.ANALYTICS TO ROLE API_READER;

-- Grant SELECT on all current views
GRANT SELECT ON ALL VIEWS IN SCHEMA HEALTHTECH.ANALYTICS TO ROLE API_READER;

-- Grant SELECT on future views
GRANT SELECT ON FUTURE VIEWS IN SCHEMA HEALTHTECH.ANALYTICS TO ROLE API_READER;

-- ============================================
-- 3. EXPLICITLY DENY PHI VAULT ACCESS
-- (No grants = no access, but document intent)
-- ============================================

-- API_READER has NO access to:
-- - HEALTHTECH.PHI_VAULT (direct identifiers)
-- - HEALTHTECH.RAW (unprocessed data)
-- - HEALTHTECH.STAGING (intermediate data)

-- Verify no access exists
-- SHOW GRANTS TO ROLE API_READER;

-- ============================================
-- 4. CREATE DEDICATED WAREHOUSE
-- ============================================

USE ROLE SYSADMIN;

CREATE WAREHOUSE IF NOT EXISTS API_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60           -- Suspend after 1 minute idle
    AUTO_RESUME = TRUE
    MIN_CLUSTER_COUNT = 1
    MAX_CLUSTER_COUNT = 2       -- Scale up to 2 clusters under load
    SCALING_POLICY = 'ECONOMY'  -- Cost-optimized scaling
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Dedicated warehouse for FHIR API queries';

-- Grant warehouse usage to API role
GRANT USAGE ON WAREHOUSE API_WH TO ROLE API_READER;

-- ============================================
-- 5. CREATE SERVICE ACCOUNT
-- ============================================

USE ROLE SECURITYADMIN;

-- Create service account for API Lambda
CREATE USER IF NOT EXISTS API_SERVICE_ACCOUNT
    PASSWORD = 'CHANGE_ME_IMMEDIATELY'  -- Rotate via Secrets Manager
    LOGIN_NAME = 'api_service_account'
    DISPLAY_NAME = 'FHIR API Service Account'
    DEFAULT_ROLE = API_READER
    DEFAULT_WAREHOUSE = API_WH
    MUST_CHANGE_PASSWORD = FALSE
    COMMENT = 'Service account for FHIR API Lambda functions';

-- Grant role to service account
GRANT ROLE API_READER TO USER API_SERVICE_ACCOUNT;

-- ============================================
-- 6. RESOURCE MONITOR (Cost Control)
-- ============================================

USE ROLE ACCOUNTADMIN;

CREATE RESOURCE MONITOR IF NOT EXISTS API_WH_MONITOR
    WITH CREDIT_QUOTA = 100           -- Monthly credit limit
    FREQUENCY = MONTHLY
    START_TIMESTAMP = IMMEDIATELY
    TRIGGERS
        ON 75 PERCENT DO NOTIFY       -- Alert at 75%
        ON 90 PERCENT DO NOTIFY       -- Alert at 90%
        ON 100 PERCENT DO SUSPEND;    -- Suspend at 100%

ALTER WAREHOUSE API_WH SET RESOURCE_MONITOR = API_WH_MONITOR;

-- ============================================
-- 7. ROW ACCESS POLICY (Organization Isolation)
-- ============================================

USE ROLE SECURITYADMIN;

-- Create row access policy for organization isolation
CREATE OR REPLACE ROW ACCESS POLICY HEALTHTECH.ANALYTICS.organization_isolation
AS (organization_id VARCHAR) RETURNS BOOLEAN ->
    -- Allow access only to rows matching the session's organization
    organization_id = CURRENT_SESSION_CONTEXT('organization_id')
    OR
    -- Allow admin role to see all data
    IS_ROLE_IN_SESSION('ADMIN_READER');

-- Apply to patient dimension
ALTER TABLE HEALTHTECH.ANALYTICS.DIM_PATIENT
    ADD ROW ACCESS POLICY HEALTHTECH.ANALYTICS.organization_isolation
    ON (organization_id);

-- Apply to encounter fact
ALTER TABLE HEALTHTECH.ANALYTICS.FCT_ENCOUNTER
    ADD ROW ACCESS POLICY HEALTHTECH.ANALYTICS.organization_isolation
    ON (organization_id);

-- Apply to observation fact
ALTER TABLE HEALTHTECH.ANALYTICS.FCT_OBSERVATION
    ADD ROW ACCESS POLICY HEALTHTECH.ANALYTICS.organization_isolation
    ON (organization_id);

-- ============================================
-- 8. NETWORK POLICY (Optional - IP Allowlist)
-- ============================================

-- Uncomment if you want to restrict access to specific IPs
-- (e.g., NAT Gateway IPs from your VPC)

-- CREATE OR REPLACE NETWORK POLICY api_network_policy
--     ALLOWED_IP_LIST = ('10.0.0.0/8', '172.16.0.0/12')  -- Your VPC CIDR
--     BLOCKED_IP_LIST = ()
--     COMMENT = 'Restrict API access to VPC';

-- ALTER USER API_SERVICE_ACCOUNT SET NETWORK_POLICY = api_network_policy;

-- ============================================
-- 9. AUDIT LOGGING
-- ============================================

-- Ensure access history is enabled (required for HIPAA)
-- This is enabled by default in Snowflake

-- Query to verify access history
-- SELECT *
-- FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY
-- WHERE USER_NAME = 'API_SERVICE_ACCOUNT'
-- ORDER BY QUERY_START_TIME DESC
-- LIMIT 100;

-- ============================================
-- 10. VERIFICATION QUERIES
-- ============================================

-- Verify role grants
SHOW GRANTS TO ROLE API_READER;

-- Verify user grants
SHOW GRANTS TO USER API_SERVICE_ACCOUNT;

-- Test access (should succeed)
USE ROLE API_READER;
USE WAREHOUSE API_WH;
SELECT COUNT(*) FROM HEALTHTECH.ANALYTICS.DIM_PATIENT LIMIT 1;

-- Test access to PHI vault (should fail)
-- USE ROLE API_READER;
-- SELECT * FROM HEALTHTECH.PHI_VAULT.PATIENT LIMIT 1;
-- Error: Insufficient privileges
```

---

## Secrets Manager Configuration

### Create Snowflake credentials secret

```bash
# Create secret with Snowflake credentials
aws secretsmanager create-secret \
    --name healthtech/snowflake/api-service-account \
    --description "Snowflake credentials for FHIR API" \
    --secret-string '{
        "account": "your-account.us-east-1",
        "user": "API_SERVICE_ACCOUNT",
        "password": "your-secure-password",
        "warehouse": "API_WH",
        "database": "HEALTHTECH",
        "schema": "ANALYTICS",
        "role": "API_READER"
    }'

# Get the ARN for SAM template
aws secretsmanager describe-secret \
    --secret-id healthtech/snowflake/api-service-account \
    --query 'ARN' \
    --output text
```

---

## Deployment Commands

```bash
cd lambda_functions

# Build with shared code
./scripts/build_api_lambdas.sh

# Deploy API stack
sam deploy \
    --template-file template-api.yaml \
    --stack-name healthtech-fhir-api-dev \
    --parameter-overrides \
        Environment=dev \
        JwksUrl=https://your-idp.com/.well-known/jwks.json \
        TokenIssuer=https://your-idp.com/ \
        ApiAudience=https://api.healthtech.com \
        SnowflakeSecretArn=arn:aws:secretsmanager:us-east-1:123456789:secret:healthtech/snowflake/api-service-account \
        VpcId=vpc-12345 \
        PrivateSubnet1=subnet-11111 \
        PrivateSubnet2=subnet-22222 \
    --capabilities CAPABILITY_IAM \
    --confirm-changeset

# Get API endpoint
aws cloudformation describe-stacks \
    --stack-name healthtech-fhir-api-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text
```

---

## Verification

```bash
# Get API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name healthtech-fhir-api-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text)

# Test with valid token
curl -X GET "${API_ENDPOINT}/v1/fhir/Patient" \
    -H "Authorization: Bearer ${JWT_TOKEN}" \
    -H "Content-Type: application/fhir+json"

# Test without token (should return 401)
curl -X GET "${API_ENDPOINT}/v1/fhir/Patient" \
    -H "Content-Type: application/fhir+json"
```
