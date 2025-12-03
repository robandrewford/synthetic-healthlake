#!/usr/bin/env python3
"""
FHIR Flattener - Converts FHIR JSON resources to tabular Parquet format.
"""
import json
import click
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


def flatten_patient(patient: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten a FHIR Patient resource to a tabular row."""
    # Extract OMOP person_id from extension
    person_id_omop = None
    if 'extension' in patient:
        for ext in patient['extension']:
            if ext.get('url') == 'http://synthetic-healthlake/omop-person-id':
                person_id_omop = ext.get('valueInteger')
    
    # Extract name
    family_name = None
    given_name = None
    if 'name' in patient and len(patient['name']) > 0:
        name = patient['name'][0]
        family_name = name.get('family')
        if 'given' in name and len(name['given']) > 0:
            given_name = name['given'][0]
    
    # Extract address
    city = None
    state = None
    postal_code = None
    country = None
    if 'address' in patient and len(patient['address']) > 0:
        address = patient['address'][0]
        city = address.get('city')
        state = address.get('state')
        postal_code = address.get('postalCode')
        country = address.get('country')
    
    # Extract language (if present)
    language = None
    if 'communication' in patient and len(patient['communication']) > 0:
        comm = patient['communication'][0]
        if 'language' in comm and 'coding' in comm['language']:
            language = comm['language']['coding'][0].get('code')
    
    return {
        'patient_id': patient.get('id'),
        'person_id_omop': person_id_omop,
        'active': patient.get('active', True),
        'family_name': family_name,
        'given_name': given_name,
        'birth_date': patient.get('birthDate'),
        'gender': patient.get('gender'),
        'deceased_datetime': patient.get('deceasedDateTime'),
        'language': language,
        'country': country,
        'postal_code': postal_code,
        'city': city,
        'state': state,
        'synthetic_source': patient.get('meta', {}).get('source', 'unknown'),
        'ingestion_timestamp': datetime.utcnow().isoformat() + 'Z',
        'fhir_ingestion_ts': datetime.utcnow().isoformat() + 'Z'
    }


@click.command()
@click.option('--input-dir', '-i', required=True, type=click.Path(exists=True), help='Input directory with FHIR JSON files')
@click.option('--output-file', '-o', required=True, type=click.Path(), help='Output Parquet file')
@click.option('--bundle/--individual', default=False, help='Input is FHIR Bundle or individual files')
def main(input_dir: str, output_file: str, bundle: bool):
    """Flatten FHIR Patient resources to Parquet."""
    input_path = Path(input_dir)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    patients = []
    
    if bundle:
        # Read bundle file
        bundle_file = input_path / 'patients_bundle.json'
        if not bundle_file.exists():
            click.echo(f"✗ Bundle file not found: {bundle_file}", err=True)
            return
        
        with bundle_file.open('r') as f:
            bundle_data = json.load(f)
            if 'entry' in bundle_data:
                patients = [entry['resource'] for entry in bundle_data['entry']]
    else:
        # Read individual files
        json_files = list(input_path.glob('patient_*.json'))
        if not json_files:
            click.echo(f"✗ No patient JSON files found in: {input_path}", err=True)
            return
        
        for json_file in json_files:
            with json_file.open('r') as f:
                patients.append(json.load(f))
    
    # Flatten patients
    flattened = [flatten_patient(p) for p in patients]
    
    # Create DataFrame and write to Parquet
    df = pd.DataFrame(flattened)
    df.to_parquet(output_path, index=False)
    
    click.echo(f"✓ Flattened {len(flattened)} FHIR patients to: {output_path}")
    click.echo(f"  Columns: {', '.join(df.columns)}")


if __name__ == "__main__":
    main()
