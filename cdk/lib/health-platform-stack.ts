import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as path from 'path';

export class HealthPlatformStack extends cdk.Stack {
    public readonly bucket: s3.Bucket;
    public readonly ingestionProcessor: lambda.Function;

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

        // 5. Outputs
        new cdk.CfnOutput(this, 'HealthBucketName', {
            value: this.bucket.bucketName,
            description: 'Landing bucket for NDJSON files'
        });
        new cdk.CfnOutput(this, 'IngestionFunctionArn', {
            value: this.ingestionProcessor.functionArn
        });
    }
}
