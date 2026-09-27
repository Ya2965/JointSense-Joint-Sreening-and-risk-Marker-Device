"""Tests for real TreeSHAP SHAP output on /assessment/stop and /assessments/{id}/pdf."""
import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://arthritis-edge.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# Force serial execution under pytest-xdist: TestShap and TestPdf share the same
# clinician user, and the backend's assessment_states dict is per-user, so
# concurrent workers would race on start/stop. Pin everything to a single worker.
import pytest as _pytest
pytestmark = _pytest.mark.xdist_group("shap_pdf_serial")


CLINICIAN_EMAIL = "doctor1@jointsense.local"
CLINICIAN_PASSWORD = "JointSense123!"

OLD_HARDCODED = {
    ("left_right_weight_asymmetry", 0.24),
    ("total_rom", 0.18),
    ("gait_speed", 0.13),
}


@pytest.fixture(scope="module")
def clinician_token():
    r = requests.post(f"{API}/auth/login", json={"identifier": CLINICIAN_EMAIL, "password": CLINICIAN_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(clinician_token):
    return {"Authorization": f"Bearer {clinician_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def second_clinician_token():
    # Register a second clinician for cross-workspace isolation tests
    email = f"test_clin_{uuid.uuid4().hex[:8]}@jointsense.local"
    username = f"TestClin{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/auth/register", json={"username": username, "email": email, "password": "Passw0rd!"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def patient(headers):
    r = requests.post(f"{API}/patients", json={"name": "TEST_ShapPatient", "age": 55, "gender": "Female", "affected_leg": "Left leg", "pain_duration": "6 months"}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def screening(headers, patient):
    answers = {str(i): 2 for i in range(7)}
    r = requests.post(f"{API}/assessment/start", json={"patient_id": patient["id"], "answers": answers, "test": "two-minute-walk"}, headers=headers)
    assert r.status_code == 200, r.text
    time.sleep(2.2)
    r = requests.post(f"{API}/assessment/stop", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# --- SHAP tests ---
class TestShap:
    def test_shap_status_available(self, screening):
        assert screening["shap_status"] == "available", screening

    def test_shap_is_nonempty_list(self, screening):
        assert isinstance(screening["shap"], list)
        assert len(screening["shap"]) >= 2

    def test_shap_entries_have_required_fields(self, screening):
        for row in screening["shap"]:
            assert "feature" in row and "contribution" in row and "direction" in row
            assert isinstance(row["contribution"], (int, float))
            assert row["direction"] in ("increases concern", "reduces concern")

    def test_shap_not_hardcoded(self, screening):
        pairs = {(row["feature"], round(float(row["contribution"]), 2)) for row in screening["shap"]}
        overlap = pairs & OLD_HARDCODED
        assert len(overlap) < len(OLD_HARDCODED), f"SHAP still matches old hardcoded values: {overlap}"

    def test_explanation_mentions_treeshap(self, screening):
        assert "TreeSHAP" in screening.get("explanation", ""), screening.get("explanation")

    def test_scores_consistent(self, screening):
        expected = round(screening["koos_score"] * 0.4 + screening["movement_score"] * 0.6, 1)
        assert abs(screening["combined_score"] - expected) < 0.11, (screening["combined_score"], expected)
        assert screening["risk_level"] in {"Low", "Moderate", "High", "Very high"}
        for k in ("koos_score", "movement_score", "combined_score"):
            assert isinstance(screening[k], (int, float))


# --- PDF tests ---
class TestPdf:
    def test_pdf_valid(self, headers, screening):
        r = requests.get(f"{API}/assessments/{screening['id']}/pdf", headers=headers)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf"), r.headers
        assert r.content[:5] == b"%PDF-", r.content[:20]
        assert len(r.content) > 1000
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower(), cd
        assert ".pdf" in cd.lower()

    def test_pdf_unknown_id_404(self, headers):
        r = requests.get(f"{API}/assessments/does-not-exist-{uuid.uuid4().hex}/pdf", headers=headers)
        assert r.status_code == 404, r.status_code

    def test_pdf_requires_auth(self, screening):
        r = requests.get(f"{API}/assessments/{screening['id']}/pdf")
        assert r.status_code == 401, r.status_code

    def test_pdf_cross_workspace_returns_404(self, screening, second_clinician_token):
        other_headers = {"Authorization": f"Bearer {second_clinician_token}"}
        r = requests.get(f"{API}/assessments/{screening['id']}/pdf", headers=other_headers)
        assert r.status_code == 404, r.status_code


# --- Cleanup ---
def teardown_module(module):
    try:
        r = requests.post(f"{API}/auth/login", json={"identifier": CLINICIAN_EMAIL, "password": CLINICIAN_PASSWORD})
        if r.status_code == 200:
            token = r.json()["token"]
            h = {"Authorization": f"Bearer {token}"}
            pts = requests.get(f"{API}/patients", headers=h).json()
            for p in pts:
                if p.get("name", "").startswith("TEST_"):
                    # No delete endpoint available; leave as-is but flag
                    pass
    except Exception:
        pass
