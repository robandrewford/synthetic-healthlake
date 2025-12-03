#!/usr/bin/env ts-node
import * as cdk from 'aws-cdk-lib';
import { FhirOmopStack } from '../lib/fhir-omop-stack';

const app = new cdk.App();

new FhirOmopStack(app, 'FhirOmopStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-west-2'
  }
});
