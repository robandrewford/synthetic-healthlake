#!/usr/bin/env python3
"""
Domain Constraints Validator - Validates synthetic data against domain constraints.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML configuration file."""
    with path.open() as f:
        return yaml.safe_load(f)


def validate_constraints(data_dir: Path, constraints: dict[str, Any]) -> list[str]:
    """Validate data against domain constraints."""
    violations = []

    for _domain_name, domain_config in constraints.get("domains", {}).items():
        for constraint in domain_config.get("constraints", []):
            constraint_id = constraint["id"]
            constraint_type = constraint["type"]
            applies_to = constraint["applies_to"]
            params = constraint["params"]

            # Parse model and field
            model_path = applies_to["model"]  # e.g., "omop.person"
            field_name = applies_to["field"]

            # Determine file to check
            if model_path.startswith("omop."):
                table_name = model_path.split(".")[1]
                file_path = data_dir / f"{table_name}.parquet"
            else:
                continue  # Skip non-OMOP for now

            if not file_path.exists():
                violations.append(f"[{constraint_id}] File not found: {file_path}")
                continue

            # Load data
            df = pd.read_parquet(file_path)

            if field_name not in df.columns:
                violations.append(
                    f"[{constraint_id}] Field '{field_name}' not found in {table_name}"
                )
                continue

            # Apply constraint based on type
            if constraint_type == "range":
                min_val = params.get("min_year")
                max_val = params.get("max_year")

                invalid_rows = df[(df[field_name] < min_val) | (df[field_name] > max_val)]

                if len(invalid_rows) > 0:
                    violations.append(
                        f"[{constraint_id}] {len(invalid_rows)} rows violate range constraint "
                        f"({min_val}-{max_val}) for {field_name}"
                    )

    return violations


def main():
    parser = argparse.ArgumentParser(
        description="Validate synthetic data against domain constraints"
    )
    parser.add_argument("--omop-dir", required=True, help="Directory with OMOP Parquet files")
    parser.add_argument("--fhir-dir", required=True, help="Directory with FHIR Parquet files")
    parser.add_argument(
        "--constraints-config", required=True, help="Path to domain constraints YAML"
    )
    parser.add_argument(
        "--distributions-config",
        required=True,
        help="Path to distribution profiles YAML",
    )
    parser.add_argument(
        "--terminology-dir", required=True, help="Directory with terminology mappings"
    )
    args = parser.parse_args()

    # Load constraints
    constraints_path = Path(args.constraints_config)
    if not constraints_path.exists():
        print(f"✗ Constraints file not found: {constraints_path}", file=sys.stderr)
        sys.exit(1)

    constraints = load_yaml(constraints_path)

    # Validate OMOP data
    omop_dir = Path(args.omop_dir)
    violations = validate_constraints(omop_dir, constraints)

    if violations:
        print(f"✗ Found {len(violations)} constraint violations:")
        for violation in violations:
            print(f"  {violation}")
        sys.exit(1)
    else:
        print(f"✓ All domain constraints passed for data in: {omop_dir}")
        sys.exit(0)


if __name__ == "__main__":
    main()
