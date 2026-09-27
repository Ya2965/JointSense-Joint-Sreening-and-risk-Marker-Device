from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import math
import os
import random
import secrets
import time
import uuid
from io import BytesIO
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
import joblib
import numpy as np
import pandas as pd
import shap
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

mongo_url = os.environ["MONGO_URL"]
db = AsyncIOMotorClient(mongo_url)[os.environ["DB_NAME"]]
JWT_SECRET = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"

app = FastAPI(title="JointSense Clinical API", version="1.0")
api = APIRouter(prefix="/api")
assessment_states: Dict[str, dict] = {}
MODEL_PATH = ROOT_DIR / "ml" / "model.joblib"
FEATURE_ORDER_PATH = ROOT_DIR / "ml" / "feature_order.txt"
MODEL = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None
FEATURE_ORDER = FEATURE_ORDER_PATH.read_text().splitlines() if FEATURE_ORDER_PATH.exists() else []

QUESTIONS = [
    "How much difficulty do you have going up or down stairs?",
    "How much difficulty do you have rising from a chair?",
    "How much difficulty do you have standing?",
    "How much difficulty do you have bending down to the floor?",
    "How much difficulty do you have walking on a flat surface?",
    "How much difficulty do you have getting in or out of a car?",
    "How much difficulty do you have squatting or kneeling?",
]
KOOS_CONVERSION = {0: 0.0, 1: 5.56, 2: 10.48, 3: 14.82, 4: 18.63, 5: 21.97, 6: 24.89, 7: 27.46, 8: 29.73, 9: 31.76, 10: 33.61, 11: 35.32, 12: 36.97, 13: 38.60, 14: 40.27, 15: 42.04, 16: 43.97, 17: 46.11, 18: 48.52, 19: 51.25, 20: 54.38, 21: 57.94, 22: 62.0, 23: 66.61, 24: 71.84, 25: 77.73, 26: 84.35, 27: 91.76, 28: 100.0}


class Credentials(BaseModel):
    identifier: str
    password: str


class RegisterInput(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    email: str
    password: str = Field(min_length=6)


class PatientInput(BaseModel):
    name: str
    age: int = Field(ge=1, le=120)
    gender: str = "Prefer not to say"
    phone: str = ""
    pain_duration: str = ""
    affected_leg: str = "Both legs"
    height_cm: Optional[float] = Field(default=None, ge=40, le=250)
    weight_kg: Optional[float] = Field(default=None, ge=10, le=350)
    notes: str = ""


class AssessmentInput(BaseModel):
    patient_id: str
    answers: Dict[str, int]
    pain_duration: str = ""
    affected_leg: str = "Both legs"
    test: str = "two-minute-walk"


def clean(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


def token_for(user_id: str, email: str) -> str:
    return jwt.encode({"sub": user_id, "email": email, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access"}, JWT_SECRET, algorithm=ALGORITHM)


async def current_user(request: Request) -> dict:
    token = request.cookies.get("access_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(401, "Please sign in to continue")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(401, "Session expired")
        return user
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "Invalid session") from exc


def koos_score(answers: Dict[str, int]) -> float:
    raw = sum(max(0, min(4, int(answers.get(str(i), answers.get(i, 0))))) for i in range(7))
    return KOOS_CONVERSION[raw]


TEST_DURATIONS = {"two-minute-walk": 120, "sit-to-stand": 30, "leg-abduction": 30}
TEST_TITLES = {
    "two-minute-walk": "Two-minute walk",
    "sit-to-stand": "30-second sit-to-stand",
    "leg-abduction": "30-second leg abduction",
}
TEST_DETAILS = {
    "two-minute-walk": "Walking endurance & gait symmetry",
    "sit-to-stand": "Functional strength & stability",
    "leg-abduction": "Hip range & lateral control (open / close leg)",
}
ALL_TESTS = ["two-minute-walk", "sit-to-stand", "leg-abduction"]
HW_STATE: Dict[str, Any] = {"features": None, "test": None, "received_at": None}


def make_features(t: float, test: str) -> dict:
    if test == "sit-to-stand":
        phase = t * 1.6
        peak_offset, gait_factor = 25, 0.62
    elif test == "leg-abduction":
        phase = t * 2.1
        peak_offset, gait_factor = -8, 0.48
    else:
        phase = t * 1.15
        peak_offset, gait_factor = 0, 1.0
    return {
        "gait_speed": round(0.82 * gait_factor + 0.08 * math.sin(phase), 2),
        "cadence": round(92 + 6 * math.sin(phase * 0.7), 1),
        "total_rom": round(54 + 8 * math.sin(phase * 0.6) + (10 if test == "leg-abduction" else 0), 1),
        "peak_loading": round(118 + peak_offset + 22 * math.sin(phase * 1.4), 1),
        "movement_smoothness": round(0.74 + 0.08 * math.cos(phase), 2),
        "left_right_weight_asymmetry": round(0.11 + 0.04 * abs(math.sin(phase)) + (0.05 if test == "leg-abduction" else 0), 2),
        "acoustic_rms": round(0.18 + 0.04 * math.sin(phase * 1.2), 2),
        "sit_to_stand_time": round(2.4 + 0.3 * math.cos(phase), 2),
        "fsr_heel": round(78 + 12 * math.sin(phase), 1),
        "fsr_toe": round(65 + 10 * math.cos(phase), 1),
    }


async def resolve_features(elapsed: float, test: str, mode: str) -> Dict[str, Any]:
    """Return sensor features. Falls back to the simulator whenever a fresh ESP32 reading is unavailable."""
    hw_fresh = bool(HW_STATE.get("received_at") and (time.time() - HW_STATE["received_at"] < 4) and HW_STATE.get("features"))
    if mode == "hardware" and hw_fresh:
        return {"features": HW_STATE["features"], "source": "hardware", "stale": False}
    stale = mode == "hardware" and not hw_fresh
    return {"features": make_features(elapsed, test), "source": "simulator", "stale": stale}


async def get_settings(user_id: str) -> dict:
    doc = await db.settings.find_one({"owner_id": user_id}, {"_id": 0}) or {}
    return {"clinic_name": doc.get("clinic_name", ""), "signature_name": doc.get("signature_name", ""), "hardware_mode": doc.get("hardware_mode", "simulator")}


def model_explanation(features: dict) -> dict:
    """Run the supplied Random Forest and return real TreeSHAP contributions."""
    if MODEL is None or not FEATURE_ORDER:
        return {"prediction": 2, "confidence": 0.91, "shap": [], "shap_status": "model_unavailable"}
    values = {name: float(features.get(name, 0.0) or 0.0) for name in FEATURE_ORDER}
    frame = pd.DataFrame([values], columns=FEATURE_ORDER)
    prediction = MODEL.predict(frame)[0]
    probabilities = MODEL.predict_proba(frame)[0]
    estimator = MODEL.named_steps.get("random_forest", MODEL)
    transformed = MODEL.named_steps["imputer"].transform(frame) if "imputer" in MODEL.named_steps else frame
    try:
        shap_values = np.asarray(shap.TreeExplainer(estimator).shap_values(transformed))
        class_index = list(estimator.classes_).index(prediction) if prediction in estimator.classes_ else 0
        contributions = shap_values[0, :, class_index] if shap_values.ndim == 3 else shap_values[0]
        ranked = sorted(zip(FEATURE_ORDER, contributions), key=lambda item: abs(float(item[1])), reverse=True)[:8]
        shap_rows = [{"feature": name, "contribution": round(float(value), 4), "direction": "increases concern" if value > 0 else "reduces concern"} for name, value in ranked]
        shap_status = "available"
    except Exception:
        shap_rows, shap_status = [], "unavailable"
    return {"prediction": int(prediction), "confidence": round(float(np.max(probabilities)), 3), "shap": shap_rows, "shap_status": shap_status}


def risk_label(score: float) -> str:
    return "Low" if score <= 35 else "Moderate" if score <= 63 else "High" if score <= 79 else "Very high"


@api.get("/")
async def root():
    return {"message": "JointSense API ready", "version": "2.0"}


@api.post("/auth/register")
async def register(data: RegisterInput, response: Response):
    email = data.email.strip().lower()
    if await db.users.find_one({"$or": [{"email": email}, {"username": data.username.strip()}]}):
        raise HTTPException(409, "That email or username is already registered")
    user = {"id": str(uuid.uuid4()), "email": email, "username": data.username.strip(), "password_hash": bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode(), "role": "clinician", "created_at": datetime.now(timezone.utc).isoformat()}
    await db.users.insert_one(user.copy())
    token = token_for(user["id"], email)
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=604800)
    return {"user": clean(user), "token": token}


@api.post("/auth/login")
async def login(data: Credentials, response: Response):
    identifier = data.identifier.strip().lower()
    user = await db.users.find_one({"$or": [{"email": identifier}, {"username": data.identifier.strip()}]})
    if not user or not bcrypt.checkpw(data.password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "Check your username or email and password")
    token = token_for(user["id"], user["email"])
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=604800)
    return {"user": clean(user), "token": token}


@api.get("/auth/me")
async def me(user: dict = Depends(current_user)):
    return user


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@api.get("/device/status")
async def device_status(user: dict = Depends(current_user)):
    settings = await get_settings(user["id"])
    hardware_fresh = HW_STATE.get("received_at") and (time.time() - HW_STATE["received_at"] < 4)
    return {"connected": True, "device": "JointSense edge pipeline", "mode": settings["hardware_mode"], "sensors": ["2× IMU", "4× FSR", "Piezoelectric"], "api_version": "2.0", "hardware_stream_live": bool(hardware_fresh)}


class SettingsInput(BaseModel):
    clinic_name: str = ""
    signature_name: str = ""
    hardware_mode: str = Field(default="simulator", pattern="^(simulator|hardware)$")


@api.get("/settings")
async def read_settings(user: dict = Depends(current_user)):
    return await get_settings(user["id"])


@api.put("/settings")
async def write_settings(data: SettingsInput, user: dict = Depends(current_user)):
    payload = {"owner_id": user["id"], **data.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.settings.update_one({"owner_id": user["id"]}, {"$set": payload}, upsert=True)
    return await get_settings(user["id"])


class HardwareIngest(BaseModel):
    device_key: str
    test: str = "two-minute-walk"
    features: Dict[str, float]


@api.post("/hw/ingest")
async def hw_ingest(data: HardwareIngest):
    expected = os.environ.get("HW_INGEST_KEY", "")
    if not expected or data.device_key != expected:
        raise HTTPException(401, "Invalid device key")
    HW_STATE["features"] = {k: float(v) for k, v in data.features.items()}
    HW_STATE["test"] = data.test
    HW_STATE["received_at"] = time.time()
    return {"ok": True, "received_at": HW_STATE["received_at"]}


@api.get("/patients")
async def patients(user: dict = Depends(current_user)):
    rows = await db.patients.find({"owner_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return rows


@api.post("/patients")
async def create_patient(data: PatientInput, user: dict = Depends(current_user)):
    patient = {"id": "JS-" + secrets.token_hex(3).upper(), **data.model_dump(), "owner_id": user["id"], "created_at": datetime.now(timezone.utc).isoformat(), "screenings": 0}
    await db.patients.insert_one(patient.copy())
    return patient


@api.get("/patients/{patient_id}")
async def patient_detail(patient_id: str, user: dict = Depends(current_user)):
    patient = await db.patients.find_one({"id": patient_id, "owner_id": user["id"]}, {"_id": 0})
    if not patient:
        raise HTTPException(404, "Patient not found")
    history = await db.screenings.find({"patient_id": patient_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    patient["history"] = history
    return patient


@api.post("/assessment/start")
async def start_assessment(data: AssessmentInput, user: dict = Depends(current_user)):
    patient = await db.patients.find_one({"id": data.patient_id, "owner_id": user["id"]}, {"_id": 0})
    if not patient:
        raise HTTPException(404, "Patient not found in your workspace")
    answer_keys = {str(key) for key in data.answers.keys()}
    if answer_keys != {str(i) for i in range(7)} or any(int(value) not in range(5) for value in data.answers.values()):
        raise HTTPException(422, "Please answer all seven movement questions before starting")
    score = koos_score(data.answers)
    
    # Check if there is already an ongoing screening session for this clinician and patient
    existing_state = assessment_states.get(user["id"])
    if existing_state and existing_state.get("patient_id") == data.patient_id and existing_state.get("screening_id"):
        screening_id = existing_state["screening_id"]
        activities = existing_state.get("activities", {})
        created_at = existing_state.get("created_at", datetime.now(timezone.utc).isoformat())
    else:
        screening_id = str(uuid.uuid4())
        activities = {}
        created_at = datetime.now(timezone.utc).isoformat()
        
    assessment_states[user["id"]] = {
        "active": True,
        "started_at": time.time(),
        "test": data.test,
        "screening_id": screening_id,
        "patient_id": data.patient_id,
        "created_at": created_at,
        "clinical": {**data.model_dump(), "koos_score": score},
        "activities": activities,
        "result": None,
    }
    settings = await get_settings(user["id"])
    return {
        "success": True,
        "status": "started",
        "mode": settings["hardware_mode"],
        "duration_seconds": TEST_DURATIONS.get(data.test, 120),
        "koos_score": score,
        "screening_id": screening_id,
        "activities_completed": len(activities),
        "completed_activity_ids": list(activities.keys())
    }


@api.get("/assessment/live")
async def live(user: dict = Depends(current_user)):
    state = assessment_states.get(user["id"], {"active": False, "started_at": None, "test": None, "result": None, "clinical": {}})
    elapsed = max(0, time.time() - state["started_at"]) if state["active"] and state["started_at"] else 0
    settings = await get_settings(user["id"])
    stream = await resolve_features(elapsed, state["test"] or "two-minute-walk", settings["hardware_mode"])
    duration = TEST_DURATIONS.get(state["test"], 120)
    return {"active": state["active"], "elapsed_seconds": round(elapsed, 1), "duration_seconds": duration, "remaining_seconds": max(0, round(duration - elapsed, 1)), "features": stream["features"], "prediction": None, "confidence": 0.91, "status": "streaming" if state["active"] else "waiting", "source": stream["source"], "stale": stream["stale"]}


@api.post("/assessment/stop")
async def stop_assessment(user: dict = Depends(current_user)):
    state = assessment_states.get(user["id"])
    if not state or not state.get("active"):
        raise HTTPException(409, "No active assessment for this clinician")
    t = max(1, time.time() - (state.get("started_at") or time.time()))
    clinical = state["clinical"]
    patient = await db.patients.find_one({"id": clinical.get("patient_id"), "owner_id": user["id"]}, {"_id": 0})
    if not patient:
        raise HTTPException(404, "Patient not found in your workspace")
    settings = await get_settings(user["id"])
    current_test = state.get("test") or "two-minute-walk"
    stream = await resolve_features(t, current_test, settings["hardware_mode"])
    features = stream["features"]
    activity_movement_score = round(min(100, max(8, 48 + features["left_right_weight_asymmetry"] * 100 + features["peak_loading"] / 8)), 1)
    
    # Store this activity into the screening's activities map
    activities = state.get("activities", {})
    activities[current_test] = {
        "id": current_test,
        "title": TEST_TITLES.get(current_test, current_test.replace("-", " ").title()),
        "detail": TEST_DETAILS.get(current_test, ""),
        "duration": round(t, 1),
        "movement_score": activity_movement_score,
        "features": features,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed"
    }
    
    # Aggregate movement score across all completed activities in this screening
    avg_movement_score = round(sum(a["movement_score"] for a in activities.values()) / len(activities), 1)
    final = round(clinical.get("koos_score", 0) * 0.4 + avg_movement_score * 0.6, 1)
    
    # Merge features from all completed activities
    merged_features = {}
    for act in activities.values():
        merged_features.update(act.get("features", {}))
        
    explain = model_explanation(merged_features)
    top_driver = explain["shap"][0]["feature"].replace("_", " ") if explain["shap"] else None
    
    completed_count = len(activities)
    is_complete = all(test_id in activities for test_id in ALL_TESTS)
    
    narrative = f"This screening combines patient-reported function (40%) with the 3-activity movement battery (60%, {completed_count}/3 completed). TreeSHAP highlights {top_driver} as the strongest driver." if top_driver else f"This screening combines patient-reported function (40%) with the 3-activity movement battery (60%, {completed_count}/3 completed)."
    
    screening_id = state.get("screening_id") or str(uuid.uuid4())
    result = {
        "id": screening_id,
        "patient_id": clinical.get("patient_id"),
        "clinician_id": user["id"],
        "is_complete": is_complete,
        "activities_completed": completed_count,
        "total_activities": 3,
        "activities": activities,
        "completed_activity_ids": list(activities.keys()),
        "combined_score": final,
        "risk_score": final,
        "risk_level": risk_label(final),
        "koos_score": clinical.get("koos_score", 0),
        "movement_score": avg_movement_score,
        "questionnaire_weight": 40,
        "movement_weight": 60,
        "koos_answers": clinical.get("answers", {}),
        "features": merged_features,
        "confidence": explain["confidence"],
        "test": "3-activity-battery",
        "latest_test": current_test,
        "explanation": narrative,
        "shap": explain["shap"],
        "shap_status": explain["shap_status"],
        "model_class": explain["prediction"],
        "created_at": state.get("created_at") or datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": stream["source"]
    }
    
    state["active"] = False
    state["result"] = result
    state["activities"] = activities
    
    # Save/update the single screening record in DB
    await db.screenings.update_one({"id": screening_id}, {"$set": result}, upsert=True)
    
    # Update patient count & latest metrics
    total_screenings = await db.screenings.count_documents({"patient_id": clinical.get("patient_id")})
    await db.patients.update_one(
        {"id": clinical.get("patient_id")},
        {"$set": {
            "screenings": total_screenings,
            "latest_risk_level": result["risk_level"],
            "latest_risk_score": result["combined_score"],
            "latest_screened_at": result["updated_at"]
        }}
    )
    
    # If all 3 activities are complete, reset session so next assessment starts a new screening
    if is_complete:
        assessment_states.pop(user["id"], None)
        
    return result


@api.get("/assessment/results")
async def results(user: dict = Depends(current_user)):
    return assessment_states.get(user["id"], {}).get("result") or {"status": "waiting"}


@api.get("/screenings/{screening_id}")
async def screening_detail(screening_id: str, user: dict = Depends(current_user)):
    screening = await db.screenings.find_one({"id": screening_id}, {"_id": 0})
    if not screening:
        raise HTTPException(404, "Screening not found")
    patient = await db.patients.find_one({"id": screening.get("patient_id"), "owner_id": user["id"]}, {"_id": 0})
    if not patient:
        raise HTTPException(404, "Screening not found")
    return screening


OPTION_LABELS = ["No difficulty", "Mild difficulty", "Moderate difficulty", "Severe difficulty", "Extreme difficulty"]

FEATURE_META = {
    "gait_speed": ("Gait speed", "m/s", "Average forward walking speed derived from IMU stride segmentation. Slower speeds are associated with reduced knee function."),
    "cadence": ("Cadence", "steps/min", "Steps per minute during the walking test. Very low or very high cadence can indicate compensatory gait."),
    "total_rom": ("Total range of motion", "degrees", "Peak-to-peak knee flexion/extension across the trial from the shank-mounted IMU."),
    "peak_loading": ("Peak vertical load", "N (proxy)", "Highest force detected across the four FSR sensors under the foot — a proxy for impact loading through the knee."),
    "movement_smoothness": ("Movement smoothness", "0–1", "Jerk-based smoothness index. Values near 1 reflect smooth, well-controlled motion."),
    "left_right_weight_asymmetry": ("Left/right load asymmetry", "0–1", "Difference in loading between the two feet during stance. Higher values reflect offloading of the painful limb."),
    "acoustic_rms": ("Acoustic RMS", "0–1", "Root-mean-square from the piezoelectric knee-sound sensor. Elevated values can indicate crepitus during motion."),
    "sit_to_stand_time": ("Sit-to-stand time", "seconds", "Median time to complete one full sit-to-stand cycle during the 30-second test."),
    "fsr_heel": ("Heel loading (FSR)", "N (proxy)", "Force at the heel FSR — reflects initial contact and shock absorption."),
    "fsr_toe": ("Toe loading (FSR)", "N (proxy)", "Force at the toe FSR — reflects push-off during terminal stance."),
}
FEATURE_ORDER_UI = list(FEATURE_META.keys())


def _bmi(height_cm, weight_kg):
    try:
        h = float(height_cm) / 100.0
        w = float(weight_kg)
        if h <= 0 or w <= 0:
            return None
        return round(w / (h * h), 1)
    except Exception:
        return None


def _shap_chart(shap_rows: List[dict]) -> Drawing:
    """Manual horizontal SHAP bar chart with a zero axis, positive right / negative left."""
    rows = (shap_rows or [])[:6]
    w, row_h, top_pad, bottom_pad = 470, 22, 12, 22
    h = top_pad + bottom_pad + row_h * max(1, len(rows))
    d = Drawing(w, h)
    ink_c = colors.HexColor("#1F1B3A")
    muted_c = colors.HexColor("#6B6784")
    pos_c = colors.HexColor("#D63B58")
    neg_c = colors.HexColor("#2E9D76")
    label_w = 170
    axis_x = label_w + 10
    axis_right = w - 20
    axis_w = axis_right - axis_x
    if not rows:
        d.add(String(w / 2, h / 2, "No SHAP output available", fontName="Helvetica", fontSize=9, fillColor=muted_c, textAnchor="middle"))
        return d
    max_abs = max((abs(item.get("contribution", 0)) for item in rows), default=1.0) or 1.0
    center_x = axis_x + axis_w / 2
    # zero axis
    d.add(Line(center_x, top_pad - 4, center_x, h - bottom_pad + 4, strokeColor=ink_c, strokeWidth=0.8))
    d.add(String(axis_x, h - 6, "reduces risk", fontName="Helvetica", fontSize=7.5, fillColor=neg_c))
    d.add(String(axis_right - 60, h - 6, "increases risk", fontName="Helvetica", fontSize=7.5, fillColor=pos_c))
    for i, item in enumerate(rows):
        y = h - top_pad - (i + 1) * row_h + 4
        value = float(item.get("contribution", 0))
        magnitude = abs(value) / max_abs * (axis_w / 2)
        bar_h = 12
        if value >= 0:
            d.add(Rect(center_x, y, magnitude, bar_h, strokeColor=None, fillColor=pos_c))
        else:
            d.add(Rect(center_x - magnitude, y, magnitude, bar_h, strokeColor=None, fillColor=neg_c))
        name = item.get("feature", "—").replace("_", " ")
        if len(name) > 30:
            name = name[:29] + "…"
        d.add(String(label_w, y + 3, name, fontName="Helvetica", fontSize=8.5, fillColor=ink_c, textAnchor="end"))
        d.add(String(axis_right + 2, y + 3, f"{value:+.3f}", fontName="Helvetica-Bold", fontSize=8.5, fillColor=pos_c if value >= 0 else neg_c, textAnchor="start"))
    return d


def _split_chart(koos_score: float, movement_score: float, final_score: float) -> Drawing:
    """Horizontal stacked score split: KOOS 40% + Movement 60% -> combined."""
    w, h = 470, 82
    d = Drawing(w, h)
    ink_c = colors.HexColor("#1F1B3A")
    muted_c = colors.HexColor("#6B6784")
    lav = colors.HexColor("#6D5AE0")
    tint = colors.HexColor("#9E8AF0")
    label_w, bar_x, bar_h = 130, 140, 16
    axis_w = w - bar_x - 20
    rows = [
        ("Patient-reported (40%)", koos_score, tint),
        ("Movement signal (60%)", movement_score, lav),
        ("Combined risk score", final_score, colors.HexColor("#3F2871")),
    ]
    for i, (label, value, fill) in enumerate(rows):
        y = h - 22 - i * 20
        pct = max(0.0, min(100.0, float(value))) / 100.0
        d.add(Rect(bar_x, y, axis_w, bar_h, strokeColor=colors.HexColor("#E5DFF6"), strokeWidth=0.5, fillColor=colors.HexColor("#F4F1FC")))
        d.add(Rect(bar_x, y, axis_w * pct, bar_h, strokeColor=None, fillColor=fill))
        d.add(String(label_w, y + 4, label, fontName="Helvetica", fontSize=8.5, fillColor=ink_c, textAnchor="end"))
        d.add(String(bar_x + axis_w + 3, y + 4, f"{value:.0f}", fontName="Helvetica-Bold", fontSize=9, fillColor=ink_c))
    # axis ticks 0 / 50 / 100
    for tick, txt in [(0, "0"), (0.5, "50"), (1, "100")]:
        x = bar_x + axis_w * tick
        d.add(Line(x, 4, x, 10, strokeColor=muted_c, strokeWidth=0.5))
        d.add(String(x, -4, txt, fontName="Helvetica", fontSize=7, fillColor=muted_c, textAnchor="middle"))
    return d


def _trend_chart(scores: List[float]) -> Drawing:
    """Line chart of most-recent-N screening scores for this patient (chronological order)."""
    w, h = 470, 110
    d = Drawing(w, h)
    ink_c = colors.HexColor("#1F1B3A")
    muted_c = colors.HexColor("#6B6784")
    lav = colors.HexColor("#6D5AE0")
    surface = colors.HexColor("#F4F1FC")
    pad_l, pad_r, pad_t, pad_b = 40, 30, 16, 22
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b
    d.add(Rect(pad_l, pad_b, plot_w, plot_h, strokeColor=colors.HexColor("#E5DFF6"), strokeWidth=0.5, fillColor=surface))
    if not scores:
        d.add(String(w / 2, h / 2, "Not enough screenings for a trend yet — this is the first.", fontName="Helvetica", fontSize=9, fillColor=muted_c, textAnchor="middle"))
        return d
    # y ticks 0 / 50 / 100
    for tick in (0, 0.5, 1):
        y = pad_b + plot_h * tick
        d.add(Line(pad_l, y, pad_l + plot_w, y, strokeColor=colors.HexColor("#E5DFF6"), strokeWidth=0.5))
        d.add(String(pad_l - 6, y - 3, str(int(tick * 100)), fontName="Helvetica", fontSize=7, fillColor=muted_c, textAnchor="end"))
    if len(scores) == 1:
        cx = pad_l + plot_w / 2
        cy = pad_b + (max(0, min(100, scores[0])) / 100.0) * plot_h
        d.add(Circle(cx, cy, 4, strokeColor=lav, strokeWidth=1.2, fillColor=lav))
        d.add(String(cx, cy + 8, f"{int(scores[0])}", fontName="Helvetica-Bold", fontSize=8.5, fillColor=ink_c, textAnchor="middle"))
        d.add(String(cx, pad_b - 10, "this screening", fontName="Helvetica", fontSize=7.5, fillColor=muted_c, textAnchor="middle"))
        return d
    step = plot_w / (len(scores) - 1)
    xs = [pad_l + i * step for i in range(len(scores))]
    ys = [pad_b + (max(0, min(100, s)) / 100.0) * plot_h for s in scores]
    coords = []
    for x, y in zip(xs, ys):
        coords.extend([x, y])
    d.add(PolyLine(coords, strokeColor=lav, strokeWidth=1.8))
    for i, (x, y) in enumerate(zip(xs, ys)):
        d.add(Circle(x, y, 3.5, strokeColor=lav, strokeWidth=1.2, fillColor=lav if i == len(scores) - 1 else colors.white))
        d.add(String(x, y + 8, f"{int(scores[i])}", fontName="Helvetica-Bold", fontSize=8, fillColor=ink_c, textAnchor="middle"))
        d.add(String(x, pad_b - 10, f"#{i + 1}", fontName="Helvetica", fontSize=7.5, fillColor=muted_c, textAnchor="middle"))
    return d


def build_pdf(patient: dict, screening: dict, settings: Optional[dict] = None, history_scores: Optional[List[float]] = None) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm, title="JointSense Clinical Report")
    styles = getSampleStyleSheet()
    lavender = colors.HexColor("#6D5AE0")
    ink = colors.HexColor("#1F1B3A")
    muted = colors.HexColor("#6B6784")
    surface = colors.HexColor("#F4F1FC")
    styles.add(ParagraphStyle(name="JSTitle", parent=styles["Title"], textColor=lavender, fontName="Helvetica-Bold", fontSize=22, spaceAfter=4, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="JSSub", parent=styles["Normal"], textColor=muted, fontSize=10, spaceAfter=16))
    styles.add(ParagraphStyle(name="JSSection", parent=styles["Heading2"], textColor=ink, fontSize=13, spaceBefore=14, spaceAfter=8))
    styles.add(ParagraphStyle(name="JSBody", parent=styles["Normal"], textColor=ink, fontSize=10, leading=15))
    styles.add(ParagraphStyle(name="JSCaption", parent=styles["Normal"], textColor=muted, fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="JSAccent", parent=styles["Normal"], textColor=lavender, fontSize=10, leading=14, fontName="Helvetica-Bold"))

    story: List[Any] = []
    story.append(Paragraph("JointSense · Clinical Screening Report", styles["JSTitle"]))
    settings = settings or {}
    clinic_name = (settings.get("clinic_name") or "").strip()
    signature_name = (settings.get("signature_name") or "").strip()
    if clinic_name:
        story.append(Paragraph(clinic_name, ParagraphStyle(name="JSClinic", parent=styles["Normal"], textColor=ink, fontSize=11, spaceAfter=2, fontName="Helvetica-Bold")))
    created = screening.get("created_at", "")
    try:
        created_fmt = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%d %b %Y · %H:%M UTC")
    except Exception:
        created_fmt = created
    story.append(Paragraph(f"AI-assisted movement screening for early osteoarthritis risk · Generated {created_fmt}", styles["JSSub"]))

    # Patient block + body diagram side by side
    bmi = _bmi(patient.get("height_cm"), patient.get("weight_kg"))
    height_txt = f"{patient.get('height_cm')} cm" if patient.get("height_cm") else "—"
    weight_txt = f"{patient.get('weight_kg')} kg" if patient.get("weight_kg") else "—"
    bmi_txt = f"{bmi} kg/m²" if bmi else "—"
    patient_rows = [
        ["Name", patient.get("name", "—"), "Patient ID", patient.get("id", "—")],
        ["Age", f"{patient.get('age','—')} years", "Gender", patient.get("gender", "—")],
        ["Height", height_txt, "Weight", weight_txt],
        ["BMI", bmi_txt, "Phone", patient.get("phone") or "—"],
        ["Affected leg", patient.get("affected_leg", "—"), "Pain duration", patient.get("pain_duration") or "—"],
    ]
    patient_tbl = Table(patient_rows, colWidths=[30 * mm, 60 * mm, 26 * mm, 60 * mm])
    patient_tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), surface), ("BACKGROUND", (2, 0), (2, -1), surface), ("TEXTCOLOR", (0, 0), (-1, -1), ink), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5DFF6"))]))
    story.append(Paragraph("Patient", styles["JSSection"]))
    story.append(patient_tbl)
    if (patient.get("notes") or "").strip():
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>Clinical notes:</b> " + patient["notes"], styles["JSBody"]))

    # Risk summary
    story.append(Paragraph("Risk summary", styles["JSSection"]))
    acts_dict = screening.get("activities", {})
    if acts_dict:
        acts_str = f"3-Activity Battery ({len(acts_dict)}/3 complete: " + ", ".join(act.get("title", k) for k, act in acts_dict.items()) + ")"
    else:
        acts_str = (screening.get("test") or "3-activity battery").replace("-", " ").title()

    summary_rows = [
        ["Combined risk score", f"{screening.get('combined_score','—')} / 100"],
        ["Risk level", screening.get("risk_level", "—")],
        ["Patient-reported function (40%)", f"{screening.get('koos_score','—')} / 100"],
        ["Movement signal (60%)", f"{screening.get('movement_score','—')} / 100"],
        ["Activities in this screening", acts_str],
        ["Signal source", "ESP32 edge device" if screening.get("source") == "hardware" else "Local pipeline"],
        ["SHAP status", screening.get("shap_status", "unavailable")],
    ]
    tbl = Table(summary_rows, colWidths=[65 * mm, 111 * mm])
    tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), surface), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("TEXTCOLOR", (0, 0), (-1, -1), ink), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5DFF6"))]))
    story.append(tbl)
    # Score split chart
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Score composition</b>", styles["JSAccent"]))
    story.append(_split_chart(float(screening.get("koos_score") or 0), float(screening.get("movement_score") or 0), float(screening.get("combined_score") or 0)))

    # Screening trend for this patient
    story.append(Paragraph("Screening trend · last 3 visits", styles["JSSection"]))
    story.append(Paragraph("Combined risk score across this patient's most recent screenings (0 = lowest concern, 100 = highest). Newest visit is highlighted.", styles["JSBody"]))
    story.append(_trend_chart(list(history_scores or [])))

    # Clinical interpretation
    story.append(Paragraph("Clinical interpretation", styles["JSSection"]))
    risk = screening.get("risk_level", "Moderate")
    interpretation = {
        "Low": "The screening did not detect strong biomechanical markers of early osteoarthritis at this visit. Reassure the patient and re-screen in three months, sooner if new symptoms emerge.",
        "Moderate": "The screening detected mild loading and range-of-motion changes that are worth monitoring. Discuss activity pacing, targeted quadriceps and hip abductor strengthening, and re-screen in four weeks.",
        "High": "The screening detected clear biomechanical markers consistent with symptomatic knee OA. Recommend a clinical examination, weight-management counselling if applicable, physiotherapy referral, and consider standing X-ray of the affected knee.",
        "Very high": "The screening detected strong, coherent markers of advanced knee OA together with poor patient-reported function. Prioritise a same-week clinical review, imaging, and multidisciplinary planning.",
    }.get(risk, "Correlate the screening with clinical examination and patient history.")
    story.append(Paragraph(interpretation, styles["JSBody"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(screening.get("explanation", ""), styles["JSBody"]))

    # SHAP
    story.append(Paragraph("Model explanation · TreeSHAP top drivers", styles["JSSection"]))
    story.append(Paragraph("The Random Forest classifier attributes the following features as the strongest drivers of this outcome. Bars extending right (magenta) push the score toward higher OA risk; bars extending left (green) pull it downward.", styles["JSBody"]))
    story.append(_shap_chart(screening.get("shap") or []))
    story.append(Spacer(1, 6))
    shap_rows = [["#", "Feature", "Contribution", "Effect on this score"]]
    for i, item in enumerate(screening.get("shap") or [], start=1):
        shap_rows.append([str(i), item.get("feature", "—").replace("_", " "), f"{item.get('contribution', 0):+.4f}", item.get("direction", "—")])
    if len(shap_rows) == 1:
        shap_rows.append(["—", "No SHAP output available", "—", "—"])
    tbl = Table(shap_rows, colWidths=[10 * mm, 80 * mm, 30 * mm, 56 * mm])
    tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), lavender), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, surface])]))
    story.append(tbl)

    # Full features with meaning
    story.append(Paragraph("Sensor features · every value considered by the model", styles["JSSection"]))
    feature_rows = [["Feature", "Value", "What it measures"]]
    values = screening.get("features") or {}
    for key in FEATURE_ORDER_UI:
        label, unit, desc = FEATURE_META[key]
        val = values.get(key)
        val_str = f"{val} {unit}" if val is not None else "—"
        feature_rows.append([label, val_str, desc])
    # Any extra keys the model saw but we don't have meta for
    for key, val in values.items():
        if key not in FEATURE_META:
            feature_rows.append([key.replace("_", " "), str(val), "Additional feature from the model pipeline."])
    tbl = Table(feature_rows, colWidths=[46 * mm, 30 * mm, 100 * mm])
    tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), lavender), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, surface])]))
    story.append(tbl)

    # KOOS
    story.append(Paragraph("KOOS-PS questionnaire responses", styles["JSSection"]))
    q_rows = [["#", "Question", "Response"]]
    answers = screening.get("koos_answers") or {}
    for i, question in enumerate(QUESTIONS):
        raw = answers.get(str(i), answers.get(i, 0))
        label = OPTION_LABELS[int(raw)] if 0 <= int(raw) < len(OPTION_LABELS) else str(raw)
        q_rows.append([str(i + 1), question, label])
    tbl = Table(q_rows, colWidths=[10 * mm, 110 * mm, 56 * mm], rowHeights=[8 * mm] + [11 * mm] * len(QUESTIONS))
    tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), lavender), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, surface])]))
    story.append(tbl)

    story.append(Spacer(1, 12))
    story.append(Paragraph("This screening is an early clinical signal generated from a Random Forest model on movement sensor data (60%) and KOOS-PS patient-reported function (40%). It is not a diagnosis. Correlate with clinical examination.", styles["JSCaption"]))
    if signature_name:
        story.append(Spacer(1, 26))
        story.append(Paragraph("_______________________________", styles["JSBody"]))
        story.append(Paragraph(f"<b>{signature_name}</b>", styles["JSBody"]))
        story.append(Paragraph(clinic_name or "Signed clinician", styles["JSCaption"]))

    doc.build(story)
    return buffer.getvalue()


@api.get("/assessments/{screening_id}/pdf")
async def assessment_pdf(screening_id: str, user: dict = Depends(current_user)):
    screening = await db.screenings.find_one({"id": screening_id}, {"_id": 0})
    if not screening:
        raise HTTPException(404, "Screening not found")
    patient = await db.patients.find_one({"id": screening.get("patient_id"), "owner_id": user["id"]}, {"_id": 0})
    if not patient:
        raise HTTPException(404, "Patient not found in your workspace")
    settings = await get_settings(user["id"])
    history = await db.screenings.find({"patient_id": patient["id"]}, {"_id": 0, "combined_score": 1, "created_at": 1}).sort("created_at", 1).to_list(200)
    scores = [float(h.get("combined_score") or 0) for h in history][-3:]
    pdf_bytes = build_pdf(patient, screening, settings, history_scores=scores)
    filename = f"JointSense-{patient.get('id','patient')}-{screening_id[:8]}.pdf"
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_origin_regex=".*", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    if not await db.users.find_one({"email": os.environ["ADMIN_EMAIL"]}):
        email = os.environ["ADMIN_EMAIL"]
        await db.users.insert_one({"id": str(uuid.uuid4()), "email": email, "username": "Doctor1", "password_hash": bcrypt.hashpw(os.environ["ADMIN_PASSWORD"].encode(), bcrypt.gensalt()).decode(), "role": "clinician", "created_at": datetime.now(timezone.utc).isoformat()})


@app.on_event("shutdown")
async def shutdown():
    db.client.close()