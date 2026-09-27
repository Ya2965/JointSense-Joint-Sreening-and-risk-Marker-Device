"""Iter5 backend tests: BMI range guard (422), PDF removes 'Assessed knee'/'Model confidence',
adds 'Score composition' + 'Screening trend' with last 3 combined_scores."""
import os
import io
import time
import pytest
import requests
from pypdf import PdfReader

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

EMAIL = "doctor1@jointsense.local"
PWD = "JointSense123!"

pytestmark = pytest.mark.xdist_group("v2_serial")


@pytest.fixture(scope="module")
def h():
    r = requests.post(f"{API}/auth/login", json={"identifier": EMAIL, "password": PWD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}


def _base_patient(name):
    return {
        "name": name, "age": 55, "gender": "Female",
        "affected_leg": "Left leg", "pain_duration": "6 months",
    }


class TestBmiRangeGuard:
    def test_reject_height_too_high(self, h):
        p = _base_patient("TEST_Iter5BadHeightHi"); p["height_cm"] = 500; p["weight_kg"] = 70
        r = requests.post(f"{API}/patients", json=p, headers=h)
        assert r.status_code == 422, r.text

    def test_reject_height_too_low(self, h):
        p = _base_patient("TEST_Iter5BadHeightLo"); p["height_cm"] = 10; p["weight_kg"] = 70
        r = requests.post(f"{API}/patients", json=p, headers=h)
        assert r.status_code == 422, r.text

    def test_reject_weight_too_high(self, h):
        p = _base_patient("TEST_Iter5BadWeightHi"); p["height_cm"] = 170; p["weight_kg"] = 1000
        r = requests.post(f"{API}/patients", json=p, headers=h)
        assert r.status_code == 422, r.text

    def test_reject_weight_too_low(self, h):
        p = _base_patient("TEST_Iter5BadWeightLo"); p["height_cm"] = 170; p["weight_kg"] = 5
        r = requests.post(f"{API}/patients", json=p, headers=h)
        assert r.status_code == 422, r.text

    def test_accept_valid_anthro(self, h):
        p = _base_patient("TEST_Iter5GoodAnthro"); p["height_cm"] = 170; p["weight_kg"] = 70
        r = requests.post(f"{API}/patients", json=p, headers=h)
        assert r.status_code in (200, 201), r.text
        d = r.json()
        assert d["height_cm"] == 170
        assert d["weight_kg"] == 70


def _set_sim(h):
    requests.put(f"{API}/settings", json={"clinic_name": "TEST Iter5", "signature_name": "Dr Iter5", "hardware_mode": "simulator"}, headers=h)


def _run_screening(h, pid):
    answers = {str(i): 2 for i in range(7)}
    requests.post(f"{API}/assessment/start", json={"patient_id": pid, "answers": answers, "test": "two-minute-walk"}, headers=h)
    time.sleep(1.1)
    stop = requests.post(f"{API}/assessment/stop", headers=h)
    assert stop.status_code == 200, stop.text
    return stop.json()


def _pdf_text(h, sid):
    r = requests.get(f"{API}/assessments/{sid}/pdf", headers=h)
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-"
    assert len(r.content) > 0
    reader = PdfReader(io.BytesIO(r.content))
    return r.content, "\n".join((p.extract_text() or "") for p in reader.pages)


class TestPdfIter5:
    @pytest.fixture(scope="class")
    def patient_with_three(self, h):
        _set_sim(h)
        p = requests.post(f"{API}/patients", json={
            "name": "TEST_Iter5Trend3", "age": 60, "gender": "Male",
            "affected_leg": "Right leg", "pain_duration": "3 months",
            "height_cm": 170, "weight_kg": 72,
        }, headers=h).json()
        pid = p["id"]
        scores = []
        last_sid = None
        for _ in range(3):
            s = _run_screening(h, pid)
            scores.append(int(round(float(s.get("combined_score") or 0))))
            last_sid = s["id"]
        return pid, last_sid, scores

    @pytest.fixture(scope="class")
    def patient_with_one(self, h):
        _set_sim(h)
        p = requests.post(f"{API}/patients", json={
            "name": "TEST_Iter5Trend1", "age": 50, "gender": "Female",
            "affected_leg": "Left leg", "pain_duration": "2 months",
            "height_cm": 165, "weight_kg": 65,
        }, headers=h).json()
        s = _run_screening(h, p["id"])
        return p["id"], s["id"], int(round(float(s.get("combined_score") or 0)))

    def test_pdf_no_assessed_knee(self, h, patient_with_three):
        _, sid, _ = patient_with_three
        body, text = _pdf_text(h, sid)
        assert "Assessed knee" not in text, "PDF should no longer contain 'Assessed knee'"

    def test_pdf_no_model_confidence(self, h, patient_with_three):
        _, sid, _ = patient_with_three
        body, text = _pdf_text(h, sid)
        assert "Model confidence" not in text, "PDF should no longer contain 'Model confidence'"

    def test_pdf_has_trend_section_and_three_scores(self, h, patient_with_three):
        _, sid, scores = patient_with_three
        body, text = _pdf_text(h, sid)
        assert "Screening trend" in text, f"Missing 'Screening trend'. Text: {text[:600]}"
        # Each of the 3 integer scores should appear in the trend chart
        for s in scores:
            assert str(s) in text, f"Score {s} missing from PDF; scores={scores}"

    def test_pdf_single_screening_trend(self, h, patient_with_one):
        _, sid, score = patient_with_one
        body, text = _pdf_text(h, sid)
        assert "Screening trend" in text
        # Either the integer score OR the 'this screening' caption should appear
        assert (str(score) in text) or ("this screening" in text), text[:600]

    def test_pdf_has_score_composition_and_shap(self, h, patient_with_three):
        _, sid, _ = patient_with_three
        body, text = _pdf_text(h, sid)
        assert "Score composition" in text
        assert "TreeSHAP" in text or "Model explanation" in text
        assert len(body) > 5000
