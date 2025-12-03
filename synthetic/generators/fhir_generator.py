#!/usr/bin/env python3
"""
FHIR Patient Generator - Creates synthetic FHIR R4 Patient resources.
"""
import json
import click
from pathlib import Path
from faker import Faker
from datetime import datetime
from typing import List, Dict, Any


class FHIRGenerator:
    """Generate synthetic FHIR R4 Patient resources."""
    
    def __init__(self, seed: int = 42):
        """Initialize generator with optional seed for reproducibility."""
        self.fake = Faker()
        Faker.seed(seed)
    
    def generate_patient(self, patient_id: int) -> Dict[str, Any]:
        """Generate a single FHIR Patient resource."""
        gender = self.fake.random_element(elements=('male', 'female'))
        birth_date = self.fake.date_of_birth(minimum_age=0, maximum_age=100)
        
        patient = {
            "resourceType": "Patient",
            "id": str(patient_id),
            "identifier": [{
                "system": "urn:oid:synthetic-healthlake",
                "value": f"patient-{patient_id:06d}"
            }],
            "active": True,
            "name": [{
                "use": "official",
                "family": self.fake.last_name(),
                "given": [self.fake.first_name()]
            }],
            "gender": gender,
            "birthDate": birth_date.isoformat(),
            "address": [{
                "use": "home",
                "line": [self.fake.street_address()],
                "city": self.fake.city(),
                "state": self.fake.state_abbr(),
                "postalCode": self.fake.zipcode(),
                "country": "US"
            }],
            "meta": {
                "source": "synthetic-generator",
                "versionId": "1",
                "lastUpdated": datetime.utcnow().isoformat() + "Z"
            },
            "extension": [{
                "url": "http://synthetic-healthlake/omop-person-id",
                "valueInteger": patient_id
            }]
        }
        
        # Randomly add deceased status
        if self.fake.boolean(chance_of_getting_true=10):
            patient["deceasedDateTime"] = self.fake.date_time_between(
                start_date=birth_date, 
                end_date='now'
            ).isoformat() + "Z"
        
        return patient
    
    def generate_patients(self, count: int) -> List[Dict[str, Any]]:
        """Generate multiple FHIR Patient resources."""
        return [self.generate_patient(i + 1) for i in range(count)]


@click.command()
@click.option('--count', '-n', default=100, help='Number of patients to generate')
@click.option('--output-dir', '-o', required=True, type=click.Path(), help='Output directory for FHIR JSON files')
@click.option('--seed', default=42, help='Random seed for reproducibility')
@click.option('--bundle/--individual', default=False, help='Output as FHIR Bundle or individual files')
def main(count: int, output_dir: str, seed: int, bundle: bool):
    """Generate synthetic FHIR Patient resources."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    generator = FHIRGenerator(seed=seed)
    patients = generator.generate_patients(count)
    
    if bundle:
        # Create FHIR Bundle
        fhir_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": patient} for patient in patients]
        }
        bundle_file = output_path / "patients_bundle.json"
        with bundle_file.open('w') as f:
            json.dump(fhir_bundle, f, indent=2)
        click.echo(f"✓ Generated {count} patients in bundle: {bundle_file}")
    else:
        # Create individual files
        for patient in patients:
            patient_file = output_path / f"patient_{patient['id']}.json"
            with patient_file.open('w') as f:
                json.dump(patient, f, indent=2)
        click.echo(f"✓ Generated {count} individual patient files in: {output_path}")


if __name__ == "__main__":
    main()
