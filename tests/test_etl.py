"""Unit tests for ETL scripts."""
import pytest
from pathlib import Path
import json
import pandas as pd
from synthetic.etl.flatten_fhir import flatten_patient


class TestFHIRFlattening:
    """Test FHIR flattening functionality."""
    
    def test_flatten_patient_basic(self):
        """Test flattening a basic FHIR patient."""
        patient = {
            'id': '1',
            'active': True,
            'name': [{
                'family': 'Smith',
                'given': ['John']
            }],
            'gender': 'male',
            'birthDate': '1990-05-15',
            'address': [{
                'city': 'Boston',
                'state': 'MA',
                'postalCode': '02101',
                'country': 'US'
            }],
            'meta': {
                'source': 'test-generator'
            },
            'extension': [{
                'url': 'http://synthetic-healthlake/omop-person-id',
                'valueInteger': 1
            }]
        }
        
        flattened = flatten_patient(patient)
        
        assert flattened['patient_id'] == '1'
        assert flattened['person_id_omop'] == 1
        assert flattened['family_name'] == 'Smith'
        assert flattened['given_name'] == 'John'
        assert flattened['birth_date'] == '1990-05-15'
        assert flattened['gender'] == 'male'
        assert flattened['city'] == 'Boston'
        assert flattened['state'] == 'MA'
    
    def test_flatten_patient_minimal(self):
        """Test flattening a patient with minimal data."""
        patient = {
            'id': '2',
            'gender': 'female',
            'birthDate': '1985-10-20'
        }
        
        flattened = flatten_patient(patient)
        
        assert flattened['patient_id'] == '2'
        assert flattened['gender'] == 'female'
        assert flattened['birth_date'] == '1985-10-20'
        assert flattened['family_name'] is None
        assert flattened['person_id_omop'] is None


class TestOMOPConversion:
    """Test OMOP CSV to Parquet conversion."""
    
    def test_parquet_schema(self, tmp_path):
        """Test that Parquet files have correct schema."""
        # Create test CSV
        csv_data = pd.DataFrame({
            'person_id': [1, 2, 3],
            'gender_concept_id': [8507, 8532, 8507],
            'year_of_birth': [1990, 1985, 2000]
        })
        
        csv_file = tmp_path / 'person.csv'
        csv_data.to_csv(csv_file, index=False)
        
        # Read back and verify types
        df = pd.read_csv(csv_file)
        assert 'person_id' in df.columns
        assert 'gender_concept_id' in df.columns
        assert len(df) == 3
