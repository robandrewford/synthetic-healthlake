#!/usr/bin/env bash
# Health Platform - dbt Runner
# Wrapper script that loads environment and runs dbt commands
#
# Usage:
#   ./scripts/run-dbt.sh run
#   ./scripts/run-dbt.sh test
#   ./scripts/run-dbt.sh build --select my_model
#
# See: docs/development/env-variable-naming-convention.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DBT_DIR="${PROJECT_ROOT}/dbt/snowflake"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_cmd() { echo -e "${BLUE}[CMD]${NC} $1"; }

# Load environment if not already loaded
if [[ -z "${HP_SNF_ACCT:-}" ]]; then
    log_info "Loading environment..."
    # shellcheck source=env-load.sh
    source "${SCRIPT_DIR}/env-load.sh"
fi

# Verify we're in the right directory
if [[ ! -f "${DBT_DIR}/dbt_project.yml" ]]; then
    log_error "dbt project not found at ${DBT_DIR}"
    exit 1
fi

# Set dbt-specific environment variables
export DBT_PROFILES_DIR="${DBT_DIR}"

# Show help if no arguments
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <dbt-command> [options]"
    echo ""
    echo "Examples:"
    echo "  $0 run                    # Run all models"
    echo "  $0 test                   # Run all tests"
    echo "  $0 build                  # Run and test all models"
    echo "  $0 run --select my_model  # Run specific model"
    echo "  $0 docs generate          # Generate documentation"
    echo "  $0 debug                  # Test connection"
    echo ""
    echo "Environment:"
    echo "  HP_SNF_ACCT:   ${HP_SNF_ACCT:-not set}"
    echo "  HP_SNF_USER:   ${HP_SNF_USER:-not set}"
    echo "  HP_SNF_DB:     ${HP_SNF_DB:-not set}"
    echo "  HP_DBT_TARGET: ${HP_DBT_TARGET:-dev}"
    exit 0
fi

# Build the dbt command
DBT_TARGET="${HP_DBT_TARGET:-dev}"
DBT_CMD="dbt"

# Check if we should use uv to run dbt
if command -v uv &> /dev/null && [[ -f "${PROJECT_ROOT}/pyproject.toml" ]]; then
    DBT_CMD="uv run dbt"
fi

# Change to dbt directory
cd "${DBT_DIR}"

# Run dbt with provided arguments
log_info "Running dbt in ${DBT_DIR}"
log_info "Target: ${DBT_TARGET}"
log_cmd "${DBT_CMD} $* --target ${DBT_TARGET}"

# Execute dbt
# shellcheck disable=SC2086
${DBT_CMD} "$@" --target "${DBT_TARGET}"
