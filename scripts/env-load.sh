#!/usr/bin/env bash
# Health Platform - Environment Loader
# Fallback script when direnv is not available
#
# Usage:
#   source scripts/env-load.sh
#   # or
#   . scripts/env-load.sh
#
# See: docs/development/env-variable-naming-convention.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if .env file exists
if [[ ! -f "${ENV_FILE}" ]]; then
    log_error ".env file not found at ${ENV_FILE}"
    log_error "Copy .env.example to .env and fill in your credentials:"
    log_error "  cp ${PROJECT_ROOT}/.env.example ${ENV_FILE}"
    return 1 2>/dev/null || exit 1
fi

# Load .env file - export each line that looks like a variable assignment
log_info "Loading environment from ${ENV_FILE}..."

while IFS= read -r line || [[ -n "${line}" ]]; do
    # Skip empty lines and comments
    [[ -z "${line}" ]] && continue
    [[ "${line}" =~ ^[[:space:]]*# ]] && continue

    # Remove leading/trailing whitespace
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"

    # Skip if not a valid assignment
    [[ ! "${line}" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] && continue

    # Export the variable
    export "${line?}"
done < "${ENV_FILE}"

# Validate required variables
REQUIRED_VARS=(
    "HP_SNF_ACCT"
    "HP_SNF_USER"
    "HP_SNF_PASS"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        MISSING_VARS+=("${var}")
    fi
done

if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
    log_error "Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        log_error "  - ${var}"
    done
    return 1 2>/dev/null || exit 1
fi

# Set up tool compatibility aliases
export AWS_PROFILE="${HP_AWS_PROFILE:-default}"
export AWS_DEFAULT_REGION="${HP_AWS_REGION:-us-east-1}"
export DBT_PROFILES_DIR="${PROJECT_ROOT}/dbt/snowflake"

# Snowflake CLI (snowsql) compatibility
export SNOWSQL_ACCOUNT="${HP_SNF_ACCT:-}"
export SNOWSQL_USER="${HP_SNF_USER:-}"
export SNOWSQL_PWD="${HP_SNF_PASS:-}"
export SNOWSQL_WAREHOUSE="${HP_SNF_WH:-COMPUTE_WH}"
export SNOWSQL_DATABASE="${HP_SNF_DB:-HEALTH_PLATFORM_DB}"
export SNOWSQL_SCHEMA="${HP_SNF_SCHEMA:-RAW}"
export SNOWSQL_ROLE="${HP_SNF_ROLE:-ACCOUNTADMIN}"

log_info "Environment loaded successfully!"
log_info "  Snowflake Account: ${HP_SNF_ACCT}"
log_info "  Snowflake User: ${HP_SNF_USER}"
log_info "  AWS Profile: ${AWS_PROFILE}"
log_info "  dbt Profiles: ${DBT_PROFILES_DIR}"
