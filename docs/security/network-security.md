# Network Security Configuration

This document describes the network security architecture for Synthetic HealthLake, including VPC configuration, security group rules, and network boundaries.

## Network Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                              AWS VPC (10.0.0.0/16)                      │
│                                                                         │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐   │
│  │     Public Subnets           │  │     Private Subnets          │   │
│  │     (10.0.0.0/20)            │  │     (10.0.128.0/20)          │   │
│  │                              │  │                              │   │
│  │  ┌─────────────────────┐    │  │  ┌─────────────────────┐    │   │
│  │  │   NAT Gateway       │    │  │  │   ECS Fargate       │    │   │
│  │  │   (Outbound only)   │    │  │  │   (Synthea Gen)     │    │   │
│  │  └─────────────────────┘    │  │  └─────────────────────┘    │   │
│  │                              │  │                              │   │
│  │  ┌─────────────────────┐    │  │  ┌─────────────────────┐    │   │
│  │  │   ALB               │    │  │  │   Lambda Functions  │    │   │
│  │  │   (If API exposed)  │    │  │  │   (FHIR API)        │    │   │
│  │  └─────────────────────┘    │  │  └─────────────────────┘    │   │
│  └──────────────────────────────┘  └──────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     VPC Endpoints (Private)                       │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │  │
│  │  │   S3    │ │  ECR    │ │  Logs   │ │ Secrets │ │  SSM    │   │  │
│  │  │(Gateway)│ │(Iface)  │ │(Iface)  │ │ Manager │ │(Iface)  │   │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Security Groups

### ECS Fargate Security Group

Purpose: Controls network access for Synthea data generation containers.

| Rule Type | Protocol | Port Range | Source/Destination | Description |
|-----------|----------|------------|-------------------|-------------|
| Egress | HTTPS | 443 | VPC Endpoints SG | ECR, Logs, Secrets |
| Egress | HTTPS | 443 | S3 Prefix List | S3 access via gateway |
| Egress | HTTPS | 443 | 0.0.0.0/0 | External dependencies (via NAT) |

```typescript
// CDK Definition
const ecsSg = new ec2.SecurityGroup(this, 'EcsSg', {
  vpc,
  description: 'Security group for ECS Fargate tasks',
  allowAllOutbound: false,
});

// Allow outbound to VPC endpoints
ecsSg.addEgressRule(
  vpcEndpointsSg,
  ec2.Port.tcp(443),
  'HTTPS to VPC endpoints'
);

// Allow outbound to S3 via gateway endpoint
ecsSg.addEgressRule(
  ec2.Peer.prefixList(s3PrefixListId),
  ec2.Port.tcp(443),
  'HTTPS to S3'
);
```

### VPC Endpoints Security Group

Purpose: Controls access to VPC interface endpoints.

| Rule Type | Protocol | Port Range | Source/Destination | Description |
|-----------|----------|------------|-------------------|-------------|
| Ingress | HTTPS | 443 | ECS Security Group | Allow ECS access |
| Ingress | HTTPS | 443 | Lambda Security Group | Allow Lambda access |

```typescript
// CDK Definition
const vpcEndpointsSg = new ec2.SecurityGroup(this, 'VpcEndpointsSg', {
  vpc,
  description: 'Security group for VPC endpoints',
  allowAllOutbound: false,
});

// Allow inbound from ECS
vpcEndpointsSg.addIngressRule(
  ecsSg,
  ec2.Port.tcp(443),
  'HTTPS from ECS tasks'
);
```

### Lambda Security Group

Purpose: Controls network access for Lambda functions within VPC.

| Rule Type | Protocol | Port Range | Source/Destination | Description |
|-----------|----------|------------|-------------------|-------------|
| Egress | HTTPS | 443 | VPC Endpoints SG | AWS service access |
| Egress | HTTPS | 443 | S3 Prefix List | S3 data access |
| Egress | Custom | 443 | Snowflake CIDR | Database connectivity |

```typescript
// CDK Definition
const lambdaSg = new ec2.SecurityGroup(this, 'LambdaSg', {
  vpc,
  description: 'Security group for Lambda functions',
  allowAllOutbound: false,
});

// Restrict to specific egress paths
lambdaSg.addEgressRule(
  vpcEndpointsSg,
  ec2.Port.tcp(443),
  'HTTPS to VPC endpoints'
);
```

## VPC Endpoints Configuration

### Required Interface Endpoints

The following interface endpoints provide private connectivity to AWS services:

| Endpoint | Service | Purpose |
|----------|---------|---------|
| ecr.api | ECR API | Container image metadata |
| ecr.dkr | ECR Docker | Container image pulls |
| logs | CloudWatch Logs | Log delivery |
| secretsmanager | Secrets Manager | Credential retrieval |
| ssm | Systems Manager | Parameter store access |

### Gateway Endpoints

| Endpoint | Service | Purpose |
|----------|---------|---------|
| s3 | Amazon S3 | Data storage (no charge) |

### CDK Implementation

```typescript
// S3 Gateway Endpoint (no cost)
vpc.addGatewayEndpoint('S3Endpoint', {
  service: ec2.GatewayVpcEndpointAwsService.S3,
  subnets: [{ subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }],
});

// Interface Endpoints
const interfaceEndpoints = [
  { id: 'EcrApiEndpoint', service: ec2.InterfaceVpcEndpointAwsService.ECR },
  { id: 'EcrDkrEndpoint', service: ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER },
  { id: 'LogsEndpoint', service: ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS },
  { id: 'SecretsEndpoint', service: ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER },
];

interfaceEndpoints.forEach(({ id, service }) => {
  vpc.addInterfaceEndpoint(id, {
    service,
    securityGroups: [vpcEndpointsSg],
    subnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
  });
});
```

## Network Access Control Lists (NACLs)

NACLs provide an additional layer of security at the subnet level.

### Private Subnet NACL

| Rule # | Type | Protocol | Port Range | Source | Allow/Deny |
|--------|------|----------|------------|--------|------------|
| 100 | Inbound | TCP | 443 | VPC CIDR | Allow |
| 110 | Inbound | TCP | 1024-65535 | 0.0.0.0/0 | Allow |
| 100 | Outbound | TCP | 443 | 0.0.0.0/0 | Allow |
| 110 | Outbound | TCP | 1024-65535 | VPC CIDR | Allow |
| * | All | All | All | 0.0.0.0/0 | Deny |

## Data Flow Patterns

### Synthetic Data Generation Flow

```text
1. Step Functions triggers ECS task
2. ECS pulls container image via ECR endpoint
3. Container retrieves secrets via Secrets Manager endpoint
4. Synthea generates data locally
5. Container uploads to S3 via gateway endpoint
6. CloudWatch logs sent via Logs endpoint
```

### API Request Flow

```text
1. API Gateway receives request
2. Lambda function invoked in VPC
3. Lambda retrieves secrets via Secrets Manager endpoint
4. Lambda queries data from S3 via gateway endpoint
5. Response returned through API Gateway
```

## Network Monitoring

### VPC Flow Logs

Enable VPC Flow Logs for network traffic analysis:

```typescript
// CDK Definition
new ec2.FlowLog(this, 'VpcFlowLog', {
  resourceType: ec2.FlowLogResourceType.fromVpc(vpc),
  trafficType: ec2.FlowLogTrafficType.ALL,
  destination: ec2.FlowLogDestination.toCloudWatchLogs(
    logGroup,
    flowLogRole
  ),
});
```

### CloudWatch Metrics

Monitor these key network metrics:

- `AWS/VPC` - VPC-level metrics
- `AWS/NATGateway` - NAT Gateway throughput and connections
- `AWS/PrivateLink` - VPC endpoint metrics

## Security Best Practices

### Network Segmentation

- [ ] Separate public and private subnets
- [ ] Use VPC endpoints to avoid internet traversal
- [ ] Implement least-privilege security groups
- [ ] Enable VPC Flow Logs for auditing

### Egress Control

- [ ] Restrict outbound traffic to known destinations
- [ ] Use VPC endpoints instead of NAT for AWS services
- [ ] Monitor for unexpected egress patterns
- [ ] Consider AWS Network Firewall for advanced filtering

### Endpoint Security

- [ ] Apply security groups to VPC endpoints
- [ ] Use endpoint policies to restrict access
- [ ] Enable private DNS for endpoints
- [ ] Monitor endpoint usage with CloudWatch

## Compliance Considerations

### HIPAA Requirements

For healthcare data workloads:

- Enable encryption in transit (TLS 1.2+)
- Use VPC endpoints to keep traffic within AWS network
- Implement comprehensive logging
- Restrict access to minimum necessary

### Audit Trail

All network changes should be tracked via:

- AWS CloudTrail for API calls
- VPC Flow Logs for network traffic
- Config rules for security group changes

## Related Documentation

- [IAM Best Practices](iam-best-practices.md)
- [Secrets Management](secrets-management.md)
- [Security Checklist](security-checklist.md)
- [Deployment Checklist](deployment-checklist.md)
