"""V2 backend tests: /hw/ingest, hardware mode live, leg-abduction, /settings, /screenings/{id}, patient latest_*, PDF w/ settings."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

CLINICIAN_EMAIL = "doctor1@jointsense.local"
CLINICIAN_PASSWORD = "JointSense123!"
HW_KEY = "jointsense-esp32-DEMO-key-change-me"

pytestmark = pytest.mark.xdist_group("v2_serial")


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"identifier": CLINICIAN_EMAIL, "password": CLINICIAN_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def patient(h):
    r = requests.post(f"{API}/patients", json={"name": "TEST_V2Patient", "age": 60, "gender": "Male", "affected_leg": "Right leg", "pain_duration": "3 months"}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _set_mode(h, mode):
    r = requests.put(f"{API}/settings", json={"clinic_name": "TEST Clinic", "signature_name": "Dr Test", "hardware_mode": mode}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


# --- /hw/ingest ---
class TestHardwareIngest:
    def test_ingest_valid_key(self):
        payload = {"device_key": HW_KEY, "test": "two-minute-walk", "features": {"gait_speed": 0.9, "cadence": 95.0, "total_rom": 55.0, "peak_loading": 120.0, "movement_smoothness": 0.8, "left_right_weight_asymmetry": 0.1, "acoustic_rms": 0.2, "sit_to_stand_time": 2.5, "fsr_heel": 80.0, "fsr_toe": 65.0}}
        r = requests.post(f"{API}/hw/ingest", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert "received_at" in data

    def test_ingest_wrong_key_401(self):
        r = requests.post(f"{API}/hw/ingest", json={"device_key": "wrong", "test": "two-minute-walk", "features": {"gait_speed": 0.9}})
        assert r.status_code == 401, r.text


# --- hardware mode live ---
class TestHardwareModeLive:
    def test_hardware_fresh_live(self, h, patient):
        _set_mode(h, "hardware")
        # push a fresh ingest with distinctive value
        feats = {"gait_speed": 1.234, "cadence": 100.0, "total_rom": 60.0, "peak_loading": 130.0, "movement_smoothness": 0.9, "left_right_weight_asymmetry": 0.05, "acoustic_rms": 0.15, "sit_to_stand_time": 2.0, "fsr_heel": 90.0, "fsr_toe": 70.0}
        r = requests.post(f"{API}/hw/ingest", json={"device_key": HW_KEY, "test": "two-minute-walk", "features": feats})
        assert r.status_code == 200
        # start assessment
        answers = {str(i): 2 for i in range(7)}
        r = requests.post(f"{API}/assessment/start", json={"patient_id": patient["id"], "answers": answers, "test": "two-minute-walk"}, headers=h)
        assert r.status_code == 200
        r = requests.get(f"{API}/assessment/live", headers=h)
        assert r.status_code == 200
        d = r.json()
        assert d["source"] == "hardware", d
        assert d["stale"] is False, d
        assert abs(d["features"]["gait_speed"] - 1.234) < 0.001, d["features"]
        # stop
        requests.post(f"{API}/assessment/stop", headers=h)

    def test_hardware_stale_falls_back_to_simulator(self, h, patient):
        _set_mode(h, "hardware")
        # wait for staleness (>4s) - push then wait
        requests.post(f"{API}/hw/ingest", json={"device_key": HW_KEY, "test": "two-minute-walk", "features": {"gait_speed": 5.5, "cadence": 100.0, "total_rom": 60.0, "peak_loading": 130.0, "movement_smoothness": 0.9, "left_right_weight_asymmetry": 0.05, "acoustic_rms": 0.15, "sit_to_stand_time": 2.0, "fsr_heel": 90.0, "fsr_toe": 70.0}})
        time.sleep(5)
        answers = {str(i): 2 for i in range(7)}
        requests.post(f"{API}/assessment/start", json={"patient_id": patient["id"], "answers": answers, "test": "two-minute-walk"}, headers=h)
        r1 = requests.get(f"{API}/assessment/live", headers=h).json()
        # New spec: auto-fallback to simulator when stale
        assert r1["source"] == "simulator", r1
        assert r1["stale"] is True, r1
        assert isinstance(r1["features"], dict) and "gait_speed" in r1["features"]
        # values non-zero and vary between polls
        assert r1["features"]["gait_speed"] != 0
        time.sleep(1.2)
        r2 = requests.get(f"{API}/assessment/live", headers=h).json()
        assert r1["features"] != r2["features"], (r1["features"], r2["features"])
        requests.post(f"{API}/assessment/stop", headers=h)

    def test_simulator_mode(self, h, patient):
        _set_mode(h, "simulator")
        answers = {str(i): 2 for i in range(7)}
        requests.post(f"{API}/assessment/start", json={"patient_id": patient["id"], "answers": answers, "test": "two-minute-walk"}, headers=h)
        r1 = requests.get(f"{API}/assessment/live", headers=h).json()
        assert r1["source"] == "simulator"
        time.sleep(1.2)
        r2 = requests.get(f"{API}/assessment/live", headers=h).json()
        # values should vary
        assert r1["features"] != r2["features"], (r1["features"], r2["features"])
        requests.post(f"{API}/assessment/stop", headers=h)


# --- leg-abduction ---
class TestLegAbduction:
    def test_leg_abduction_flow(self, h, patient):
        _set_mode(h, "simulator")
        answers = {str(i): 1 for i in range(7)}
        r = requests.post(f"{API}/assessment/start", json={"patient_id": patient["id"], "answers": answers, "test": "leg-abduction"}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["duration_seconds"] == 30
        live1 = requests.get(f"{API}/assessment/live", headers=h).json()
        assert live1["duration_seconds"] == 30
        rem1 = live1["remaining_seconds"]
        time.sleep(1.5)
        live2 = requests.get(f"{API}/assessment/live", headers=h).json()
        rem2 = live2["remaining_seconds"]
        assert rem2 < rem1, (rem1, rem2)
        r = requests.post(f"{API}/assessment/stop", headers=h)
        assert r.status_code == 200
        d = r.json()
        assert d["test"] == "leg-abduction"
        assert d["shap_status"] == "available"
        assert len(d["shap"]) >= 1


# --- settings persistence ---
class TestSettings:
    def test_get_and_put(self, h):
        r = requests.put(f"{API}/settings", json={"clinic_name": "TEST Clinic X", "signature_name": "Dr X", "hardware_mode": "simulator"}, headers=h)
        assert r.status_code == 200
        d = r.json()
        assert d["clinic_name"] == "TEST Clinic X"
        assert d["signature_name"] == "Dr X"
        assert d["hardware_mode"] == "simulator"
        # persistence
        r2 = requests.get(f"{API}/settings", headers=h)
        assert r2.status_code == 200
        assert r2.json() == d

    def test_invalid_hardware_mode_422(self, h):
        r = requests.put(f"{API}/settings", json={"clinic_name": "X", "signature_name": "Y", "hardware_mode": "gibberish"}, headers=h)
        assert r.status_code == 422, r.text


# --- /screenings/{id} ---
class TestScreeningDetail:
    @pytest.fixture(scope="class")
    def screening_id(self, h, patient):
        _set_mode(h, "simulator")
        answers = {str(i): 2 for i in range(7)}
        requests.post(f"{API}/assessment/start", json={"patient_id": patient["id"], "answers": answers, "test": "sit-to-stand"}, headers=h)
        time.sleep(1.2)
        r = requests.post(f"{API}/assessment/stop", headers=h)
        return r.json()["id"]

    def test_owner_can_read(self, h, screening_id):
        r = requests.get(f"{API}/screenings/{screening_id}", headers=h)
        assert r.status_code == 200
        assert r.json()["id"] == screening_id

    def test_unauth_401(self, screening_id):
        r = requests.get(f"{API}/screenings/{screening_id}")
        assert r.status_code == 401

    def test_cross_workspace_404(self, screening_id):
        # register second clinician
        email = f"test_v2_{uuid.uuid4().hex[:8]}@jointsense.local"
        username = f"Testv2{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/auth/register", json={"username": username, "email": email, "password": "Passw0rd!"})
        assert r.status_code == 200
        tok = r.json()["token"]
        r = requests.get(f"{API}/screenings/{screening_id}", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 404


# --- patient latest_* ---
class TestPatientLatest:
    def test_patient_has_latest_fields(self, h, patient):
        _set_mode(h, "simulator")
        answers = {str(i): 3 for i in range(7)}
        requests.post(f"{API}/assessment/start", json={"patient_id": patient["id"], "answers": answers, "test": "two-minute-walk"}, headers=h)
        time.sleep(1.2)
        stop = requests.post(f"{API}/assessment/stop", headers=h).json()
        r = requests.get(f"{API}/patients/{patient['id']}", headers=h)
        assert r.status_code == 200
        d = r.json()
        assert d.get("latest_risk_level") in {"Low", "Moderate", "High", "Very high"}
        assert isinstance(d.get("latest_risk_score"), (int, float))
        assert d.get("latest_screened_at")
        assert d["latest_risk_level"] == stop["risk_level"]
        assert "history" in d and any(s["id"] == stop["id"] for s in d["history"])


# --- PDF with settings ---
class TestPdfWithSettings:
    def test_pdf_larger_with_clinic_and_signature(self, h, patient):
        _set_mode(h, "simulator")
        answers = {str(i): 2 for i in range(7)}
        # baseline: empty settings
        requests.put(f"{API}/settings", json={"clinic_name": "", "signature_name": "", "hardware_mode": "simulator"}, headers=h)
        requests.post(f"{API}/assessment/start", json={"patient_id": patient["id"], "answers": answers, "test": "two-minute-walk"}, headers=h)
        time.sleep(1.2)
        sid1 = requests.post(f"{API}/assessment/stop", headers=h).json()["id"]
        r1 = requests.get(f"{API}/assessments/{sid1}/pdf", headers=h)
        assert r1.status_code == 200
        assert r1.content[:5] == b"%PDF-"
        base_size = len(r1.content)

        # now with clinic + signature
        requests.put(f"{API}/settings", json={"clinic_name": "TEST BigClinic Northwest Hospital", "signature_name": "Dr Test Signature Long Name", "hardware_mode": "simulator"}, headers=h)
        requests.post(f"{API}/assessment/start", json={"patient_id": patient["id"], "answers": answers, "test": "two-minute-walk"}, headers=h)
        time.sleep(1.2)
        sid2 = requests.post(f"{API}/assessment/stop", headers=h).json()["id"]
        r2 = requests.get(f"{API}/assessments/{sid2}/pdf", headers=h)
        assert r2.status_code == 200
        assert r2.content[:5] == b"%PDF-"
        assert len(r2.content) > base_size, (len(r2.content), base_size)
