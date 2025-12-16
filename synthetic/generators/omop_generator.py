#!/usr/bin/env python3
"""
OMOP CDM Generator - Creates synthetic OMOP Person, Condition, and Measurement data.
"""

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import click
import pandas as pd
from faker import Faker


class OMOPGenerator:
    """Generate synthetic OMOP CDM data."""

    def __init__(self, seed: int = 42):
        """Initialize generator with optional seed for reproducibility."""
        self.fake = Faker()
        Faker.seed(seed)
        random.seed(seed)

        # Common OMOP concept IDs (simplified for demonstration)
        self.gender_concepts = {"male": 8507, "female": 8532}
        self.race_concepts = [8527, 8516, 8515, 8557]  # White, Black, Asian, Other
        self.ethnicity_concepts = [38003563, 38003564]  # Hispanic, Not Hispanic

        # Common condition concepts (diabetes, hypertension, asthma)
        self.condition_concepts = [201826, 320128, 317009]

        # Common measurement concepts (glucose, blood pressure, BMI)
        self.measurement_concepts = [3004501, 3012888, 3038553]

    def generate_person(self, person_id: int) -> dict[str, Any]:
        """Generate a single OMOP Person record."""
        gender = self.fake.random_element(elements=("male", "female"))
        birth_date = self.fake.date_of_birth(minimum_age=0, maximum_age=100)

        return {
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

    def generate_conditions(self, person_id: int, count: int = None) -> list[dict[str, Any]]:
        """Generate condition occurrences for a person."""
        if count is None:
            count = random.randint(0, 3)  # 0-3 conditions per person

        conditions = []
        base_date = datetime.now() - timedelta(days=random.randint(30, 3650))

        for i in range(count):
            condition_date = base_date + timedelta(days=random.randint(0, 365))
            conditions.append(
                {
                    "condition_occurrence_id": f"{person_id}{i:03d}",
                    "person_id": person_id,
                    "condition_concept_id": random.choice(self.condition_concepts),
                    "condition_start_date": condition_date.date().isoformat(),
                    "condition_start_datetime": condition_date.isoformat(),
                    "condition_type_concept_id": 32817,  # EHR
                    "visit_occurrence_id": None,
                }
            )

        return conditions

    def generate_measurements(self, person_id: int, count: int = None) -> list[dict[str, Any]]:
        """Generate measurements for a person."""
        if count is None:
            count = random.randint(0, 5)  # 0-5 measurements per person

        measurements = []
        base_date = datetime.now() - timedelta(days=random.randint(30, 365))

        for i in range(count):
            measurement_date = base_date + timedelta(days=random.randint(0, 365))
            concept_id = random.choice(self.measurement_concepts)

            # Generate realistic values based on measurement type
            if concept_id == 3004501:  # Glucose
                value = random.uniform(70, 200)
                unit_concept_id = 8840  # mg/dL
            elif concept_id == 3012888:  # Systolic BP
                value = random.uniform(90, 180)
                unit_concept_id = 8876  # mmHg
            else:  # BMI
                value = random.uniform(18, 40)
                unit_concept_id = 9531  # kg/m2

            measurements.append(
                {
                    "measurement_id": f"{person_id}{i:04d}",
                    "person_id": person_id,
                    "measurement_concept_id": concept_id,
                    "measurement_date": measurement_date.date().isoformat(),
                    "measurement_datetime": measurement_date.isoformat(),
                    "measurement_type_concept_id": 44818702,  # Lab result
                    "value_as_number": round(value, 2),
                    "unit_concept_id": unit_concept_id,
                    "visit_occurrence_id": None,
                }
            )

        return measurements


@click.command()
@click.option("--count", "-n", default=100, help="Number of persons to generate")
@click.option(
    "--output-dir",
    "-o",
    required=True,
    type=click.Path(),
    help="Output directory for OMOP CSV files",
)
@click.option("--seed", default=42, help="Random seed for reproducibility")
@click.option(
    "--format",
    type=click.Choice(["csv", "parquet"]),
    default="csv",
    help="Output format",
)
def main(count: int, output_dir: str, seed: int, format: str):
    """Generate synthetic OMOP CDM data."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generator = OMOPGenerator(seed=seed)

    # Generate persons
    persons = [generator.generate_person(i + 1) for i in range(count)]

    # Generate conditions and measurements
    all_conditions = []
    all_measurements = []

    for person in persons:
        person_id = person["person_id"]
        all_conditions.extend(generator.generate_conditions(person_id))
        all_measurements.extend(generator.generate_measurements(person_id))

    # Write to files
    if format == "csv":
        # Person table
        person_df = pd.DataFrame(persons)
        person_file = output_path / "person.csv"
        person_df.to_csv(person_file, index=False)

        # Condition occurrence table
        if all_conditions:
            condition_df = pd.DataFrame(all_conditions)
            condition_file = output_path / "condition_occurrence.csv"
            condition_df.to_csv(condition_file, index=False)

        # Measurement table
        if all_measurements:
            measurement_df = pd.DataFrame(all_measurements)
            measurement_file = output_path / "measurement.csv"
            measurement_df.to_csv(measurement_file, index=False)

        click.echo(
            f"✓ Generated {count} persons with {len(all_conditions)} conditions and {len(all_measurements)} measurements"
        )
        click.echo(f"  Output: {output_path}")
    else:  # parquet
        person_df = pd.DataFrame(persons)
        person_file = output_path / "person.parquet"
        person_df.to_parquet(person_file, index=False)

        if all_conditions:
            condition_df = pd.DataFrame(all_conditions)
            condition_file = output_path / "condition_occurrence.parquet"
            condition_df.to_parquet(condition_file, index=False)

        if all_measurements:
            measurement_df = pd.DataFrame(all_measurements)
            measurement_file = output_path / "measurement.parquet"
            measurement_df.to_parquet(measurement_file, index=False)

        click.echo(
            f"✓ Generated {count} persons with {len(all_conditions)} conditions and {len(all_measurements)} measurements (Parquet)"
        )
        click.echo(f"  Output: {output_path}")


if __name__ == "__main__":
    main()
