"""Test fixtures and configuration."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_fhir_patient():
    """Sample FHIR patient for testing."""
    return {
        "resourceType": "Patient",
        "id": "1",
        "active": True,
        "name": [{"use": "official", "family": "Doe", "given": ["Jane"]}],
        "gender": "female",
        "birthDate": "1990-01-01",
        "address": [
            {
                "use": "home",
                "city": "Boston",
                "state": "MA",
                "postalCode": "02101",
                "country": "US",
            }
        ],
    }


@pytest.fixture
def sample_omop_person():
    """Sample OMOP person for testing."""
    return {
        "person_id": 1,
        "gender_concept_id": 8532,
        "year_of_birth": 1990,
        "month_of_birth": 1,
        "day_of_birth": 1,
        "race_concept_id": 8527,
        "ethnicity_concept_id": 38003563,
    }
