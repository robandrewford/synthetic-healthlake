#!/usr/bin/env bash
# =============================================================================
# cleanup.sh - Safely destroy AWS resources and local generated data
# =============================================================================
# Usage:
#   ./scripts/cleanup.sh [OPTIONS]
#
# Options:
#   --local          Clean local generated data only
#   --aws            Destroy AWS resources (CDK destroy)
#   --s3             Empty S3 buckets
#   --all            Clean everything (local + AWS)
#   --dry-run        Show what would be deleted without deleting
#   -y, --yes        Skip confirmation prompts
#   -h, --help       Show this help message
#
# Examples:
#   ./scripts/cleanup.sh --local           # Clean local output only
#   ./scripts/cleanup.sh --aws --dry-run   # Preview AWS destruction
#   ./scripts/cleanup.sh --all -y          # Clean everything without prompts
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Options
CLEAN_LOCAL=false
CLEAN_AWS=false
CLEAN_S3=false
DRY_RUN=false
SKIP_CONFIRM=false

# Logging
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }
log_dry() { echo -e "${YELLOW}[DRY-RUN]${NC} Would: $1"; }

# Help
show_help() {
    cat << 'EOF'
cleanup.sh - Safely destroy AWS resources and local generated data

Usage:
  ./scripts/cleanup.sh [OPTIONS]

Options:
  --local          Clean local generated data only
  --aws            Destroy AWS resources (CDK destroy)
  --s3             Empty S3 buckets
  --all            Clean everything (local + AWS)
  --dry-run        Show what would be deleted without deleting
  -y, --yes        Skip confirmation prompts
  -h, --help       Show this help message

Examples:
  ./scripts/cleanup.sh --local           # Clean local output only
  ./scripts/cleanup.sh --aws --dry-run   # Preview AWS destruction
  ./scripts/cleanup.sh --all -y          # Clean everything without prompts
EOF
    exit 0
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --local)
                CLEAN_LOCAL=true
                shift
                ;;
            --aws)
                CLEAN_AWS=true
                shift
                ;;
            --s3)
                CLEAN_S3=true
                shift
                ;;
            --all)
                CLEAN_LOCAL=true
                CLEAN_AWS=true
                CLEAN_S3=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -y|--yes)
                SKIP_CONFIRM=true
                shift
                ;;
            -h|--help)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                ;;
        esac
    done

    # Default to local if nothing specified
    if [[ "$CLEAN_LOCAL" == false && "$CLEAN_AWS" == false && "$CLEAN_S3" == false ]]; then
        CLEAN_LOCAL=true
    fi
}

# Confirmation prompt
confirm() {
    local message="$1"
    if [[ "$SKIP_CONFIRM" == true ]]; then
        return 0
    fi

    echo -e "${YELLOW}⚠ WARNING:${NC} $message"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cancelled."
        exit 0
    fi
}

# Clean local generated data
clean_local() {
    log_info "Cleaning local generated data..."

    local dirs=(
        "output/sample-10k"
        "output/sample-small"
        "output/sample-medium"
        "output/sample-large"
        "output/sample-xlarge"
        "output/bench-small"
        "output/bench-medium"
        "output/bench-large"
    )

    local total_size=0
    local found_dirs=()

    for dir in "${dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            found_dirs+=("$dir")
            size=$(du -sk "$dir" 2>/dev/null | cut -f1)
            total_size=$((total_size + size))
        fi
    done

    if [[ ${#found_dirs[@]} -eq 0 ]]; then
        log_info "No local generated data found."
        return
    fi

    echo ""
    echo "Found ${#found_dirs[@]} directories ($(numfmt --to=iec-i --suffix=B $((total_size * 1024)) 2>/dev/null || echo "${total_size}KB")):"
    for dir in "${found_dirs[@]}"; do
        echo "  - $dir"
    done
    echo ""

    if [[ "$DRY_RUN" == true ]]; then
        log_dry "Delete ${#found_dirs[@]} directories"
        return
    fi

    confirm "This will delete ${#found_dirs[@]} directories of generated data."

    for dir in "${found_dirs[@]}"; do
        rm -rf "$dir"
        log_success "Deleted: $dir"
    done

    log_success "Local cleanup complete"
}

# Empty S3 buckets
clean_s3() {
    log_info "Checking for S3 buckets to empty..."

    # Find project buckets
    local buckets
    buckets=$(aws s3 ls 2>/dev/null | grep -E "(fhir-omop|synthetic-healthlake|health-platform)" | awk '{print $3}' || true)

    if [[ -z "$buckets" ]]; then
        log_info "No matching S3 buckets found."
        return
    fi

    echo ""
    echo "Found S3 buckets:"
    echo "$buckets" | while read -r bucket; do
        count=$(aws s3 ls "s3://$bucket" --recursive 2>/dev/null | wc -l | xargs)
        echo "  - s3://$bucket ($count objects)"
    done
    echo ""

    if [[ "$DRY_RUN" == true ]]; then
        log_dry "Empty all matching S3 buckets"
        return
    fi

    confirm "This will PERMANENTLY DELETE all objects in these S3 buckets."

    echo "$buckets" | while read -r bucket; do
        if [[ -n "$bucket" ]]; then
            log_info "Emptying s3://$bucket..."
            aws s3 rm "s3://$bucket" --recursive 2>/dev/null || true
            log_success "Emptied: s3://$bucket"
        fi
    done

    log_success "S3 cleanup complete"
}

# Destroy AWS resources
clean_aws() {
    log_info "Preparing to destroy AWS resources..."

    if ! command -v cdk &> /dev/null; then
        log_error "CDK CLI not found. Install with: npm install -g aws-cdk"
        exit 1
    fi

    # Check for CDK stacks
    cd cdk

    echo ""
    log_info "Current CDK stacks:"
    npx cdk list 2>/dev/null || true
    echo ""

    if [[ "$DRY_RUN" == true ]]; then
        log_dry "Run 'cdk destroy --all' in cdk/ directory"
        cd ..
        return
    fi

    confirm "This will DESTROY all CDK stacks and associated AWS resources."

    log_info "Running CDK destroy..."
    npx cdk destroy --all --force

    cd ..
    log_success "AWS resources destroyed"
}

# Clean dbt artifacts
clean_dbt() {
    log_info "Cleaning dbt artifacts..."

    local dbt_dirs=(
        "dbt/snowflake/target"
        "dbt/snowflake/logs"
        "dbt/snowflake/dbt_packages"
    )

    for dir in "${dbt_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            if [[ "$DRY_RUN" == true ]]; then
                log_dry "Delete $dir"
            else
                rm -rf "$dir"
                log_success "Deleted: $dir"
            fi
        fi
    done
}

# Clean Python cache
clean_python_cache() {
    log_info "Cleaning Python cache..."

    if [[ "$DRY_RUN" == true ]]; then
        find . -type d -name "__pycache__" 2>/dev/null | head -5
        log_dry "Delete all __pycache__ directories"
        return
    fi

    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true

    log_success "Python cache cleaned"
}

# Main
main() {
    parse_args "$@"

    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║              SYNTHETIC HEALTHLAKE - CLEANUP UTILITY                  ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""

    if [[ "$DRY_RUN" == true ]]; then
        log_warning "DRY-RUN MODE - No changes will be made"
        echo ""
    fi

    # Run cleanup tasks
    if [[ "$CLEAN_LOCAL" == true ]]; then
        clean_local
        clean_dbt
        clean_python_cache
    fi

    if [[ "$CLEAN_S3" == true ]]; then
        clean_s3
    fi

    if [[ "$CLEAN_AWS" == true ]]; then
        clean_aws
    fi

    echo ""
    log_success "Cleanup complete!"
    echo ""
}

main "$@"
