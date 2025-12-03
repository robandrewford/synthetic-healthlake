import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as glue from 'aws-cdk-lib/aws-glue';
import * as logs from 'aws-cdk-lib/aws-logs';

export class FhirOmopStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const vpc = new ec2.Vpc(this, 'FhirOmopVpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        { name: 'public', subnetType: ec2.SubnetType.PUBLIC },
        { name: 'private-app', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }
      ]
    });

    const dataBucket = new s3.Bucket(this, 'FhirOmopDataBucket', {
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL
    });

    const glueDb = new glue.Database(this, 'FhirOmopGlueDatabase', {
      databaseName: 'fhir_omop'
    });

    const cluster = new ecs.Cluster(this, 'FhirOmopCluster', {
      vpc,
      containerInsights: true
    });

    const taskRole = new iam.Role(this, 'FhirOmopTaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com')
    });

    dataBucket.grantReadWrite(taskRole);

    taskRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy')
    );

    const executionRole = new iam.Role(this, 'FhirOmopExecRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy')
      ]
    });

    const logGroup = new logs.LogGroup(this, 'FhirOmopTaskLogs', {
      retention: logs.RetentionDays.ONE_WEEK
    });

    const syntheticTaskDef = new ecs.FargateTaskDefinition(this, 'SyntheticTaskDef', {
      cpu: 1024,
      memoryLimitMiB: 2048,
      taskRole,
      executionRole
    });

    syntheticTaskDef.addContainer('SyntheticContainer', {
      image: ecs.ContainerImage.fromRegistry('your-registry/synthetic-generator:latest'),
      logging: ecs.LogDrivers.awsLogs({
        logGroup,
        streamPrefix: 'synthetic'
      }),
      environment: {
        S3_DATA_BUCKET: dataBucket.bucketName,
        GLUE_DB_NAME: glueDb.databaseName
      }
    });

    const dbtTaskDef = new ecs.FargateTaskDefinition(this, 'DbtTaskDef', {
      cpu: 1024,
      memoryLimitMiB: 2048,
      taskRole,
      executionRole
    });

    dbtTaskDef.addContainer('DbtContainer', {
      image: ecs.ContainerImage.fromRegistry('your-registry/dbt-fhir-omop:latest'),
      logging: ecs.LogDrivers.awsLogs({
        logGroup,
        streamPrefix: 'dbt'
      }),
      environment: {
        S3_DATA_BUCKET: dataBucket.bucketName,
        GLUE_DB_NAME: glueDb.databaseName,
        DBT_TARGET: 'dev'
      }
    });

    new cdk.CfnOutput(this, 'DataBucketName', { value: dataBucket.bucketName });
    new cdk.CfnOutput(this, 'GlueDatabaseName', { value: glueDb.databaseName });
    new cdk.CfnOutput(this, 'ClusterName', { value: cluster.clusterName });
  }
}
