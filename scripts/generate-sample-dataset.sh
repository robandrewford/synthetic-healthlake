#!/usr/bin/env bash
# =============================================================================
# generate-sample-dataset.sh - Generate synthetic FHIR+OMOP patient datasets
# =============================================================================
# Usage:
#   ./scripts/generate-sample-dataset.sh [OPTIONS]
#
# Options:
#   -s, --size SIZE      Dataset size: small (100), medium (1000), large (10000),
#                        xlarge (50000), or custom number (default: large)
#   -o, --output DIR     Output directory (default: output/sample-{size})
#   --seed SEED          Random seed for reproducibility (default: 42)
#   --validate           Run validation after generation
#   -h, --help           Show this help message
#
# Examples:
#   ./scripts/generate-sample-dataset.sh                     # Generate 10k patients
#   ./scripts/generate-sample-dataset.sh --size small        # Generate 100 patients
#   ./scripts/generate-sample-dataset.sh --size 5000         # Custom size
#   ./scripts/generate-sample-dataset.sh --validate          # With validation
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SIZE="large"
SEED=42
VALIDATE=false
OUTPUT_DIR=""

# Size mappings
declare -A SIZE_MAP=(
    ["small"]=100
    ["medium"]=1000
    ["large"]=10000
    ["xlarge"]=50000
)

# Print colored message
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Show help message
show_help() {
    cat << 'EOF'
generate-sample-dataset.sh - Generate synthetic FHIR+OMOP patient datasets
Usage:
  ./scripts/generate-sample-dataset.sh [OPTIONS]

Options:
  -s, --size SIZE      Dataset size: small (100), medium (1000), large (10000),
                       xlarge (50000), or custom number (default: large)
  -o, --output DIR     Output directory (default: output/sample-{size})
  --seed SEED          Random seed for reproducibility (default: 42)
  --validate           Run validation after generation
  -h, --help           Show this help message

Examples:
  ./scripts/generate-sample-dataset.sh                     # Generate 10k patients
  ./scripts/generate-sample-dataset.sh --size small        # Generate 100 patients
  ./scripts/generate-sample-dataset.sh --size 5000         # Custom size
  ./scripts/generate-sample-dataset.sh --validate          # With validation
EOF
    exit 0
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--size)
                SIZE="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --seed)
                SEED="$2"
                shift 2
                ;;
            --validate)
                VALIDATE=true
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
}

# Resolve size to count
resolve_size() {
    local size="$1"

    # Check if it's a named size
    if [[ -n "${SIZE_MAP[$size]:-}" ]]; then
        echo "${SIZE_MAP[$size]}"
        return
    fi

    # Check if it's a number
    if [[ "$size" =~ ^[0-9]+$ ]]; then
        echo "$size"
        return
    fi

    log_error "Invalid size: $size. Use small, medium, large, xlarge, or a number."
    exit 1
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v uv &> /dev/null; then
        log_error "uv is not installed. Please install it: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    if ! command -v python &> /dev/null; then
        log_error "python is not installed."
        exit 1
    fi

    log_success "Dependencies OK"
}

# Generate the dataset
generate_dataset() {
    local count="$1"
    local output_dir="$2"
    local seed="$3"

    local fhir_dir="${output_dir}/fhir"
    local omop_dir="${output_dir}/omop"

    log_info "Generating ${count} patients..."
    log_info "  FHIR output: ${fhir_dir}"
    log_info "  OMOP output: ${omop_dir}"
    log_info "  Seed: ${seed}"

    # Create output directories
    mkdir -p "${fhir_dir}" "${omop_dir}"

    # Run the generator
    uv run python synthetic/generators/unified_generator.py \
        --count "${count}" \
        --fhir-dir "${fhir_dir}" \
        --omop-dir "${omop_dir}" \
        --seed "${seed}" \
        --format ndjson

    log_success "Dataset generated successfully"
}

# Validate the dataset
validate_dataset() {
    local output_dir="$1"

    log_info "Validating dataset..."

    python -c "
import pandas as pd
import json
import sys

output_dir = '${output_dir}'

# Validate OMOP files
try:
    person_df = pd.read_parquet(f'{output_dir}/omop/person.parquet')
    conditions_df = pd.read_parquet(f'{output_dir}/omop/condition_occurrence.parquet')
    measurements_df = pd.read_parquet(f'{output_dir}/omop/measurement.parquet')
except Exception as e:
    print(f'ERROR: Failed to read Parquet files: {e}')
    sys.exit(1)

# Validate FHIR file
try:
    with open(f'{output_dir}/fhir/patients.ndjson', 'r') as f:
        patients = [json.loads(line) for line in f]
except Exception as e:
    print(f'ERROR: Failed to read FHIR NDJSON: {e}')
    sys.exit(1)

# Validate record counts match
if len(person_df) != len(patients):
    print(f'ERROR: FHIR ({len(patients)}) and OMOP ({len(person_df)}) patient counts do not match')
    sys.exit(1)

# Validate required columns
required_person_cols = ['person_id', 'gender_concept_id', 'year_of_birth']
for col in required_person_cols:
    if col not in person_df.columns:
        print(f'ERROR: Missing required column: {col}')
        sys.exit(1)

# Validate no null person_ids
if person_df['person_id'].isnull().any():
    print('ERROR: Found null person_id values')
    sys.exit(1)

# Validate gender concept IDs are valid
valid_genders = {8507, 8532}  # Male, Female
invalid_genders = set(person_df['gender_concept_id'].unique()) - valid_genders
if invalid_genders:
    print(f'WARNING: Found unexpected gender concept IDs: {invalid_genders}')

print('OK')
"

    if [[ $? -eq 0 ]]; then
        log_success "Dataset validation passed"
    else
        log_error "Dataset validation failed"
        exit 1
    fi
}

# Print dataset statistics
print_statistics() {
    local output_dir="$1"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "                         DATASET STATISTICS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    python -c "
import pandas as pd
import json
import os

output_dir = '${output_dir}'

# Load data
person_df = pd.read_parquet(f'{output_dir}/omop/person.parquet')
conditions_df = pd.read_parquet(f'{output_dir}/omop/condition_occurrence.parquet')
measurements_df = pd.read_parquet(f'{output_dir}/omop/measurement.parquet')

with open(f'{output_dir}/fhir/patients.ndjson', 'r') as f:
    patients = [json.loads(line) for line in f]

# File sizes
def get_size(path):
    size = os.path.getsize(path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f'{size:.1f} {unit}'
        size /= 1024
    return f'{size:.1f} TB'

print(f'''
📊 Record Counts:
   ├─ FHIR Patients:    {len(patients):,}
   ├─ OMOP Persons:     {len(person_df):,}
   ├─ Conditions:       {len(conditions_df):,}
   └─ Measurements:     {len(measurements_df):,}

📁 File Sizes:
   ├─ patients.ndjson:              {get_size(f\"{output_dir}/fhir/patients.ndjson\")}
   ├─ person.parquet:               {get_size(f\"{output_dir}/omop/person.parquet\")}
   ├─ condition_occurrence.parquet: {get_size(f\"{output_dir}/omop/condition_occurrence.parquet\")}
   └─ measurement.parquet:          {get_size(f\"{output_dir}/omop/measurement.parquet\")}

👥 Demographics:
   ├─ Male:   {len(person_df[person_df['gender_concept_id'] == 8507]):,} ({len(person_df[person_df['gender_concept_id'] == 8507]) / len(person_df) * 100:.1f}%)
   ├─ Female: {len(person_df[person_df['gender_concept_id'] == 8532]):,} ({len(person_df[person_df['gender_concept_id'] == 8532]) / len(person_df) * 100:.1f}%)
   └─ Birth Year Range: {person_df['year_of_birth'].min()} - {person_df['year_of_birth'].max()}

🩺 Conditions:
   ├─ Type 2 Diabetes:  {len(conditions_df[conditions_df['condition_concept_id'] == 201826]):,}
   ├─ Hypertension:     {len(conditions_df[conditions_df['condition_concept_id'] == 320128]):,}
   └─ Asthma:           {len(conditions_df[conditions_df['condition_concept_id'] == 317009]):,}

📏 Measurements:
   ├─ Glucose:     {len(measurements_df[measurements_df['measurement_concept_id'] == 3004501]):,}
   ├─ Systolic BP: {len(measurements_df[measurements_df['measurement_concept_id'] == 3012888]):,}
   └─ BMI:         {len(measurements_df[measurements_df['measurement_concept_id'] == 3038553]):,}
''')

# Deceased count
deceased = sum(1 for p in patients if 'deceasedDateTime' in p)
print(f'💀 Deceased: {deceased:,} ({deceased / len(patients) * 100:.1f}%)')
"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main function
main() {
    parse_args "$@"

    # Resolve count from size
    COUNT=$(resolve_size "$SIZE")

    # Set default output directory if not specified
    if [[ -z "$OUTPUT_DIR" ]]; then
        if [[ -n "${SIZE_MAP[$SIZE]:-}" ]]; then
            OUTPUT_DIR="output/sample-${SIZE}"
        else
            OUTPUT_DIR="output/sample-${COUNT}"
        fi
    fi

    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║           SYNTHETIC HEALTHLAKE - SAMPLE DATASET GENERATOR            ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo ""

    check_dependencies
    generate_dataset "$COUNT" "$OUTPUT_DIR" "$SEED"

    if [[ "$VALIDATE" == true ]]; then
        validate_dataset "$OUTPUT_DIR"
    fi

    print_statistics "$OUTPUT_DIR"

    echo ""
    log_success "Dataset ready at: ${OUTPUT_DIR}"
    echo ""
    echo "Next steps:"
    echo "  • Query with Python: python -c \"import pandas as pd; print(pd.read_parquet('${OUTPUT_DIR}/omop/person.parquet').head())\""
    echo "  • Upload to S3: aws s3 sync ${OUTPUT_DIR}/ s3://your-bucket/synthetic/"
    echo "  • See docs: docs/data/sample-dataset.md"
    echo ""
}

main "$@"
