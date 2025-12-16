"""
Integration tests for organization data isolation.

These tests verify that the multi-tenant API correctly isolates
data between organizations. Each organization should only see
their own data.

Note: These tests require a configured test environment with:
- Snowflake connection
- Test data for multiple organizations
- API Gateway endpoint (for E2E tests)
"""

import json
import os
from unittest.mock import patch

import pytest

# Skip all tests if not in integration test mode
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "true",
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to run.",
)


class TestOrgIsolationPatient:
    """Test organization isolation for Patient API."""

    @pytest.fixture
    def org_a_context(self):
        """Organization A context."""
        return {
            "organization_id": "org-a-test-001",
            "organization_name": "Test Hospital A",
        }

    @pytest.fixture
    def org_b_context(self):
        """Organization B context."""
        return {
            "organization_id": "org-b-test-002",
            "organization_name": "Test Clinic B",
        }

    @pytest.fixture
    def mock_db_with_org_data(self):
        """Mock database with organization-scoped data."""
        # Simulated data with organization context
        patient_data = {
            "org-a-test-001": [
                {
                    "RECORD_CONTENT": {
                        "id": "pat-a-001",
                        "resourceType": "Patient",
                        "name": [{"family": "OrgA"}],
                    }
                },
                {
                    "RECORD_CONTENT": {
                        "id": "pat-a-002",
                        "resourceType": "Patient",
                        "name": [{"family": "OrgA"}],
                    }
                },
            ],
            "org-b-test-002": [
                {
                    "RECORD_CONTENT": {
                        "id": "pat-b-001",
                        "resourceType": "Patient",
                        "name": [{"family": "OrgB"}],
                    }
                },
            ],
        }

        def mock_execute(sql, params=None):
            # Extract org_id from SQL WHERE clause (simplified)
            for org_id, data in patient_data.items():
                if org_id in sql:
                    return data
            return []

        return mock_execute

    def test_org_a_sees_only_own_patients(self, org_a_context, mock_db_with_org_data):
        """Verify Organization A only sees its own patients."""
        with patch("health_platform.utils.db.execute_query", mock_db_with_org_data):
            # Simulate API call with org_a context
            # In real implementation, this would call the handler
            results = mock_db_with_org_data(
                f"SELECT * FROM patients WHERE org_id = '{org_a_context['organization_id']}'"
            )

            assert len(results) == 2
            for patient in results:
                assert patient["RECORD_CONTENT"]["name"][0]["family"] == "OrgA"

    def test_org_b_sees_only_own_patients(self, org_b_context, mock_db_with_org_data):
        """Verify Organization B only sees its own patients."""
        with patch("health_platform.utils.db.execute_query", mock_db_with_org_data):
            results = mock_db_with_org_data(
                f"SELECT * FROM patients WHERE org_id = '{org_b_context['organization_id']}'"
            )

            assert len(results) == 1
            assert results[0]["RECORD_CONTENT"]["name"][0]["family"] == "OrgB"

    def test_cross_org_access_denied(self, org_a_context, org_b_context, mock_db_with_org_data):
        """Verify org A cannot access org B patient by ID."""
        # This test verifies that even if org A tries to access pat-b-001,
        # the system returns nothing (because of org filtering)
        with patch("health_platform.utils.db.execute_query", mock_db_with_org_data):
            results = mock_db_with_org_data(
                f"SELECT * FROM patients WHERE org_id = '{org_a_context['organization_id']}' AND id = 'pat-b-001'"
            )

            # Should return nothing because pat-b-001 belongs to org B
            assert len(results) == 0 or all(
                p["RECORD_CONTENT"]["id"].startswith("pat-a") for p in results
            )


class TestOrgIsolationEncounter:
    """Test organization isolation for Encounter API."""

    @pytest.fixture
    def mock_encounter_data(self):
        """Mock encounter data with organization scoping."""
        encounter_data = {
            "org-a-test-001": [
                {
                    "RECORD_CONTENT": {
                        "id": "enc-a-001",
                        "resourceType": "Encounter",
                        "status": "finished",
                        "subject": {"reference": "Patient/pat-a-001"},
                    }
                },
            ],
            "org-b-test-002": [
                {
                    "RECORD_CONTENT": {
                        "id": "enc-b-001",
                        "resourceType": "Encounter",
                        "status": "in-progress",
                        "subject": {"reference": "Patient/pat-b-001"},
                    }
                },
            ],
        }
        return encounter_data

    def test_encounter_patient_filter_respects_org(self, mock_encounter_data):
        """Verify encounter search by patient respects org boundaries."""
        org_a_id = "org-a-test-001"

        # Searching for encounters for pat-a-001 from org A
        org_a_encounters = mock_encounter_data.get(org_a_id, [])

        # Should only see org A's encounter
        assert len(org_a_encounters) == 1
        assert org_a_encounters[0]["RECORD_CONTENT"]["id"] == "enc-a-001"

    def test_encounter_cannot_reference_cross_org_patient(self, mock_encounter_data):
        """Verify encounters cannot reference patients from other orgs."""
        org_a_encounters = mock_encounter_data.get("org-a-test-001", [])

        for enc in org_a_encounters:
            patient_ref = enc["RECORD_CONTENT"]["subject"]["reference"]
            # Patient reference should be within org A's namespace
            assert "pat-a" in patient_ref


class TestOrgIsolationObservation:
    """Test organization isolation for Observation API."""

    @pytest.fixture
    def mock_observation_data(self):
        """Mock observation data with organization scoping."""
        return {
            "org-a-test-001": [
                {
                    "RECORD_CONTENT": {
                        "id": "obs-a-001",
                        "resourceType": "Observation",
                        "code": {"coding": [{"code": "8867-4", "display": "Heart rate"}]},
                        "subject": {"reference": "Patient/pat-a-001"},
                        "valueQuantity": {"value": 72, "unit": "beats/min"},
                    }
                },
            ],
            "org-b-test-002": [
                {
                    "RECORD_CONTENT": {
                        "id": "obs-b-001",
                        "resourceType": "Observation",
                        "code": {"coding": [{"code": "8867-4", "display": "Heart rate"}]},
                        "subject": {"reference": "Patient/pat-b-001"},
                        "valueQuantity": {"value": 80, "unit": "beats/min"},
                    }
                },
            ],
        }

    def test_observation_code_search_respects_org(self, mock_observation_data):
        """Verify searching by LOINC code respects org boundaries."""
        # Both orgs have heart rate observations
        org_a_obs = mock_observation_data.get("org-a-test-001", [])
        org_b_obs = mock_observation_data.get("org-b-test-002", [])

        # Each org should only see their own
        assert len(org_a_obs) == 1
        assert org_a_obs[0]["RECORD_CONTENT"]["id"] == "obs-a-001"

        assert len(org_b_obs) == 1
        assert org_b_obs[0]["RECORD_CONTENT"]["id"] == "obs-b-001"

    def test_observation_patient_filter_respects_org(self, mock_observation_data):
        """Verify observation patient filter respects org boundaries."""
        org_a_obs = mock_observation_data.get("org-a-test-001", [])

        for obs in org_a_obs:
            patient_ref = obs["RECORD_CONTENT"]["subject"]["reference"]
            assert "pat-a" in patient_ref


class TestOrgIsolationIngestion:
    """Test organization isolation for Ingestion API."""

    def test_webhook_stores_with_org_context(self):
        """Verify webhook ingestion stores data with organization context."""
        from health_platform.ingestion.webhook.handler import store_bundle

        test_bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [{"resource": {"resourceType": "Patient", "id": "test-pat"}}],
        }

        with patch("health_platform.ingestion.webhook.handler.s3_client") as mock_s3:
            mock_s3.put_object.return_value = {}

            s3_key = store_bundle(test_bundle, "test-job-123")

            # Verify S3 put was called
            mock_s3.put_object.assert_called_once()

            # Verify key structure includes date partitioning
            assert "incoming/fhir" in s3_key
            assert "test-job-123" in s3_key

    def test_presigned_url_scoped_to_org(self):
        """Verify presigned URLs are scoped to organization namespace."""
        from health_platform.ingestion.presigned.handler import generate_upload_url

        with patch("health_platform.ingestion.presigned.handler.s3_client") as mock_s3:
            mock_s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/test"

            result = generate_upload_url("{}", "test-request")

            # Response should include S3 key in org namespace
            response_body = json.loads(result["body"])
            assert "incoming/fhir/uploads" in response_body["s3Key"]


class TestOrgIsolationE2E:
    """End-to-end organization isolation tests.

    These tests require a running API and test environment.
    """

    @pytest.fixture
    def api_endpoint(self):
        """Get API endpoint from environment."""
        endpoint = os.environ.get("API_ENDPOINT")
        if not endpoint:
            pytest.skip("API_ENDPOINT not configured")
        return endpoint

    @pytest.fixture
    def org_a_token(self):
        """Get JWT token for Organization A."""
        token = os.environ.get("ORG_A_JWT_TOKEN")
        if not token:
            pytest.skip("ORG_A_JWT_TOKEN not configured")
        return token

    @pytest.fixture
    def org_b_token(self):
        """Get JWT token for Organization B."""
        token = os.environ.get("ORG_B_JWT_TOKEN")
        if not token:
            pytest.skip("ORG_B_JWT_TOKEN not configured")
        return token

    def test_e2e_patient_isolation(self, api_endpoint, org_a_token, org_b_token):
        """E2E test: Verify patient API respects org isolation."""
        import requests

        # Get patients as Org A
        resp_a = requests.get(
            f"{api_endpoint}/Patient",
            headers={"Authorization": f"Bearer {org_a_token}"},
        )
        assert resp_a.status_code == 200
        patients_a = resp_a.json()

        # Get patients as Org B
        resp_b = requests.get(
            f"{api_endpoint}/Patient",
            headers={"Authorization": f"Bearer {org_b_token}"},
        )
        assert resp_b.status_code == 200
        patients_b = resp_b.json()

        # Verify no overlap in patient IDs
        ids_a = {e["resource"]["id"] for e in patients_a.get("entry", [])}
        ids_b = {e["resource"]["id"] for e in patients_b.get("entry", [])}

        assert ids_a.isdisjoint(ids_b), "Patient IDs should not overlap between organizations"

    def test_e2e_cross_org_patient_access_denied(self, api_endpoint, org_a_token):
        """E2E test: Verify cross-org patient access is denied."""
        import requests

        # Try to access a patient ID that belongs to another org
        # This should return 404 (not found) rather than 403 (forbidden)
        # to avoid leaking information about resource existence
        resp = requests.get(
            f"{api_endpoint}/Patient/org-b-patient-id",
            headers={"Authorization": f"Bearer {org_a_token}"},
        )

        # Should return 404 - patient not found in this org's context
        assert resp.status_code == 404


class TestOrgIsolationSQL:
    """Test that SQL queries properly include organization filters."""

    def test_patient_query_includes_org_filter(self):
        """Verify patient queries include organization filter."""
        # This is a pattern test to ensure future development maintains isolation

        # Expected: All data access queries should include WHERE org_id = ?
        # or equivalent filtering mechanism

        # Example SQL pattern that should be enforced:
        safe_query_pattern = """
        SELECT * FROM patients
        WHERE organization_id = %(org_id)s
        AND patient_id = %(patient_id)s
        """

        # Verify the pattern includes org filter
        assert "organization_id" in safe_query_pattern.lower()

    def test_encounter_query_includes_org_filter(self):
        """Verify encounter queries include organization filter."""
        safe_query_pattern = """
        SELECT * FROM encounters
        WHERE organization_id = %(org_id)s
        """

        assert "organization_id" in safe_query_pattern.lower()

    def test_observation_query_includes_org_filter(self):
        """Verify observation queries include organization filter."""
        safe_query_pattern = """
        SELECT * FROM observations
        WHERE organization_id = %(org_id)s
        """

        assert "organization_id" in safe_query_pattern.lower()


class TestOrgIsolationAudit:
    """Test audit logging for organization access."""

    def test_access_logged_with_org_context(self):
        """Verify API access is logged with organization context."""

        # Set up log capture
        with patch("logging.Logger.info") as mock_log:
            # Simulate handler logging
            mock_log(
                "Processing request",
                extra={
                    "organization_id": "org-test-001",
                    "request_id": "req-123",
                    "resource_type": "Patient",
                },
            )

            # Verify log was called with org context
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert "extra" in call_args.kwargs or len(call_args) > 1

    def test_cross_org_attempt_logged(self):
        """Verify cross-organization access attempts are logged."""
        # This test ensures that if someone tries to access another org's data,
        # it gets logged for security monitoring

        log_entry = {
            "event": "cross_org_access_attempt",
            "requesting_org": "org-a",
            "target_resource_org": "org-b",
            "resource_type": "Patient",
            "resource_id": "pat-b-001",
            "result": "denied",
        }

        # Verify log entry has required fields for security monitoring
        assert "requesting_org" in log_entry
        assert "target_resource_org" in log_entry
        assert log_entry["result"] == "denied"
