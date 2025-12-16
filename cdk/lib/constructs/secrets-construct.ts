import { Construct } from 'constructs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as ecs from 'aws-cdk-lib/aws-ecs';

/**
 * Secrets structure for Snowflake database credentials.
 * This matches the expected JSON structure in AWS Secrets Manager.
 */
export interface SnowflakeSecretFields {
  readonly account: string;
  readonly user: string;
  readonly password: string;
  readonly role: string;
  readonly warehouse: string;
  readonly database: string;
}

/**
 * Secrets structure for JWT/API authentication.
 */
export interface AuthSecretFields {
  readonly jwtSecret: string;
  readonly apiKeyHash?: string;
}

/**
 * Properties for the PlatformSecrets construct.
 */
export interface PlatformSecretsProps {
  /**
   * Name prefix for all secrets (e.g., 'health-platform').
   * Secrets will be named as: {prefix}/snowflake, {prefix}/auth, etc.
   */
  readonly secretNamePrefix: string;

  /**
   * Optional: Create secrets with initial placeholder values.
   * Set to false if secrets already exist and you just want references.
   * @default true
   */
  readonly createSecrets?: boolean;

  /**
   * Optional: KMS key ARN for encrypting secrets.
   * If not provided, AWS managed key is used.
   */
  readonly encryptionKeyArn?: string;
}

/**
 * PlatformSecrets - Centralized secrets management construct.
 *
 * This construct creates and manages secrets for the health platform:
 * - Snowflake database credentials (for API Lambdas and dbt ECS tasks)
 * - Authentication secrets (JWT signing key, API key hash)
 *
 * Usage:
 * ```typescript
 * const secrets = new PlatformSecrets(this, 'Secrets', {
 *   secretNamePrefix: 'health-platform'
 * });
 *
 * // Grant Lambda access to Snowflake credentials
 * secrets.grantSnowflakeRead(myLambdaFunction);
 *
 * // Get environment variables for Lambda
 * const env = secrets.getLambdaEnvironment();
 *
 * // Get secrets for ECS task
 * const ecsSecrets = secrets.getEcsSecrets();
 * ```
 */
export class PlatformSecrets extends Construct {
  /**
   * The Snowflake credentials secret.
   * JSON structure: { account, user, password, role, warehouse, database }
   */
  public readonly snowflakeSecret: secretsmanager.ISecret;

  /**
   * The authentication secret (JWT, API keys).
   * JSON structure: { jwtSecret, apiKeyHash }
   */
  public readonly authSecret: secretsmanager.ISecret;

  /**
   * The secret name prefix used for all secrets.
   */
  public readonly secretNamePrefix: string;

  constructor(scope: Construct, id: string, props: PlatformSecretsProps) {
    super(scope, id);

    this.secretNamePrefix = props.secretNamePrefix;
    const createSecrets = props.createSecrets ?? true;

    if (createSecrets) {
      // Create Snowflake credentials secret with placeholder values
      // IMPORTANT: Update these values after deployment via AWS Console or CLI
      this.snowflakeSecret = new secretsmanager.Secret(this, 'SnowflakeSecret', {
        secretName: `${props.secretNamePrefix}/snowflake`,
        description: 'Snowflake database credentials for Health Platform',
        generateSecretString: {
          secretStringTemplate: JSON.stringify({
            account: 'PLACEHOLDER_ACCOUNT.us-east-1',
            user: 'PLACEHOLDER_USER',
            role: 'HEALTH_PLATFORM_ROLE',
            warehouse: 'COMPUTE_WH',
            database: 'HEALTH_PLATFORM_DB',
          }),
          generateStringKey: 'password',
          excludePunctuation: false,
          passwordLength: 32,
        },
      });

      // Create authentication secret
      this.authSecret = new secretsmanager.Secret(this, 'AuthSecret', {
        secretName: `${props.secretNamePrefix}/auth`,
        description: 'Authentication secrets for Health Platform API',
        generateSecretString: {
          secretStringTemplate: JSON.stringify({
            apiKeyHash: '',
          }),
          generateStringKey: 'jwtSecret',
          excludePunctuation: false,
          passwordLength: 64,
        },
      });
    } else {
      // Reference existing secrets by name
      this.snowflakeSecret = secretsmanager.Secret.fromSecretNameV2(
        this,
        'SnowflakeSecret',
        `${props.secretNamePrefix}/snowflake`
      );

      this.authSecret = secretsmanager.Secret.fromSecretNameV2(
        this,
        'AuthSecret',
        `${props.secretNamePrefix}/auth`
      );
    }
  }

  /**
   * Grant read access to Snowflake credentials for a Lambda function.
   * This adds the necessary IAM permissions.
   */
  public grantSnowflakeRead(lambdaFunction: lambda.IFunction): void {
    this.snowflakeSecret.grantRead(lambdaFunction);
  }

  /**
   * Grant read access to authentication secrets for a Lambda function.
   */
  public grantAuthRead(lambdaFunction: lambda.IFunction): void {
    this.authSecret.grantRead(lambdaFunction);
  }

  /**
   * Grant read access to Snowflake credentials for an IAM role (e.g., ECS task role).
   */
  public grantSnowflakeReadToRole(role: iam.IRole): void {
    this.snowflakeSecret.grantRead(role);
  }

  /**
   * Get environment variables for Lambda functions that use Snowflake.
   * The Lambda should use AWS SDK to fetch the actual secret values at runtime.
   *
   * @returns Environment variables object
   */
  public getLambdaEnvironment(): { [key: string]: string } {
    return {
      SNOWFLAKE_SECRET_ARN: this.snowflakeSecret.secretArn,
      SNOWFLAKE_SECRET_NAME: `${this.secretNamePrefix}/snowflake`,
    };
  }

  /**
   * Get environment variables for Lambda authorizer function.
   *
   * @returns Environment variables object
   */
  public getAuthorizerEnvironment(): { [key: string]: string } {
    return {
      AUTH_SECRET_ARN: this.authSecret.secretArn,
      AUTH_SECRET_NAME: `${this.secretNamePrefix}/auth`,
    };
  }

  /**
   * Get ECS secrets mapping for Snowflake credentials.
   * These can be passed to container definitions to inject secrets as environment variables.
   *
   * The secret JSON fields are mapped to individual environment variables:
   * - HP_SNF_ACCT <- snowflake:account
   * - HP_SNF_USER <- snowflake:user
   * - HP_SNF_PASS <- snowflake:password
   * - HP_SNF_ROLE <- snowflake:role
   * - HP_SNF_WH <- snowflake:warehouse
   * - HP_SNF_DB <- snowflake:database
   *
   * See: docs/development/env-variable-naming-convention.md
   *
   * @returns Map of environment variable name to ECS Secret
   */
  public getEcsSnowflakeSecrets(): { [key: string]: ecs.Secret } {
    return {
      HP_SNF_ACCT: ecs.Secret.fromSecretsManager(this.snowflakeSecret, 'account'),
      HP_SNF_USER: ecs.Secret.fromSecretsManager(this.snowflakeSecret, 'user'),
      HP_SNF_PASS: ecs.Secret.fromSecretsManager(this.snowflakeSecret, 'password'),
      HP_SNF_ROLE: ecs.Secret.fromSecretsManager(this.snowflakeSecret, 'role'),
      HP_SNF_WH: ecs.Secret.fromSecretsManager(this.snowflakeSecret, 'warehouse'),
      HP_SNF_DB: ecs.Secret.fromSecretsManager(this.snowflakeSecret, 'database'),
    };
  }

  /**
   * Get ECS secrets mapping for authentication.
   *
   * @returns Map of environment variable name to ECS Secret
   */
  public getEcsAuthSecrets(): { [key: string]: ecs.Secret } {
    return {
      JWT_SECRET: ecs.Secret.fromSecretsManager(this.authSecret, 'jwtSecret'),
    };
  }
}

/**
 * Helper function to create a policy statement for reading specific secret fields.
 * Useful when you need fine-grained access control.
 */
export function createSecretReadPolicy(secretArn: string): iam.PolicyStatement {
  return new iam.PolicyStatement({
    effect: iam.Effect.ALLOW,
    actions: [
      'secretsmanager:GetSecretValue',
      'secretsmanager:DescribeSecret',
    ],
    resources: [secretArn],
  });
}
