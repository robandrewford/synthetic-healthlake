#!/usr/bin/env python3
"""
Cross-Model Validator - Validates consistency between FHIR and OMOP datasets.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


def validate_cross_model(omop_dir: Path, fhir_dir: Path) -> bool:
    """Validate consistency between FHIR and OMOP data."""
    violations = []

    # Load OMOP person data
    omop_person_file = omop_dir / "person.parquet"
    if not omop_person_file.exists():
        print(f"✗ OMOP person file not found: {omop_person_file}", file=sys.stderr)
        return False

    omop_df = pd.read_parquet(omop_person_file)

    # Load FHIR patient data
    fhir_patient_file = fhir_dir / "fhir_patient_flat.parquet"
    if not fhir_patient_file.exists():
        print(f"✗ FHIR patient file not found: {fhir_patient_file}", file=sys.stderr)
        return False

    fhir_df = pd.read_parquet(fhir_patient_file)

    # Check 1: Verify person_id / patient_id consistency
    omop_person_ids = set(omop_df["person_id"].unique())
    fhir_person_ids = set(fhir_df["person_id_omop"].dropna().astype(int).unique())

    missing_in_fhir = omop_person_ids - fhir_person_ids
    missing_in_omop = fhir_person_ids - omop_person_ids

    if missing_in_fhir:
        violations.append(f"Found {len(missing_in_fhir)} OMOP persons missing in FHIR")

    if missing_in_omop:
        violations.append(f"Found {len(missing_in_omop)} FHIR patients missing in OMOP")

    # Check 2: Verify birth date consistency (for matching IDs)
    merged = pd.merge(
        omop_df[["person_id", "year_of_birth", "month_of_birth", "day_of_birth"]],
        fhir_df[["person_id_omop", "birth_date"]],
        left_on="person_id",
        right_on="person_id_omop",
        how="inner",
    )

    # Compare birth dates
    date_mismatches = 0
    for _, row in merged.iterrows():
        if pd.notna(row["birth_date"]):
            fhir_date = pd.to_datetime(row["birth_date"])
            if (
                row["year_of_birth"] != fhir_date.year
                or row["month_of_birth"] != fhir_date.month
                or row["day_of_birth"] != fhir_date.day
            ):
                date_mismatches += 1

    if date_mismatches > 0:
        violations.append(f"Found {date_mismatches} birth date mismatches between FHIR and OMOP")

    # Report results
    if violations:
        print(f"✗ Found {len(violations)} cross-model validation issues:")
        for violation in violations:
            print(f"  {violation}")
        return False
    else:
        print("✓ Cross-model validation passed")
        print(f"  OMOP persons: {len(omop_person_ids)}")
        print(f"  FHIR patients: {len(fhir_person_ids)}")
        print(f"  Matched records: {len(merged)}")
        return True


def main():
    parser = argparse.ArgumentParser(description="Cross-model validation between FHIR and OMOP")
    parser.add_argument("--omop-dir", required=True, help="Directory with OMOP Parquet files")
    parser.add_argument("--fhir-dir", required=True, help="Directory with FHIR Parquet files")
    args = parser.parse_args()

    omop_dir = Path(args.omop_dir)
    fhir_dir = Path(args.fhir_dir)

    success = validate_cross_model(omop_dir, fhir_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
