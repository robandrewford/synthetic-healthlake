# Step 4: SAM Template for Deployment

## Overview

AWS SAM template defining Lambda functions, Step Functions state machine, and supporting resources.

---

## template.yaml

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: FHIR Bulk Export Ingestion Pipeline

Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]
  
  SourceBucket:
    Type: String
    Default: healthtech-fhir-source
  
  LandingBucket:
    Type: String
    Default: healthtech-data-lake

Globals:
  Function:
    Timeout: 300
    MemorySize: 1024
    Runtime: python3.11
    Architectures:
      - arm64  # Graviton2 for cost savings
    Environment:
      Variables:
        SOURCE_BUCKET: !Ref SourceBucket
        LANDING_BUCKET: !Ref LandingBucket
        LANDING_PREFIX: landing/fhir
        LOG_LEVEL: INFO

Resources:
  # IAM Role for Lambda functions
  FhirIngestionRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub fhir-ingestion-role-${Environment}
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
      Policies:
        - PolicyName: S3Access
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - s3:GetObject
                  - s3:ListBucket
                Resource:
                  - !Sub arn:aws:s3:::${SourceBucket}
                  - !Sub arn:aws:s3:::${SourceBucket}/*
              - Effect: Allow
                Action:
                  - s3:PutObject
                  - s3:GetObject
                Resource:
                  - !Sub arn:aws:s3:::${LandingBucket}/landing/fhir/*

  # Lambda 1: Initiate Export
  InitiateExportFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub fhir-initiate-export-${Environment}
      Handler: initiate_export.lambda_handler
      CodeUri: fhir_ingestion/
      Role: !GetAtt FhirIngestionRole.Arn
      Description: Initiate FHIR bulk export (Synthea or Epic)

  # Lambda 2: Poll Export Status  
  PollExportStatusFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub fhir-poll-status-${Environment}
      Handler: poll_export_status.lambda_handler
      CodeUri: fhir_ingestion/
      Role: !GetAtt FhirIngestionRole.Arn
      Description: Poll FHIR export status

  # Lambda 3: Download Resources
  DownloadResourcesFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub fhir-download-resources-${Environment}
      Handler: download_resources.lambda_handler
      CodeUri: fhir_ingestion/
      Role: !GetAtt FhirIngestionRole.Arn
      Timeout: 900  # 15 min for large exports
      MemorySize: 2048
      Description: Download and transform FHIR resources to landing zone

  # Step Functions State Machine
  FhirIngestionStateMachine:
    Type: AWS::Serverless::StateMachine
    Properties:
      Name: !Sub fhir-ingestion-${Environment}
      DefinitionUri: statemachine/fhir_ingestion.asl.json
      DefinitionSubstitutions:
        InitiateExportArn: !GetAtt InitiateExportFunction.Arn
        PollStatusArn: !GetAtt PollExportStatusFunction.Arn
        DownloadResourcesArn: !GetAtt DownloadResourcesFunction.Arn
        AlertTopicArn: !Ref AlertTopic
      Policies:
        - LambdaInvokePolicy:
            FunctionName: !Ref InitiateExportFunction
        - LambdaInvokePolicy:
            FunctionName: !Ref PollExportStatusFunction
        - LambdaInvokePolicy:
            FunctionName: !Ref DownloadResourcesFunction
        - SNSPublishMessagePolicy:
            TopicName: !GetAtt AlertTopic.TopicName

  # SNS Topic for alerts
  AlertTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: !Sub fhir-ingestion-alerts-${Environment}

  # EventBridge Rule for scheduled execution
  DailyIngestionRule:
    Type: AWS::Events::Rule
    Properties:
      Name: !Sub fhir-daily-ingestion-${Environment}
      Description: Trigger FHIR ingestion daily at 6 AM UTC
      ScheduleExpression: cron(0 6 * * ? *)
      State: DISABLED  # Enable when ready
      Targets:
        - Id: FhirIngestionTarget
          Arn: !Ref FhirIngestionStateMachine
          RoleArn: !GetAtt EventBridgeRole.Arn
          Input: |
            {
              "source_prefix": "synthea/batch-001",
              "mode": "synthea"
            }

  EventBridgeRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: events.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: StartStateMachine
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action: states:StartExecution
                Resource: !Ref FhirIngestionStateMachine

Outputs:
  InitiateExportFunction:
    Description: Initiate Export Lambda ARN
    Value: !GetAtt InitiateExportFunction.Arn
  
  StateMachineArn:
    Description: State Machine ARN
    Value: !Ref FhirIngestionStateMachine
  
  AlertTopicArn:
    Description: SNS Alert Topic ARN
    Value: !Ref AlertTopic
```

---

## statemachine/fhir_ingestion.asl.json

Step Functions state machine definition using Amazon States Language.

```json
{
  "Comment": "FHIR Bulk Export Ingestion Pipeline",
  "StartAt": "InitiateExport",
  "States": {
    "InitiateExport": {
      "Type": "Task",
      "Resource": "${InitiateExportArn}",
      "ResultPath": "$.exportStatus",
      "Next": "PollStatus",
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "ResultPath": "$.error",
        "Next": "NotifyFailure"
      }]
    },
    
    "PollStatus": {
      "Type": "Task",
      "Resource": "${PollStatusArn}",
      "InputPath": "$.exportStatus",
      "ResultPath": "$.pollResult",
      "Next": "CheckComplete",
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "ResultPath": "$.error",
        "Next": "NotifyFailure"
      }]
    },
    
    "CheckComplete": {
      "Type": "Choice",
      "Choices": [{
        "Variable": "$.pollResult.complete",
        "BooleanEquals": true,
        "Next": "DownloadResources"
      }],
      "Default": "WaitForExport"
    },
    
    "WaitForExport": {
      "Type": "Wait",
      "Seconds": 60,
      "Next": "PollStatus"
    },
    
    "DownloadResources": {
      "Type": "Task",
      "Resource": "${DownloadResourcesArn}",
      "InputPath": "$.pollResult",
      "ResultPath": "$.downloadResult",
      "Next": "Success",
      "Catch": [{
        "ErrorEquals": ["States.ALL"],
        "ResultPath": "$.error",
        "Next": "NotifyFailure"
      }]
    },
    
    "NotifyFailure": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "${AlertTopicArn}",
        "Subject": "FHIR Ingestion Pipeline Failed",
        "Message.$": "States.Format('Export failed: {}', $.error)"
      },
      "Next": "Failed"
    },
    
    "Success": {
      "Type": "Succeed"
    },
    
    "Failed": {
      "Type": "Fail",
      "Error": "IngestionFailed",
      "Cause": "See error details in execution history"
    }
  }
}
```

---

## samconfig.toml

SAM deployment configuration.

```toml
version = 0.1

[default.deploy.parameters]
stack_name = "fhir-ingestion-dev"
resolve_s3 = true
s3_prefix = "fhir-ingestion"
region = "us-east-1"
confirm_changeset = true
capabilities = "CAPABILITY_NAMED_IAM"
parameter_overrides = "Environment=\"dev\" SourceBucket=\"healthtech-fhir-source\" LandingBucket=\"healthtech-data-lake\""

[staging.deploy.parameters]
stack_name = "fhir-ingestion-staging"
resolve_s3 = true
s3_prefix = "fhir-ingestion"
region = "us-east-1"
confirm_changeset = true
capabilities = "CAPABILITY_NAMED_IAM"
parameter_overrides = "Environment=\"staging\" SourceBucket=\"healthtech-fhir-source\" LandingBucket=\"healthtech-data-lake\""

[prod.deploy.parameters]
stack_name = "fhir-ingestion-prod"
resolve_s3 = true
s3_prefix = "fhir-ingestion"
region = "us-east-1"
confirm_changeset = true
capabilities = "CAPABILITY_NAMED_IAM"
parameter_overrides = "Environment=\"prod\" SourceBucket=\"healthtech-fhir-source-prod\" LandingBucket=\"healthtech-data-lake-prod\""
```
