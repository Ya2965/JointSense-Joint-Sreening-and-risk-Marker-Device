import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


def test_core_api_and_assessment():
    session = requests.Session()
    root = session.get(f"{BASE_URL}/api/")
    assert root.status_code == 200 and root.json()["simulator"] is True
    login = session.post(f"{BASE_URL}/api/auth/login", json={"identifier": "doctor1@jointsense.local", "password": "JointSense123!"})
    assert login.status_code == 200 and login.json()["user"]["username"] == "Doctor1"
    assert "access_token" in session.cookies or login.json().get("token")
    assert session.get(f"{BASE_URL}/api/auth/me").status_code == 200
    patient = session.post(f"{BASE_URL}/api/patients", json={"name": "TEST_JointSense Patient", "age": 67, "gender": "Female", "pain_duration": "8 months", "affected_leg": "Left leg"})
    assert patient.status_code == 200 and patient.json()["name"] == "TEST_JointSense Patient"
    patient_id = patient.json()["id"]
    detail = session.get(f"{BASE_URL}/api/patients/{patient_id}")
    assert detail.status_code == 200 and detail.json()["id"] == patient_id
    answers = {str(i): 2 for i in range(7)}
    start = session.post(f"{BASE_URL}/api/assessment/start", json={"patient_id": patient_id, "answers": answers, "pain_duration": "8 months", "affected_leg": "Left leg", "test": "two-minute-walk"})
    assert start.status_code == 200 and start.json()["status"] == "started"
    live = session.get(f"{BASE_URL}/api/assessment/live")
    assert live.status_code == 200 and live.json()["active"] is True and "gait_speed" in live.json()["features"]
    stop = session.post(f"{BASE_URL}/api/assessment/stop")
    assert stop.status_code == 200 and stop.json()["questionnaire_weight"] == 40 and stop.json()["movement_weight"] == 60
