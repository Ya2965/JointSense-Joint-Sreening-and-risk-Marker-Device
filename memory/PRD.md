# JointSense PRD

## Original problem statement
Build a professional web and mobile-friendly osteoarthritis early-risk detection app using the existing workspace and selected logic from the uploaded JointSense ZIP. The product should support demo simulator mode now and a future Raspberry Pi/ESP32 hardware adapter, functional local clinician accounts, seven languages, lavender/purple light and dark themes, rich transitions, KOS-style patient questions, movement tests, 40/60 scoring, SHAP-style explanations, detailed sensor/model values, and report output.

## Architecture decisions
- React 19 frontend with responsive CSS, Framer Motion transitions, Lucide icons, and browser session persistence.
- FastAPI backend with MongoDB using the protected `MONGO_URL` and `DB_NAME` values.
- JWT-backed local clinician authentication with bcrypt passwords, httpOnly cookie plus bearer-token support.
- Per-clinician assessment state, owner-scoped patient and screening records, and strict seven-answer validation.
- Demo simulator exposes hardware-shaped live values through the same assessment endpoints that can later connect to a Raspberry Pi/ESP32 adapter.
- Existing ZIP logic was inspected and the important simulator, sensor, feature, model, 40/60, and SHAP concepts were carried into the workspace API boundary.

## User personas
- Clinician or researcher running a guided screening with a patient.
- ML/edge-AI researcher reviewing raw movement features for future model training.
- Future hardware operator connecting the same workflow to ESP32 sensors and Raspberry Pi.

## Core requirements (static)
- Welcome onboarding, seven-language choice, login/signup, session persistence.
- Clinician dashboard with device state, metrics, patient search, and patient creation.
- Patient profile and screening history.
- KOS-style seven-item assessment plus pain duration and affected leg.
- Three selectable movement tests with simulator live values and safety guidance.
- 40% patient-reported + 60% movement score composition.
- Risk level, score explanation, SHAP-style contributors, raw feature values, questionnaire answers, and report action.
- Mobile-friendly layouts, light/dark lavender theme, meaningful animation, and unique `data-testid` coverage for test flows.

## What's implemented
- 2026-09-26: Replaced starter UI with complete JointSense onboarding, auth, dashboard, intake, patient profile, assessment, and results flows.
- 2026-09-26: Added MongoDB patient/screening persistence and local bcrypt/JWT clinician accounts.
- 2026-09-26: Added per-user simulator assessment state, strict ownership checks, live feature streaming, 40/60 scoring, and SHAP-style result output.
- 2026-09-26: Added all seven language choices, theme switching, responsive mobile layouts, clinical imagery, transitions, and print/download report action.
- 2026-09-26: Verified frontend production build, backend syntax, public API flow, incomplete-answer rejection, live values, and completed result generation.

## Prioritized backlog
- P0: Connect the hardware adapter to the existing `/api/assessment/live` contract and map real serial packets into feature values.
- P1: Add authorized translations for the official clinical instrument wording before clinical deployment.
- P1: Persist assessment drafts and completed multi-test sessions as separate test records instead of one final result.
- P2: Add clinician report PDF generation with clinic branding and exportable CSV feature data.
- P2: Add trend charts comparing a patient's screenings over time.

## Remaining next tasks
- Validate the Raspberry Pi/ESP32 serial adapter against representative packets.
- Confirm the model's production feature order and replace demo feature generation where available.
- Review clinical copy and instrument licensing with the responsible clinical team.
## Update — Feb 2026 · Real SHAP + Branded PDF
- `stop_assessment` now calls `model_explanation(features)` — real TreeSHAP over the shipped Random Forest at `/app/backend/ml/model.joblib`. `shap`, `shap_status`, `model_class`, `confidence` are all model-driven. Narrative `explanation` names the top TreeSHAP driver.
- New endpoint `GET /api/assessments/{screening_id}/pdf` returns a branded ReportLab PDF (lavender theme) with patient block, risk summary, top TreeSHAP contributions, all 10 sensor feature values, and full 7-question KOOS-PS response table. Auth-scoped to the clinician who owns the patient.
- Frontend `Results` page: `Download clinical PDF` button now hits the real endpoint (axios blob → `<a download>`), with a "Preparing report…" loading state. Removed `window.print()`.
- Removed the "Demo mode" chip from the assessment header per user request.
- Backend tests: `/app/backend/tests/test_shap_and_pdf.py` — 10/10 passing (iteration_2.json).

## Known non-blocking notes
- `assessment_states` is an in-memory per-user dict — single active screening per clinician per process.
- SHAP failures are silently downgraded to `shap_status: "unavailable"` (no logging).
