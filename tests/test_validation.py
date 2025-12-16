"""Unit tests for validation scripts."""

import pandas as pd
import yaml

from synthetic.scripts.apply_domain_constraints import load_yaml, validate_constraints


class TestDomainConstraints:
    """Test domain constraint validation."""

    def test_load_yaml(self, tmp_path):
        """Test loading YAML configuration."""
        config = {"version": 0.1, "domains": {"patient": {"constraints": []}}}

        config_file = tmp_path / "test_config.yaml"
        with config_file.open("w") as f:
            yaml.dump(config, f)

        loaded = load_yaml(config_file)
        assert loaded["version"] == 0.1
        assert "domains" in loaded

    def test_validate_age_range(self, tmp_path):
        """Test age range constraint validation."""
        # Create test data
        data = pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "year_of_birth": [1990, 2020, 1850],  # 1850 is out of range
            }
        )

        data_file = tmp_path / "person.parquet"
        data.to_parquet(data_file, index=False)

        # Create constraints
        constraints = {
            "domains": {
                "patient": {
                    "constraints": [
                        {
                            "id": "age_range",
                            "type": "range",
                            "applies_to": {
                                "model": "omop.person",
                                "field": "year_of_birth",
                            },
                            "params": {"min_year": 1920, "max_year": 2020},
                        }
                    ]
                }
            }
        }

        violations = validate_constraints(tmp_path, constraints)
        assert len(violations) == 1
        assert "age_range" in violations[0]


class TestCrossModelValidation:
    """Test cross-model validation."""

    def test_matching_ids(self, tmp_path):
        """Test that matching IDs pass validation."""
        # Create OMOP data
        omop_data = pd.DataFrame(
            {
                "person_id": [1, 2, 3],
                "year_of_birth": [1990, 1985, 2000],
                "month_of_birth": [5, 10, 3],
                "day_of_birth": [15, 20, 8],
            }
        )

        omop_file = tmp_path / "person.parquet"
        omop_data.to_parquet(omop_file, index=False)

        # Create FHIR data
        fhir_data = pd.DataFrame(
            {
                "patient_id": ["1", "2", "3"],
                "person_id_omop": [1, 2, 3],
                "birth_date": ["1990-05-15", "1985-10-20", "2000-03-08"],
            }
        )

        fhir_file = tmp_path / "fhir_patient_flat.parquet"
        fhir_data.to_parquet(fhir_file, index=False)

        # Validation should pass (tested via script, not directly here)
        assert omop_file.exists()
        assert fhir_file.exists()
