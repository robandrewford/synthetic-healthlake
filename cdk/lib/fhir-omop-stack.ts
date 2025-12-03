import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as glue from 'aws-cdk-lib/aws-glue';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import { StepFunctionsPipeline } from './step-functions-pipeline';

export class FhirOmopStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly cluster: ecs.Cluster;
  public readonly dataBucket: s3.Bucket;
  public readonly glueDb: glue.CfnDatabase;
  public readonly taskSecurityGroup: ec2.SecurityGroup;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // 1. VPC with Public and Private Subnets
    this.vpc = new ec2.Vpc(this, 'FhirOmopVpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        { name: 'public', subnetType: ec2.SubnetType.PUBLIC },
        { name: 'private-app', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }
      ]
    });

    // 2. VPC Endpoints for Security & Privacy
    this.vpc.addGatewayEndpoint('S3Endpoint', {
      service: ec2.GatewayVpcEndpointAwsService.S3
    });

    const interfaceEndpoints = {
      'Glue': ec2.InterfaceVpcEndpointAwsService.GLUE,
      'Athena': ec2.InterfaceVpcEndpointAwsService.ATHENA,
      'CloudWatch': ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
      'ECR': ec2.InterfaceVpcEndpointAwsService.ECR,
      'ECR_DOCKER': ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER
    };

    Object.entries(interfaceEndpoints).forEach(([name, service]) => {
      this.vpc.addInterfaceEndpoint(`${name}Endpoint`, {
        service,
        subnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }
      });
    });

    // 3. KMS Encryption
    const key = new kms.Key(this, 'DataKey', {
      enableKeyRotation: true,
      alias: 'alias/fhir-omop-data-key',
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // 4. S3 Bucket with Encryption
    this.dataBucket = new s3.Bucket(this, 'FhirOmopDataBucket', {
      versioned: true,
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: key,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true
    });

    // 5. Glue Database
    this.glueDb = new glue.CfnDatabase(this, 'FhirOmopGlueDatabase', {
      catalogId: this.account,
      databaseInput: {
        name: 'fhir_omop'
      }
    });

    // 6. Security Groups
    this.taskSecurityGroup = new ec2.SecurityGroup(this, 'TaskSecurityGroup', {
      vpc: this.vpc,
      description: 'Security group for ECS tasks',
      allowAllOutbound: true
    });

    // 7. ECS Cluster
    this.cluster = new ecs.Cluster(this, 'FhirOmopCluster', {
      vpc: this.vpc,
      containerInsights: true
    });

    // 8. IAM Roles (Least Privilege)
    const taskRole = new iam.Role(this, 'FhirOmopTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com')
    });

    this.dataBucket.grantReadWrite(taskRole);
    key.grantEncryptDecrypt(taskRole);

    // Grant Glue permissions
    taskRole.addToPolicy(new iam.PolicyStatement({
      actions: ['glue:GetDatabase', 'glue:GetTable', 'glue:CreateTable', 'glue:UpdateTable'],
      resources: [
        `arn:aws:glue:${this.region}:${this.account}:catalog`,
        `arn:aws:glue:${this.region}:${this.account}:database/${this.glueDb.ref}`,
        `arn:aws:glue:${this.region}:${this.account}:table/${this.glueDb.ref}/*`
      ]
    }));

    const executionRole = new iam.Role(this, 'FhirOmopExecRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy')
      ]
    });

    // 9. Logging & Monitoring
    const logGroup = new logs.LogGroup(this, 'FhirOmopTaskLogs', {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // 10. Task Definitions
    const syntheticTaskDef = new ecs.FargateTaskDefinition(this, 'SyntheticTaskDef', {
      cpu: 1024,
      memoryLimitMiB: 2048,
      taskRole,
      executionRole
    });

    syntheticTaskDef.addContainer('SyntheticContainer', {
      image: ecs.ContainerImage.fromRegistry(this.node.tryGetContext('syntheticImage') || 'public.ecr.aws/docker/library/python:3.11'),
      logging: ecs.LogDrivers.awsLogs({
        logGroup,
        streamPrefix: 'synthetic'
      }),
      environment: {
        S3_DATA_BUCKET: this.dataBucket.bucketName,
        GLUE_DB_NAME: this.glueDb.ref
      }
    });

    const dbtTaskDef = new ecs.FargateTaskDefinition(this, 'DbtTaskDef', {
      cpu: 1024,
      memoryLimitMiB: 2048,
      taskRole,
      executionRole
    });

    dbtTaskDef.addContainer('DbtContainer', {
      image: ecs.ContainerImage.fromRegistry(this.node.tryGetContext('dbtImage') || 'public.ecr.aws/docker/library/python:3.11'),
      logging: ecs.LogDrivers.awsLogs({
        logGroup,
        streamPrefix: 'dbt'
      }),
      environment: {
        S3_DATA_BUCKET: this.dataBucket.bucketName,
        GLUE_DB_NAME: this.glueDb.ref,
        DBT_TARGET: 'dev'
      }
    });

    // 11. Alarms
    new cloudwatch.Alarm(this, 'TaskFailureAlarm', {
      metric: this.cluster.metric('TaskFailures'),
      threshold: 1,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
    });

    // 12. Outputs
    new cdk.CfnOutput(this, 'DataBucketName', { value: this.dataBucket.bucketName });
    new cdk.CfnOutput(this, 'GlueDatabaseName', { value: this.glueDb.ref });
    new cdk.CfnOutput(this, 'ClusterName', { value: this.cluster.clusterName });
    new cdk.CfnOutput(this, 'KmsKeyId', { value: key.keyId });
    new cdk.CfnOutput(this, 'SyntheticTaskDefArn', { value: syntheticTaskDef.taskDefinitionArn });
    new cdk.CfnOutput(this, 'DbtTaskDefArn', { value: dbtTaskDef.taskDefinitionArn });

    // 13. Tagging
    cdk.Tags.of(this).add('Project', 'fhir-omop-reference');
    cdk.Tags.of(this).add('Environment', 'dev');
    cdk.Tags.of(this).add('ManagedBy', 'CDK');

    // 14. Step Functions Pipeline
    new StepFunctionsPipeline(this, 'Pipeline', {
      cluster: this.cluster,
      syntheticTaskDef: syntheticTaskDef,
      dbtTaskDef: dbtTaskDef,
      dataBucketName: this.dataBucket.bucketName
    });
  }
}
