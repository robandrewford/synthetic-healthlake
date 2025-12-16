import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as path from 'path';
import * as apigwv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as apigwv2_integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as apigwv2_authorizers from 'aws-cdk-lib/aws-apigatewayv2-authorizers';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { PlatformSecrets } from './constructs/secrets-construct';

export class HealthPlatformStack extends cdk.Stack {
    public readonly bucket: s3.Bucket;
    public readonly ingestionProcessor: lambda.Function;
    public readonly patientApiFunction: lambda.Function;
    public readonly encounterApiFunction: lambda.Function;
    public readonly observationApiFunction: lambda.Function;
    public readonly webhookFunction: lambda.Function;
    public readonly presignedUrlFunction: lambda.Function;
    public readonly authorizerFunction: lambda.Function;
    public readonly httpApi: apigwv2.HttpApi;
    public readonly ingestionQueue: sqs.Queue;
    public readonly secrets: PlatformSecrets;

    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        // ========================================================================
        // Resource Tagging Strategy
        // ========================================================================
        // Apply tags to all resources in this stack for:
        // - Cost allocation and tracking
        // - Environment identification
        // - Management and governance
        const environment = props?.env?.account ? 'prod' : 'dev';

        cdk.Tags.of(this).add('Project', 'fhir-omop-reference');
        cdk.Tags.of(this).add('Environment', environment);
        cdk.Tags.of(this).add('ManagedBy', 'CDK');
        cdk.Tags.of(this).add('Application', 'health-platform');
        cdk.Tags.of(this).add('CostCenter', 'healthcare-analytics');
        cdk.Tags.of(this).add('Owner', 'platform-team');

        // Common Lambda code asset configuration
        const lambdaCodeExcludes = [
            'cdk', 'node_modules', '.git', '.venv', 'venv', '.beads',
            '__pycache__', 'tests', 'docs', 'output', 'htmlcov', '.coverage'
        ];

        // ========================================================================
        // Secrets Management
        // ========================================================================

        // Create centralized secrets for the platform
        // After deployment, update secret values via AWS Console or CLI:
        //   aws secretsmanager put-secret-value --secret-id health-platform/snowflake --secret-string '...'
        this.secrets = new PlatformSecrets(this, 'Secrets', {
            secretNamePrefix: 'health-platform',
            createSecrets: true,
        });

        // Environment variables pointing to secrets (Lambdas fetch values at runtime)
        const dbEnvironment = {
            ...this.secrets.getLambdaEnvironment(),
            DB_DATABASE: 'HEALTH_PLATFORM_DB',
            DB_SCHEMA: 'RAW',
        };

        // ========================================================================
        // Infrastructure: S3 Bucket and SQS Queue
        // ========================================================================

        // 1. Landing/Data Bucket with Enhanced Security
        this.bucket = new s3.Bucket(this, 'HealthPlatformBucket', {
            // Encryption: Server-side encryption with S3-managed keys
            encryption: s3.BucketEncryption.S3_MANAGED,

            // Security: Block all public access
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,

            // Security: Enforce HTTPS-only access
            enforceSSL: true,

            // Versioning for data protection and audit trail
            versioned: true,

            // Lifecycle rules for cost optimization
            lifecycleRules: [
                {
                    // Move processed files to Intelligent-Tiering after 30 days
                    id: 'ProcessedToIntelligentTiering',
                    prefix: 'processed/',
                    transitions: [
                        {
                            storageClass: s3.StorageClass.INTELLIGENT_TIERING,
                            transitionAfter: cdk.Duration.days(30),
                        },
                    ],
                },
                {
                    // Move landing files to Infrequent Access after 90 days
                    id: 'LandingToIA',
                    prefix: 'landing/',
                    transitions: [
                        {
                            storageClass: s3.StorageClass.INFREQUENT_ACCESS,
                            transitionAfter: cdk.Duration.days(90),
                        },
                    ],
                },
                {
                    // Delete incomplete multipart uploads after 7 days
                    id: 'AbortIncompleteMultipartUploads',
                    abortIncompleteMultipartUploadAfter: cdk.Duration.days(7),
                },
                {
                    // Expire non-current versions after 90 days (cost optimization)
                    id: 'ExpireOldVersions',
                    noncurrentVersionExpiration: cdk.Duration.days(90),
                },
            ],

            // Development settings (change for production)
            autoDeleteObjects: true,
            removalPolicy: cdk.RemovalPolicy.DESTROY,

            // EventBridge for S3 event notifications
            eventBridgeEnabled: true,

            // CORS for presigned URL uploads
            cors: [{
                allowedMethods: [s3.HttpMethods.POST, s3.HttpMethods.PUT, s3.HttpMethods.HEAD, s3.HttpMethods.GET],
                allowedOrigins: ['*'],  // Restrict in production
                allowedHeaders: ['*'],
                maxAge: 3600,
            }],
        });

        // 2. Ingestion Queue (for async processing)
        this.ingestionQueue = new sqs.Queue(this, 'IngestionQueue', {
            queueName: `${id}-ingestion-queue`,
            visibilityTimeout: cdk.Duration.seconds(300),
            retentionPeriod: cdk.Duration.days(7),
            deadLetterQueue: {
                queue: new sqs.Queue(this, 'IngestionDLQ', {
                    queueName: `${id}-ingestion-dlq`,
                    retentionPeriod: cdk.Duration.days(14)
                }),
                maxReceiveCount: 3
            }
        });

        // ========================================================================
        // Ingestion Lambdas
        // ========================================================================

        // 3. Ingestion Processor Lambda (S3 event triggered)
        this.ingestionProcessor = new lambda.Function(this, 'IngestionProcessor', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'health_platform.ingestion.processor.handler.lambda_handler',
            code: lambda.Code.fromAsset(path.join(__dirname, '../../'), {
                exclude: lambdaCodeExcludes
            }),
            environment: {
                PROCESSED_PREFIX: 'processed/'
            },
            timeout: cdk.Duration.seconds(60),
            memorySize: 256,
            architecture: lambda.Architecture.ARM_64,
        });
        this.bucket.grantReadWrite(this.ingestionProcessor);

        // S3 Event Notification (trigger on 'landing/' prefix)
        this.bucket.addEventNotification(
            s3.EventType.OBJECT_CREATED,
            new s3n.LambdaDestination(this.ingestionProcessor),
            { prefix: 'landing/', suffix: '.ndjson' }
        );

        // 4. Webhook Ingestion Lambda
        this.webhookFunction = new lambda.Function(this, 'WebhookFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'health_platform.ingestion.webhook.handler.lambda_handler',
            code: lambda.Code.fromAsset(path.join(__dirname, '../../'), {
                exclude: lambdaCodeExcludes
            }),
            environment: {
                UPLOAD_BUCKET: this.bucket.bucketName,
                UPLOAD_PREFIX: 'incoming/fhir',
                INGESTION_QUEUE_URL: this.ingestionQueue.queueUrl
            },
            timeout: cdk.Duration.seconds(30),
            memorySize: 256,
            architecture: lambda.Architecture.ARM_64,
        });
        this.bucket.grantWrite(this.webhookFunction);
        this.ingestionQueue.grantSendMessages(this.webhookFunction);

        // 5. Presigned URL Lambda
        this.presignedUrlFunction = new lambda.Function(this, 'PresignedUrlFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'health_platform.ingestion.presigned.handler.lambda_handler',
            code: lambda.Code.fromAsset(path.join(__dirname, '../../'), {
                exclude: lambdaCodeExcludes
            }),
            environment: {
                UPLOAD_BUCKET: this.bucket.bucketName,
                UPLOAD_PREFIX: 'incoming/fhir',
                PRESIGNED_URL_EXPIRY: '3600'
            },
            timeout: cdk.Duration.seconds(10),
            memorySize: 128,
            architecture: lambda.Architecture.ARM_64,
        });
        // Grant S3 PutObject for presigned URL generation
        this.bucket.grantPut(this.presignedUrlFunction);

        // ========================================================================
        // FHIR API Lambdas
        // ========================================================================

        // 6. Patient API Lambda
        this.patientApiFunction = new lambda.Function(this, 'PatientApiFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'health_platform.api.patient.handler.lambda_handler',
            code: lambda.Code.fromAsset(path.join(__dirname, '../../'), {
                exclude: lambdaCodeExcludes
            }),
            environment: dbEnvironment,
            timeout: cdk.Duration.seconds(30),
            memorySize: 256,
            architecture: lambda.Architecture.ARM_64,
        });

        // 7. Encounter API Lambda
        this.encounterApiFunction = new lambda.Function(this, 'EncounterApiFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'health_platform.api.encounter.handler.lambda_handler',
            code: lambda.Code.fromAsset(path.join(__dirname, '../../'), {
                exclude: lambdaCodeExcludes
            }),
            environment: dbEnvironment,
            timeout: cdk.Duration.seconds(30),
            memorySize: 256,
            architecture: lambda.Architecture.ARM_64,
        });

        // 8. Observation API Lambda
        this.observationApiFunction = new lambda.Function(this, 'ObservationApiFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'health_platform.api.observation.handler.lambda_handler',
            code: lambda.Code.fromAsset(path.join(__dirname, '../../'), {
                exclude: lambdaCodeExcludes
            }),
            environment: dbEnvironment,
            timeout: cdk.Duration.seconds(30),
            memorySize: 256,
            architecture: lambda.Architecture.ARM_64,
        });

        // Grant FHIR API Lambdas permission to read Snowflake credentials
        this.secrets.grantSnowflakeRead(this.patientApiFunction);
        this.secrets.grantSnowflakeRead(this.encounterApiFunction);
        this.secrets.grantSnowflakeRead(this.observationApiFunction);

        // ========================================================================
        // API Gateway
        // ========================================================================

        // 9. Authorizer Lambda (with access to auth secrets for JWT validation)
        this.authorizerFunction = new lambda.Function(this, 'AuthorizerFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'health_platform.api.authorizer.handler.lambda_handler',
            code: lambda.Code.fromAsset(path.join(__dirname, '../../'), {
                exclude: lambdaCodeExcludes
            }),
            environment: this.secrets.getAuthorizerEnvironment(),
            architecture: lambda.Architecture.ARM_64,
        });

        // Grant Authorizer permission to read auth secrets
        this.secrets.grantAuthRead(this.authorizerFunction);

        // 10. HTTP API with Authorizer
        const authorizer = new apigwv2_authorizers.HttpLambdaAuthorizer(
            'DefaultAuthorizer',
            this.authorizerFunction,
            {
                authorizerName: 'CustomLambdaAuthorizer',
                responseTypes: [apigwv2_authorizers.HttpLambdaResponseType.SIMPLE],
            }
        );

        this.httpApi = new apigwv2.HttpApi(this, 'HealthPlatformApi', {
            apiName: 'HealthPlatformApi',
            defaultAuthorizer: authorizer,
            corsPreflight: {
                allowOrigins: ['*'],
                allowMethods: [
                    apigwv2.CorsHttpMethod.GET,
                    apigwv2.CorsHttpMethod.POST,
                    apigwv2.CorsHttpMethod.OPTIONS
                ],
                allowHeaders: ['Authorization', 'Content-Type', 'X-Request-Id'],
            }
        });

        // ========================================================================
        // API Routes
        // ========================================================================

        // Patient Routes
        const patientIntegration = new apigwv2_integrations.HttpLambdaIntegration(
            'PatientIntegration',
            this.patientApiFunction
        );
        this.httpApi.addRoutes({
            path: '/Patient',
            methods: [apigwv2.HttpMethod.GET],
            integration: patientIntegration,
        });
        this.httpApi.addRoutes({
            path: '/Patient/{id}',
            methods: [apigwv2.HttpMethod.GET],
            integration: patientIntegration,
        });

        // Encounter Routes
        const encounterIntegration = new apigwv2_integrations.HttpLambdaIntegration(
            'EncounterIntegration',
            this.encounterApiFunction
        );
        this.httpApi.addRoutes({
            path: '/Encounter',
            methods: [apigwv2.HttpMethod.GET],
            integration: encounterIntegration,
        });
        this.httpApi.addRoutes({
            path: '/Encounter/{id}',
            methods: [apigwv2.HttpMethod.GET],
            integration: encounterIntegration,
        });

        // Observation Routes
        const observationIntegration = new apigwv2_integrations.HttpLambdaIntegration(
            'ObservationIntegration',
            this.observationApiFunction
        );
        this.httpApi.addRoutes({
            path: '/Observation',
            methods: [apigwv2.HttpMethod.GET],
            integration: observationIntegration,
        });
        this.httpApi.addRoutes({
            path: '/Observation/{id}',
            methods: [apigwv2.HttpMethod.GET],
            integration: observationIntegration,
        });

        // Ingestion Routes
        const webhookIntegration = new apigwv2_integrations.HttpLambdaIntegration(
            'WebhookIntegration',
            this.webhookFunction
        );
        this.httpApi.addRoutes({
            path: '/ingestion/fhir/Bundle',
            methods: [apigwv2.HttpMethod.POST],
            integration: webhookIntegration,
        });
        this.httpApi.addRoutes({
            path: '/ingestion/jobs/{jobId}',
            methods: [apigwv2.HttpMethod.GET],
            integration: webhookIntegration,
        });

        const presignedIntegration = new apigwv2_integrations.HttpLambdaIntegration(
            'PresignedIntegration',
            this.presignedUrlFunction
        );
        this.httpApi.addRoutes({
            path: '/ingestion/upload-url',
            methods: [apigwv2.HttpMethod.POST],
            integration: presignedIntegration,
        });

        // ========================================================================
        // Outputs
        // ========================================================================

        new cdk.CfnOutput(this, 'HealthBucketName', {
            value: this.bucket.bucketName,
            description: 'Data lake bucket for FHIR files'
        });
        new cdk.CfnOutput(this, 'IngestionQueueUrl', {
            value: this.ingestionQueue.queueUrl,
            description: 'SQS queue URL for ingestion processing'
        });
        new cdk.CfnOutput(this, 'IngestionFunctionArn', {
            value: this.ingestionProcessor.functionArn
        });
        new cdk.CfnOutput(this, 'PatientApiFunctionArn', {
            value: this.patientApiFunction.functionArn
        });
        new cdk.CfnOutput(this, 'EncounterApiFunctionArn', {
            value: this.encounterApiFunction.functionArn
        });
        new cdk.CfnOutput(this, 'ObservationApiFunctionArn', {
            value: this.observationApiFunction.functionArn
        });
        new cdk.CfnOutput(this, 'WebhookFunctionArn', {
            value: this.webhookFunction.functionArn
        });
        new cdk.CfnOutput(this, 'PresignedUrlFunctionArn', {
            value: this.presignedUrlFunction.functionArn
        });
        new cdk.CfnOutput(this, 'ApiEndpoint', {
            value: this.httpApi.apiEndpoint,
            description: 'HTTP API Endpoint URL'
        });

        // Secrets outputs
        new cdk.CfnOutput(this, 'SnowflakeSecretArn', {
            value: this.secrets.snowflakeSecret.secretArn,
            description: 'ARN of Snowflake credentials secret'
        });
        new cdk.CfnOutput(this, 'AuthSecretArn', {
            value: this.secrets.authSecret.secretArn,
            description: 'ARN of authentication secret'
        });
    }
}
