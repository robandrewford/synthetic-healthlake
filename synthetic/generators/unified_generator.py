#!/usr/bin/env python3
"""
Unified Synthetic Data Generator - Creates correlated FHIR and OMOP datasets.
Ensures that FHIR Patient and OMOP Person represent the same individual.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import click
import pandas as pd
from faker import Faker


class UnifiedGenerator:
    """Generate correlated FHIR and OMOP synthetic data."""

    def __init__(self, seed: int = 42):
        """Initialize generator with seed for reproducibility."""
        self.fake = Faker()
        self.fake.seed_instance(seed)
        random.seed(seed)

        # OMOP concept mappings
        self.gender_concepts = {"male": 8507, "female": 8532}
        self.race_concepts = [8527, 8516, 8515, 8557]
        self.ethnicity_concepts = [38003563, 38003564]
        self.condition_concepts = [
            (201826, "Type 2 Diabetes"),
            (320128, "Essential Hypertension"),
            (317009, "Asthma"),
        ]
        self.measurement_concepts = [
            (3004501, "Glucose", 70, 200, 8840),  # mg/dL
            (3012888, "Systolic BP", 90, 180, 8876),  # mmHg
            (3038553, "BMI", 18, 40, 9531),  # kg/m2
        ]

    def generate_person(self, person_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
        """Generate correlated FHIR Patient and OMOP Person."""
        # Generate shared demographics
        gender = self.fake.random_element(elements=("male", "female"))
        birth_date = self.fake.date_of_birth(minimum_age=0, maximum_age=100)
        family_name = self.fake.last_name()
        given_name = self.fake.first_name()

        # FHIR Patient
        fhir_patient = {
            "resourceType": "Patient",
            "id": str(person_id),
            "identifier": [
                {
                    "system": "urn:oid:synthetic-healthlake",
                    "value": f"patient-{person_id:06d}",
                }
            ],
            "active": True,
            "name": [{"use": "official", "family": family_name, "given": [given_name]}],
            "gender": gender,
            "birthDate": birth_date.isoformat(),
            "address": [
                {
                    "use": "home",
                    "line": [self.fake.street_address()],
                    "city": self.fake.city(),
                    "state": self.fake.state_abbr(),
                    "postalCode": self.fake.zipcode(),
                    "country": "US",
                }
            ],
            "meta": {
                "source": "unified-generator",
                "versionId": "1",
                "lastUpdated": datetime.utcnow().isoformat() + "Z",
            },
            "extension": [
                {
                    "url": "http://synthetic-healthlake/omop-person-id",
                    "valueInteger": person_id,
                }
            ],
        }

        # Randomly add deceased status
        if self.fake.boolean(chance_of_getting_true=10):
            deceased_date = self.fake.date_time_between(start_date=birth_date, end_date="now")
            fhir_patient["deceasedDateTime"] = deceased_date.isoformat() + "Z"

        # OMOP Person
        omop_person = {
            "person_id": person_id,
            "gender_concept_id": self.gender_concepts[gender],
            "year_of_birth": birth_date.year,
            "month_of_birth": birth_date.month,
            "day_of_birth": birth_date.day,
            "birth_datetime": birth_date.isoformat(),
            "race_concept_id": random.choice(self.race_concepts),
            "ethnicity_concept_id": random.choice(self.ethnicity_concepts),
            "person_source_value": f"person-{person_id:06d}",
            "gender_source_value": gender,
            "race_source_value": "synthetic",
            "ethnicity_source_value": "synthetic",
        }

        return fhir_patient, omop_person

    def generate_conditions(self, person_id: int, count: int = None) -> list[dict[str, Any]]:
        """Generate OMOP condition occurrences."""
        if count is None:
            count = random.randint(0, 3)

        conditions = []
        base_date = datetime.now() - timedelta(days=random.randint(30, 3650))

        selected_conditions = random.sample(
            self.condition_concepts, min(count, len(self.condition_concepts))
        )

        for i, (concept_id, _name) in enumerate(selected_conditions):
            condition_date = base_date + timedelta(days=random.randint(0, 365))
            conditions.append(
                {
                    "condition_occurrence_id": f"{person_id}{i:03d}",
                    "person_id": person_id,
                    "condition_concept_id": concept_id,
                    "condition_start_date": condition_date.date().isoformat(),
                    "condition_start_datetime": condition_date.isoformat(),
                    "condition_type_concept_id": 32817,
                    "visit_occurrence_id": None,
                }
            )

        return conditions

    def generate_measurements(self, person_id: int, count: int = None) -> list[dict[str, Any]]:
        """Generate OMOP measurements."""
        if count is None:
            count = random.randint(0, 5)

        measurements = []
        base_date = datetime.now() - timedelta(days=random.randint(30, 365))

        for i in range(count):
            measurement_date = base_date + timedelta(days=random.randint(0, 365))
            concept_id, name, min_val, max_val, unit_concept_id = random.choice(
                self.measurement_concepts
            )
            value = random.uniform(min_val, max_val)

            measurements.append(
                {
                    "measurement_id": f"{person_id}{i:04d}",
                    "person_id": person_id,
                    "measurement_concept_id": concept_id,
                    "measurement_date": measurement_date.date().isoformat(),
                    "measurement_datetime": measurement_date.isoformat(),
                    "measurement_type_concept_id": 44818702,
                    "value_as_number": round(value, 2),
                    "unit_concept_id": unit_concept_id,
                    "visit_occurrence_id": None,
                }
            )

        return measurements


@click.command()
@click.option("--count", "-n", default=100, help="Number of persons to generate")
@click.option(
    "--fhir-dir",
    required=True,
    type=click.Path(),
    help="Output directory for FHIR JSON",
)
@click.option(
    "--omop-dir",
    required=True,
    type=click.Path(),
    help="Output directory for OMOP Parquet",
)
@click.option("--seed", default=42, help="Random seed for reproducibility")
@click.option(
    "--format",
    type=click.Choice(["json", "ndjson"]),
    default="json",
    help="Output format for FHIR (json=Bundle, ndjson=Newline Delimited)",
)
def main(count: int, fhir_dir: str, omop_dir: str, seed: int, format: str):
    """Generate correlated FHIR and OMOP synthetic datasets."""
    fhir_path = Path(fhir_dir)
    omop_path = Path(omop_dir)
    fhir_path.mkdir(parents=True, exist_ok=True)
    omop_path.mkdir(parents=True, exist_ok=True)

    generator = UnifiedGenerator(seed=seed)

    # Generate correlated data
    fhir_patients = []
    omop_persons = []
    all_conditions = []
    all_measurements = []

    for i in range(count):
        person_id = i + 1

        # Generate correlated FHIR and OMOP person
        fhir_patient, omop_person = generator.generate_person(person_id)
        fhir_patients.append(fhir_patient)
        omop_persons.append(omop_person)

        # Generate conditions and measurements
        all_conditions.extend(generator.generate_conditions(person_id))
        all_measurements.extend(generator.generate_measurements(person_id))

    # Write FHIR Data
    if format == "ndjson":
        ndjson_file = fhir_path / "patients.ndjson"
        with ndjson_file.open("w") as f:
            for patient in fhir_patients:
                f.write(json.dumps(patient) + "\n")
        click.echo(f"  FHIR: {ndjson_file} (NDJSON)")
    else:
        # Write FHIR Bundle
        fhir_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": patient} for patient in fhir_patients],
        }
        bundle_file = fhir_path / "patients_bundle.json"
        with bundle_file.open("w") as f:
            json.dump(fhir_bundle, f, indent=2)
        click.echo(f"  FHIR: {bundle_file} (Bundle)")

    # Write OMOP tables
    person_df = pd.DataFrame(omop_persons)
    person_df.to_parquet(omop_path / "person.parquet", index=False)

    if all_conditions:
        condition_df = pd.DataFrame(all_conditions)
        condition_df.to_parquet(omop_path / "condition_occurrence.parquet", index=False)

    if all_measurements:
        measurement_df = pd.DataFrame(all_measurements)
        measurement_df.to_parquet(omop_path / "measurement.parquet", index=False)

    click.echo(f"✓ Generated {count} correlated FHIR/OMOP persons")

    click.echo(f"  OMOP: {omop_path}")
    click.echo(f"  Conditions: {len(all_conditions)}")
    click.echo(f"  Measurements: {len(all_measurements)}")


if __name__ == "__main__":
    main()
