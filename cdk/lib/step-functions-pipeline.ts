import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as logs from 'aws-cdk-lib/aws-logs';

export interface PipelineProps {
    cluster: ecs.Cluster;
    syntheticTaskDef: ecs.FargateTaskDefinition;
    dbtTaskDef: ecs.FargateTaskDefinition;
    dataBucketName: string;
}

export class StepFunctionsPipeline extends Construct {
    public readonly stateMachine: sfn.StateMachine;

    constructor(scope: Construct, id: string, props: PipelineProps) {
        super(scope, id);

        const logGroup = new logs.LogGroup(this, 'PipelineLogs', {
            retention: logs.RetentionDays.ONE_WEEK,
            removalPolicy: cdk.RemovalPolicy.DESTROY
        });

        // 1. Generate Synthetic Data
        const generateTask = new tasks.EcsRunTask(this, 'GenerateData', {
            cluster: props.cluster,
            taskDefinition: props.syntheticTaskDef,
            launchTarget: new tasks.EcsFargateLaunchTarget(),
            containerOverrides: [{
                containerDefinition: props.syntheticTaskDef.defaultContainer!,
                command: ['/app/scripts/run_synthetic_pipeline.sh'],
                environment: [
                    { name: 'PIPELINE_RUN_ID', value: sfn.JsonPath.stringAt('$$.Execution.Name') },
                    { name: 'S3_DATA_BUCKET', value: props.dataBucketName },
                    { name: 'PATIENT_COUNT', value: '100' }
                ]
            }],
            resultPath: '$.generateResult'
        });

        // 2. Flatten FHIR
        const flattenTask = new tasks.EcsRunTask(this, 'FlattenFHIR', {
            cluster: props.cluster,
            taskDefinition: props.syntheticTaskDef,
            launchTarget: new tasks.EcsFargateLaunchTarget(),
            containerOverrides: [{
                containerDefinition: props.syntheticTaskDef.defaultContainer!,
                command: ['echo', 'Flattening handled in generate step'],
                environment: [
                    { name: 'PIPELINE_RUN_ID', value: sfn.JsonPath.stringAt('$$.Execution.Name') }
                ]
            }],
            resultPath: '$.flattenResult'
        });

        // 3. Convert OMOP
        const convertTask = new tasks.EcsRunTask(this, 'ConvertOMOP', {
            cluster: props.cluster,
            taskDefinition: props.syntheticTaskDef,
            launchTarget: new tasks.EcsFargateLaunchTarget(),
            containerOverrides: [{
                containerDefinition: props.syntheticTaskDef.defaultContainer!,
                command: ['echo', 'Conversion handled in generate step'],
                environment: [
                    { name: 'PIPELINE_RUN_ID', value: sfn.JsonPath.stringAt('$$.Execution.Name') }
                ]
            }],
            resultPath: '$.convertResult'
        });

        // 4. Run dbt
        const dbtTask = new tasks.EcsRunTask(this, 'RunDbt', {
            cluster: props.cluster,
            taskDefinition: props.dbtTaskDef,
            launchTarget: new tasks.EcsFargateLaunchTarget(),
            containerOverrides: [{
                containerDefinition: props.dbtTaskDef.defaultContainer!,
                command: ['/app/scripts/run_dbt_pipeline.sh'],
                environment: [
                    { name: 'PIPELINE_RUN_ID', value: sfn.JsonPath.stringAt('$$.Execution.Name') },
                    { name: 'S3_DATA_BUCKET', value: props.dataBucketName }
                ]
            }],
            resultPath: '$.dbtResult'
        });

        // Chain tasks
        const definition = generateTask
            .next(flattenTask)
            .next(convertTask)
            .next(dbtTask);

        this.stateMachine = new sfn.StateMachine(this, 'FhirOmopPipeline', {
            definitionBody: sfn.DefinitionBody.fromChainable(definition),
            timeout: cdk.Duration.hours(2),
            logs: {
                destination: logGroup,
                level: sfn.LogLevel.ALL
            }
        });

        new cdk.CfnOutput(scope, 'StateMachineArn', { value: this.stateMachine.stateMachineArn });
    }
}
