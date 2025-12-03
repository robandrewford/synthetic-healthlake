"""Unit tests for synthetic data generators."""
import pytest
from pathlib import Path
import json
import pandas as pd
from synthetic.generators.fhir_generator import FHIRGenerator
from synthetic.generators.omop_generator import OMOPGenerator
from synthetic.generators.unified_generator import UnifiedGenerator


class TestFHIRGenerator:
    """Test FHIR patient generator."""
    
    def test_generate_patient(self):
        """Test generating a single FHIR patient."""
        generator = FHIRGenerator(seed=42)
        patient = generator.generate_patient(1)
        
        assert patient['resourceType'] == 'Patient'
        assert patient['id'] == '1'
        assert 'name' in patient
        assert 'gender' in patient
        assert 'birthDate' in patient
        assert patient['gender'] in ['male', 'female']
    
    def test_generate_multiple_patients(self):
        """Test generating multiple FHIR patients."""
        generator = FHIRGenerator(seed=42)
        patients = generator.generate_patients(5)
        
        assert len(patients) == 5
        assert all(p['resourceType'] == 'Patient' for p in patients)
        
        # Check IDs are sequential
        ids = [int(p['id']) for p in patients]
        assert ids == [1, 2, 3, 4, 5]
    
    def test_reproducibility(self):
        """Test that same seed produces same results."""
        gen1 = FHIRGenerator(seed=42)
        gen2 = FHIRGenerator(seed=42)
        
        patient1 = gen1.generate_patient(1)
        patient2 = gen2.generate_patient(1)
        
        assert patient1['birthDate'] == patient2['birthDate']
        assert patient1['gender'] == patient2['gender']


class TestOMOPGenerator:
    """Test OMOP data generator."""
    
    def test_generate_person(self):
        """Test generating a single OMOP person."""
        generator = OMOPGenerator(seed=42)
        person = generator.generate_person(1)
        
        assert person['person_id'] == 1
        assert 'gender_concept_id' in person
        assert 'year_of_birth' in person
        assert person['gender_concept_id'] in [8507, 8532]  # male or female
    
    def test_generate_conditions(self):
        """Test generating conditions for a person."""
        generator = OMOPGenerator(seed=42)
        conditions = generator.generate_conditions(1, count=2)
        
        assert len(conditions) == 2
        assert all(c['person_id'] == 1 for c in conditions)
        assert all('condition_concept_id' in c for c in conditions)
    
    def test_generate_measurements(self):
        """Test generating measurements for a person."""
        generator = OMOPGenerator(seed=42)
        measurements = generator.generate_measurements(1, count=3)
        
        assert len(measurements) == 3
        assert all(m['person_id'] == 1 for m in measurements)
        assert all('value_as_number' in m for m in measurements)


class TestUnifiedGenerator:
    """Test unified FHIR+OMOP generator."""
    
    def test_generate_correlated_person(self):
        """Test that FHIR and OMOP data are correlated."""
        generator = UnifiedGenerator(seed=42)
        fhir_patient, omop_person = generator.generate_person(1)
        
        # Check IDs match
        assert fhir_patient['id'] == '1'
        assert omop_person['person_id'] == 1
        
        # Check birth dates match
        fhir_birth = fhir_patient['birthDate']
        omop_birth = f"{omop_person['year_of_birth']}-{omop_person['month_of_birth']:02d}-{omop_person['day_of_birth']:02d}"
        assert fhir_birth == omop_birth
        
        # Check gender matches
        fhir_gender = fhir_patient['gender']
        omop_gender_concept = omop_person['gender_concept_id']
        
        if fhir_gender == 'male':
            assert omop_gender_concept == 8507
        else:
            assert omop_gender_concept == 8532
    
    def test_reproducibility(self):
        """Test that same seed produces same correlated data."""
        gen1 = UnifiedGenerator(seed=42)
        gen2 = UnifiedGenerator(seed=42)
        
        fhir1, omop1 = gen1.generate_person(1)
        fhir2, omop2 = gen2.generate_person(1)
        
        assert fhir1['birthDate'] == fhir2['birthDate']
        assert omop1['year_of_birth'] == omop2['year_of_birth']
