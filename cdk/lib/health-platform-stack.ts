import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as path from 'path';
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as apigwv2_integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as apigwv2_authorizers from 'aws-cdk-lib/aws-apigatewayv2-authorizers';

export class HealthPlatformStack extends cdk.Stack {
    public readonly bucket: s3.Bucket;
    public readonly ingestionProcessor: lambda.Function;
    public readonly patientApiFunction: lambda.Function;
    public readonly authorizerFunction: lambda.Function;
    public readonly httpApi: apigwv2.HttpApi;

    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        // 1. Landing/Data Bucket
        this.bucket = new s3.Bucket(this, 'HealthPlatformBucket', {
            encryption: s3.BucketEncryption.S3_MANAGED,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
            autoDeleteObjects: true,
            removalPolicy: cdk.RemovalPolicy.DESTROY,
            eventBridgeEnabled: true,
            cors: [{
                allowedMethods: [s3.HttpMethods.POST, s3.HttpMethods.PUT, s3.HttpMethods.HEAD],
                allowedOrigins: ['*'],
                allowedHeaders: ['*']
            }]
        });

        // 2. Ingestion Lambda
        // We mount the entire project root to allow importing 'health_platform' package
        this.ingestionProcessor = new lambda.Function(this, 'IngestionProcessor', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'health_platform.ingestion.processor.handler.lambda_handler',
            code: lambda.Code.fromAsset(path.join(__dirname, '../../'), {
                exclude: [
                    'cdk', 'node_modules', '.git', '.venv', 'venv', '.beads',
                    '__pycache__', 'tests', 'docs', 'output'
                ]
            }),
            environment: {
                PROCESSED_PREFIX: 'processed/'
            },
            timeout: cdk.Duration.seconds(60),
            memorySize: 256,
            architecture: lambda.Architecture.ARM_64,
        });

        // 3. Permissions
        this.bucket.grantReadWrite(this.ingestionProcessor);

        // 4. S3 Event Notification (trigger on 'landing/' prefix)
        this.bucket.addEventNotification(
            s3.EventType.OBJECT_CREATED,
            new s3n.LambdaDestination(this.ingestionProcessor),
            { prefix: 'landing/', suffix: '.ndjson' }
        );

        // ========================================================================
        // Session 3: API Foundation
        // ========================================================================

        // 5. Patient API Lambda
        this.patientApiFunction = new lambda.Function(this, 'PatientApiFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'health_platform.api.patient.handler.lambda_handler',
            code: lambda.Code.fromAsset(path.join(__dirname, '../../'), {
                exclude: [
                    'cdk', 'node_modules', '.git', '.venv', 'venv', '.beads',
                    '__pycache__', 'tests', 'docs', 'output'
                ]
            }),
            environment: {
                // Placeholders for DB credentials.
                // In production, use AWS Secrets Manager.
                DB_ACCOUNT: 'PLACEHOLDER_ACCOUNT',
                DB_USER: 'PLACEHOLDER_USER',
                DB_PASSWORD: 'PLACEHOLDER_PASSWORD',
                DB_WAREHOUSE: 'PLACEHOLDER_WH',
                DB_DATABASE: 'HEALTH_PLATFORM_DB',
                DB_SCHEMA: 'RAW'
            },
            timeout: cdk.Duration.seconds(30),
            memorySize: 256,
            architecture: lambda.Architecture.ARM_64,
        });

        // 6. Authorizer Lambda
        this.authorizerFunction = new lambda.Function(this, 'AuthorizerFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'health_platform.api.authorizer.handler.lambda_handler',
            code: lambda.Code.fromAsset(path.join(__dirname, '../../'), {
                exclude: [
                    'cdk', 'node_modules', '.git', '.venv', 'venv', '.beads',
                    '__pycache__', 'tests', 'docs', 'output'
                ]
            }),
            architecture: lambda.Architecture.ARM_64,
        });

        // 7. API Gateway (HTTP API)
        const authorizer = new apigwv2_authorizers.HttpLambdaAuthorizer(
            'DefaultAuthorizer',
            this.authorizerFunction,
            {
                authorizerName: 'CustomLambdaAuthorizer',
                responseTypes: [apigwv2_authorizers.HttpLambdaResponseType.SIMPLE], // V2 Simple Response
            }
        );

        this.httpApi = new apigwv2.HttpApi(this, 'HealthPlatformApi', {
            apiName: 'HealthPlatformApi',
            defaultAuthorizer: authorizer,
            corsPreflight: {
                allowOrigins: ['*'],
                allowMethods: [apigwv2.CorsHttpMethod.GET],
                allowHeaders: ['Authorization', 'Content-Type'],
            }
        });

        // 8. Routes
        this.httpApi.addRoutes({
            path: '/patient/{patientId}',
            methods: [apigwv2.HttpMethod.GET],
            integration: new apigwv2_integrations.HttpLambdaIntegration(
                'PatientIntegration',
                this.patientApiFunction
            ),
        });

        // 6. Outputs
        new cdk.CfnOutput(this, 'HealthBucketName', {
            value: this.bucket.bucketName,
            description: 'Landing bucket for NDJSON files'
        });
        new cdk.CfnOutput(this, 'IngestionFunctionArn', {
            value: this.ingestionProcessor.functionArn
        });
        new cdk.CfnOutput(this, 'ApiEndpoint', {
            value: this.httpApi.apiEndpoint,
            description: 'HTTP API Endpoint URL'
        });
    }
}
