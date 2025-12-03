#!/usr/bin/env python3
"""
OMOP to Parquet Converter - Converts OMOP CSV files to Parquet format.
"""
import click
import pandas as pd
from pathlib import Path
from typing import Dict, Any


# OMOP table schemas with data types
OMOP_SCHEMAS = {
    'person': {
        'person_id': 'int64',
        'gender_concept_id': 'int64',
        'year_of_birth': 'int64',
        'month_of_birth': 'Int64',  # Nullable
        'day_of_birth': 'Int64',  # Nullable
        'birth_datetime': 'str',
        'race_concept_id': 'int64',
        'ethnicity_concept_id': 'int64',
        'person_source_value': 'str',
        'gender_source_value': 'str',
        'race_source_value': 'str',
        'ethnicity_source_value': 'str'
    },
    'condition_occurrence': {
        'condition_occurrence_id': 'str',
        'person_id': 'int64',
        'condition_concept_id': 'int64',
        'condition_start_date': 'str',
        'condition_start_datetime': 'str',
        'condition_type_concept_id': 'int64',
        'visit_occurrence_id': 'Int64'  # Nullable
    },
    'measurement': {
        'measurement_id': 'str',
        'person_id': 'int64',
        'measurement_concept_id': 'int64',
        'measurement_date': 'str',
        'measurement_datetime': 'str',
        'measurement_type_concept_id': 'int64',
        'value_as_number': 'float64',
        'unit_concept_id': 'int64',
        'visit_occurrence_id': 'Int64'  # Nullable
    }
}


def convert_csv_to_parquet(csv_file: Path, output_dir: Path, table_name: str):
    """Convert a single OMOP CSV file to Parquet."""
    # Read CSV
    df = pd.read_csv(csv_file)
    
    # Apply schema if available
    if table_name in OMOP_SCHEMAS:
        schema = OMOP_SCHEMAS[table_name]
        for col, dtype in schema.items():
            if col in df.columns:
                try:
                    df[col] = df[col].astype(dtype)
                except Exception as e:
                    click.echo(f"  Warning: Could not convert {col} to {dtype}: {e}")
    
    # Write to Parquet
    output_file = output_dir / f"{table_name}.parquet"
    df.to_parquet(output_file, index=False)
    
    return len(df), output_file


@click.command()
@click.option('--input-dir', '-i', required=True, type=click.Path(exists=True), help='Input directory with OMOP CSV files')
@click.option('--output-dir', '-o', required=True, type=click.Path(), help='Output directory for Parquet files')
def main(input_dir: str, output_dir: str):
    """Convert OMOP CSV files to Parquet format."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all CSV files
    csv_files = list(input_path.glob('*.csv'))
    
    if not csv_files:
        click.echo(f"✗ No CSV files found in: {input_path}", err=True)
        return
    
    total_rows = 0
    converted_files = []
    
    for csv_file in csv_files:
        table_name = csv_file.stem
        try:
            row_count, output_file = convert_csv_to_parquet(csv_file, output_path, table_name)
            total_rows += row_count
            converted_files.append((table_name, row_count, output_file))
            click.echo(f"✓ Converted {table_name}: {row_count} rows → {output_file.name}")
        except Exception as e:
            click.echo(f"✗ Error converting {csv_file.name}: {e}", err=True)
    
    click.echo(f"\n✓ Converted {len(converted_files)} tables ({total_rows} total rows)")
    click.echo(f"  Output: {output_path}")


if __name__ == "__main__":
    main()
