"""Iter4 backend tests: anthropometry+notes on patients, PDF (BMI/body-diagram/interpretation/features), hw auto-fallback, leg-abduction double-stop 409."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

EMAIL = "doctor1@jointsense.local"
PWD = "JointSense123!"
HW_KEY = "jointsense-esp32-DEMO-key-change-me"

pytestmark = pytest.mark.xdist_group("v2_serial")


@pytest.fixture(scope="module")
def h():
    r = requests.post(f"{API}/auth/login", json={"identifier": EMAIL, "password": PWD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}


def _set_mode(h, mode):
    r = requests.put(f"{API}/settings", json={"clinic_name": "TEST Iter4", "signature_name": "Dr Iter4", "hardware_mode": mode}, headers=h)
    assert r.status_code == 200, r.text


# --- Patient anthropometry + notes ---
class TestPatientAnthro:
    def test_create_with_anthro_notes_and_read_back(self, h):
        payload = {
            "name": "TEST_Iter4Anthro",
            "age": 55,
            "gender": "Female",
            "affected_leg": "Left leg",
            "pain_duration": "6 months",
            "height_cm": 162,
            "weight_kg": 68,
            "notes": "TEST_Iter4 patient with mild pain flares in the morning.",
        }
        r = requests.post(f"{API}/patients", json=payload, headers=h)
        assert r.status_code == 200, r.text
        created = r.json()
        assert created["height_cm"] == 162
        assert created["weight_kg"] == 68
        assert created["notes"].startswith("TEST_Iter4 patient")
        pid = created["id"]
        # Read back
        r = requests.get(f"{API}/patients/{pid}", headers=h)
        assert r.status_code == 200
        d = r.json()
        assert d["height_cm"] == 162
        assert d["weight_kg"] == 68
        assert "mild pain flares" in d["notes"]

    def test_optional_fields_default_none(self, h):
        r = requests.post(f"{API}/patients", json={"name": "TEST_Iter4NoAnthro", "age": 40, "gender": "Male", "affected_leg": "Right leg", "pain_duration": "1 month"}, headers=h)
        assert r.status_code == 200, r.text
        d = r.json()
        # Should not error and should not have real numbers
        assert d.get("height_cm") in (None, 0, "")
        assert d.get("weight_kg") in (None, 0, "")


# --- PDF with anthropometry / body diagram / interpretation / feature table ---
class TestPdfRichContent:
    @pytest.fixture(scope="class")
    def rich_screening(self, h):
        _set_mode(h, "simulator")
        p = requests.post(f"{API}/patients", json={
            "name": "TEST_Iter4PDF", "age": 60, "gender": "Male", "affected_leg": "Right leg",
            "pain_duration": "3 months", "height_cm": 162, "weight_kg": 68,
            "notes": "TEST notes for pdf",
        }, headers=h).json()
        answers = {str(i): 2 for i in range(7)}
        requests.post(f"{API}/assessment/start", json={"patient_id": p["id"], "answers": answers, "test": "two-minute-walk"}, headers=h)
        time.sleep(1.2)
        stop = requests.post(f"{API}/assessment/stop", headers=h).json()
        return stop["id"]

    def test_pdf_contains_expected_strings(self, h, rich_screening):
        import io
        from pypdf import PdfReader
        r = requests.get(f"{API}/assessments/{rich_screening}/pdf", headers=h)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        body = r.content
        reader = PdfReader(io.BytesIO(body))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        checks = ["25.9", "Clinical interpretation", "Sensor features"]
        missing = [c for c in checks if c not in text]
        assert not missing, f"Missing in PDF text: {missing}\nFirst 500 chars: {text[:500]}"
        assert len(body) > 7000, f"PDF too small: {len(body)} bytes"


# --- Hardware auto-fallback to simulator when stale ---
class TestHwAutoFallback:
    def test_stale_hardware_falls_back_to_simulator(self, h):
        _set_mode(h, "hardware")
        p = requests.post(f"{API}/patients", json={"name": "TEST_Iter4Fallback", "age": 50, "gender": "Male", "affected_leg": "Left leg", "pain_duration": "2 months"}, headers=h).json()
        # push once then wait for stale
        feats = {"gait_speed": 7.77, "cadence": 100.0, "total_rom": 60.0, "peak_loading": 130.0, "movement_smoothness": 0.9, "left_right_weight_asymmetry": 0.05, "acoustic_rms": 0.15, "sit_to_stand_time": 2.0, "fsr_heel": 90.0, "fsr_toe": 70.0}
        requests.post(f"{API}/hw/ingest", json={"device_key": HW_KEY, "test": "two-minute-walk", "features": feats})
        time.sleep(5)
        answers = {str(i): 2 for i in range(7)}
        requests.post(f"{API}/assessment/start", json={"patient_id": p["id"], "answers": answers, "test": "two-minute-walk"}, headers=h)
        r1 = requests.get(f"{API}/assessment/live", headers=h).json()
        assert r1["source"] == "simulator", r1
        assert r1["stale"] is True, r1
        assert r1["features"]["gait_speed"] != 0
        # ensure it isn't returning the stale hardware payload
        assert abs(r1["features"]["gait_speed"] - 7.77) > 0.001
        time.sleep(1.2)
        r2 = requests.get(f"{API}/assessment/live", headers=h).json()
        assert r1["features"] != r2["features"]

        # Now push a fresh packet -> source flips to hardware immediately
        requests.post(f"{API}/hw/ingest", json={"device_key": HW_KEY, "test": "two-minute-walk", "features": feats})
        r3 = requests.get(f"{API}/assessment/live", headers=h).json()
        assert r3["source"] == "hardware", r3
        assert r3["stale"] is False, r3
        assert abs(r3["features"]["gait_speed"] - 7.77) < 0.001
        requests.post(f"{API}/assessment/stop", headers=h)
        _set_mode(h, "simulator")


# --- leg-abduction end-to-end + duplicate stop 409 ---
class TestLegAbductionFlow:
    def test_leg_abduction_save_and_double_stop(self, h):
        _set_mode(h, "simulator")
        p = requests.post(f"{API}/patients", json={"name": "TEST_Iter4LegAbd", "age": 62, "gender": "Female", "affected_leg": "Right leg", "pain_duration": "5 months"}, headers=h).json()
        answers = {str(i): 1 for i in range(7)}
        r = requests.post(f"{API}/assessment/start", json={"patient_id": p["id"], "answers": answers, "test": "leg-abduction"}, headers=h)
        assert r.status_code == 200, r.text
        time.sleep(2.2)
        r = requests.post(f"{API}/assessment/stop", headers=h)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["test"] == "leg-abduction"
        assert isinstance(d.get("shap"), list) and len(d["shap"]) >= 1
        assert "movement_score" in d or "movement_score" in d.get("scores", {})
        assert "combined_score" in d or "combined_score" in d.get("scores", {})
        # double-stop -> 409
        r2 = requests.post(f"{API}/assessment/stop", headers=h)
        assert r2.status_code == 409, (r2.status_code, r2.text)
