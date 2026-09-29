# JointSense — Joint Screening and Risk Marker Device

JointSense is an integrated medical-tech application designed for non-invasive joint screening, mobility assessment, and biomechanical risk marker detection.

> **AI-Assisted Wearable Multi-Sensor Field-Deployable Kit for OA Risk Screening**
> Smart India Hackathon 2026 · Problem Statement **SIH26004** · Team **Rocket** (Team ID 121133) · Theme: MedTech / BioTech / HealthTech · Category: Hardware

JointSense is a wearable multi-sensor kit that captures gait, joint vibration, and plantar loading data, combines it with symptom questionnaires through an edge-AI algorithm, and generates an **explainable knee osteoarthritis (OA) risk score** on a handheld device.

---

## 🔗 Important Links

| Resource | What you will find | Link |
|---|---|---|
| 📚 Docs & references | Project documentation and research references | [`docs/`](docs/references) |
| ✅ Validation | Validation protocols and datasets | [`validation/`](validation/data) |
| 🔧 Hardware | Hardware folder (BOM, pinout) | [`hardware/`](hardware/) |
| 🧾 Bill of Materials | Components, specifications and costs | [`hardware/BOM and specifications`](hardware/BOM%20and%20specifications) |
| 📌 Pinout reference | ESP32 / sensor wiring and pin assignments | [`hardware/pinout reference`](hardware/pinout%20reference) |
| 🧠 Firmware | ESP32 firmware (dual BMI270 knee-angle test) | [`firmware/main.ino`](firmware/main.ino) |
| 🖥️ Backend API | FastAPI server, ML model, PDF reports | [`backend/`](backend/) |
| 🎨 Frontend | React clinician interface | [`frontend/`](frontend/) |
| 🧪 Test reports | Pytest and end-to-end test results | [`test_reports/`](test_reports/) |
| 📝 Product requirements | PRD, architecture decisions, backlog | [`memory/PRD.md`](memory/PRD.md) |

> **Note:** the BOM, pinout, docs and validation files are currently placeholders and are being filled in. Each link above will show the latest content as it is added.

---

## 🩺 The Problem

- **74% MSD prevalence in the North Eastern Region (NER):** a study of Northeast Indian farmers found that 74% experienced work-related musculoskeletal disorders due to labour-intensive practices on steep terrain. [1]
- **29.4% knee OA in NE cohorts:** knee OA accounts for nearly a third of joint-pain cases among rural Assam tea garden workers, driven by heavy basket loads and ergonomic strain on steep slopes. [2]
- **Diagnostic and specialist care gap:** rural Community Health Centres across Northeast India face substantial shortages of specialist doctors and radiographers, limiting access to specialist consultation and X-ray-based diagnosis. [3]

JointSense strengthens preliminary screening beyond questionnaires and visual observation, and creates an intermediate assessment layer between basic screening and specialist diagnosis.

## 💡 What Makes JointSense Different

- **Objective biomechanics + subjective symptoms:** combines sensor data with WOMAC / KOOS questionnaires. [4][12]
- **Joint vibroarthrography (VAG)** integrated with wearable gait and motion analysis.
- **Explainable, personalised risk assessment** (SHAP) instead of a black-box prediction.
- **Multilingual and completely offline:** easy-to-use interface for health workers.
- **Modular architecture:** can be extended to other joints with minimal changes.

| Existing solution and its shortcoming | JointSense advantage |
|---|---|
| Subjective questionnaires alone | Multimodal objective + symptom assessment |
| Manual examination | Quantitative sensor-assisted assessment |
| Imaging-dependent workflows | Portable preliminary screening |
| Opaque or disconnected AI tools | Explainable, integrated edge-AI risk assessment |

---

## 🧭 How a Screening Works

1. **User and clinical inputs:** choose language (multilingual, voice-guided), enter age, BMI, gender and medical history, then complete the WOMAC / KOOS questionnaire on the handheld/laptop HMI.
2. **Sensor setup (non-invasive, lightweight):** thigh IMU, shin IMU, piezoelectric VAG sensor on the patella, and an FSR insole (heel, mid, forefoot).
3. **Functional tests** (inspired by OARSI performance-based tests [5]):
   - 10 m walking test (2–3 rounds), gait analysis
   - Sit-to-stand test (5 repetitions), functional strength
   - Knee flexion-extension test (5 repetitions per leg), range of motion
4. **Edge processing (ESP32):** real-time acquisition (IMU, FSR, VAG), calibration, filtering and noise reduction, timestamping, and serial transmission to the Raspberry Pi.
5. **Processing (Raspberry Pi):** read sensor data, synchronise signals, window and segment, extract features, and fuse the modalities.
6. **AI analysis:** Random Forest classifier (scikit-learn) for risk classification, with SHAP for explainable risk factors.
7. **Risk report:** risk score, risk category and key contributing factors shown on the HMI, plus a downloadable PDF report.
8. **Data storage and sync (offline-first):** local encrypted SQLite storage, no internet needed for screening, and cloud sync (MongoDB) when a network is available.

The final score combines **40% patient-reported symptoms** and **60% movement data**.

---

## 🔩 Hardware Components

| Component | Role |
|---|---|
| BMI270 IMU (×2, thigh and shin) | Movement, joint angle and gait |
| CM01B piezoelectric contact microphone | Joint vibration / acoustic emission (VAG) |
| Analog front end for CM01B | Amplifier, low-pass filter, high-speed ADC |
| FSR-402 based insole | Plantar loading and weight asymmetry |
| ADS1115 (16-bit ADC) | Digitising FSR channels |
| ESP32 | Edge acquisition and preprocessing |
| Raspberry Pi 3B | Synchronisation, feature extraction, AI, reporting |

See [`hardware/BOM and specifications`](hardware/BOM%20and%20specifications) and [`hardware/pinout reference`](hardware/pinout%20reference) for details.

## 🧮 Software Stack

| Layer | Technologies |
|---|---|
| Core processing | Python, multiprocessing, threading, queues, events |
| AI / ML | scikit-learn (Random Forest), joblib, SHAP |
| Storage and visualisation | SQLite (on-device), MongoDB (cloud sync), Matplotlib |
| Reporting and communication | ReportLab / WeasyPrint PDF, REST API |
| HMI | Flask / FastAPI backend, React frontend, JSON |

## 📊 Key Features Extracted

The model works on movement, gait, plantar-loading, acoustic and clinical features. The exact production feature order is in [`backend/ml/feature_order.txt`](backend/ml/feature_order.txt). Highlights:

- **Range of motion:** maximum flexion angle, total ROM, peak angular velocity and acceleration, step time, cadence
- **Gait and loading:** stride length, gait symmetry, peak loading, loading rate, weight asymmetry, plantar pressure distribution
- **Joint sound (VAG):** dominant frequency, acoustic event count
- **Functional and clinical:** sit-to-stand time, pain score, stiffness score, age, BMI, gender

---

## 📁 Repository Structure

```text
JointSense/
├── backend/               # FastAPI server, ML model (Random Forest + SHAP), PDF reports, tests
├── frontend/              # React web / UI interface components
├── firmware/              # ESP32 firmware (dual BMI270 knee test)
├── hardware/              # BOM and specifications, pinout reference
├── docs/                  # Documentation and references
├── validation/            # Validation protocols and data
├── data/                  # Datasets
├── memory/                # PRD, persistent notes / system logs
├── test_reports/          # Generated assessment reports and test logs
├── tests/                 # Unit and integration test suites
├── auth_testing.md        # Authentication test documentation
├── design_guidelines.json # UI/UX design tokens and layout configs
└── README.md              # Project documentation
```

---

## ⚙️ Backend Setup & Configuration

The JointSense backend is built with Python (FastAPI). Follow the steps below to configure and launch the API server locally:

### 1. Prerequisites
- **Python 3.11+** installed on your system (the pinned NumPy / pandas versions need it)
- `pip` package manager
- A running **MongoDB** instance (local or hosted)

### 2. Navigate to Backend Directory
```bash
cd backend
```

### 3. Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-local.txt
```

### 4. Configure Environment
Create or edit `backend/.env` with your own values:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=jointsense
CORS_ORIGINS=*
JWT_SECRET=<long random string>
ADMIN_EMAIL=<clinician login email>
ADMIN_PASSWORD=<clinician password>
HW_INGEST_KEY=<shared key used by the ESP32 / Pi to post data>
```

> Use your own secrets. Never reuse demo values in a real deployment.

### 5. Run the API Server
```bash
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

The API is served under `/api`. On first start, a clinician account is created from `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

### Main API endpoints

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout` |
| Device and settings | `GET /api/device/status`, `GET/PUT /api/settings`, `POST /api/hw/ingest` |
| Patients | `GET/POST /api/patients`, `GET /api/patients/{patient_id}` |
| Assessment | `POST /api/assessment/start`, `GET /api/assessment/live`, `POST /api/assessment/stop`, `GET /api/assessment/results` |
| Results and reports | `GET /api/screenings/{screening_id}`, `GET /api/assessments/{screening_id}/pdf` |

The backend can run in **simulator** mode (no hardware needed) or **hardware** mode. In hardware mode the device posts features to `/api/hw/ingest`; if the stream goes stale, the API automatically falls back to the simulator and flags it.

## 🖥️ Frontend Setup

```bash
cd frontend
npm install        # or: yarn install
```

Create `frontend/.env`:
```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

```bash
npm start          # opens http://localhost:3000
```

The interface supports seven languages (English, हिन्दी, मराठी, বাংলা, தமிழ், తెలుగు, ಕನ್ನಡ), light and dark themes, and mobile-friendly layouts.

## 🔌 Firmware

[`firmware/main.ino`](firmware/main.ino) runs a **seated knee-extension test** on an ESP32 DevKit V1 using two BMI270 IMUs (thigh and shank) on separate I2C buses, with Madgwick fusion, gyro calibration, a neutral-pose self-check, and optional CSV output for a Python logger. Pin assignments are listed in the [pinout reference](hardware/pinout%20reference).

Firmware currently covers the dual-IMU knee angle test. The FSR insole and piezoelectric VAG channels from the full design are on the roadmap below.

## 🧪 Testing

```bash
cd backend
pytest
```

Backend tests cover authentication, SHAP output, PDF generation, hardware ingest and fallback, and input validation. Results from each iteration are stored in [`test_reports/`](test_reports/).

---

## 🌍 Feasibility, Impact and Scalability

- **Technical:** each sensing modality has a defined validation protocol; low, bounded power draw for full-day battery operation; fault-tolerant design that returns a partial, flagged result rather than failing silently.
- **Field:** short protocols for health camps, no advanced imaging or deep learning required, seated or standing assessments, minimal operator training, and durable enclosures and straps.
- **Scalability:** costs fall with volume, more regions add training data, deployment is limited by device availability rather than trained personnel, and structured data allows future integration with NPHCE and e-Sanjeevani-style systems.
- **Impact:** earlier risk detection, non-specialist screening where specialists are scarce, doorstep screening that reduces access barriers (women carry a higher OA burden [10]), and structured regional musculoskeletal data.
- **Alignment:** National Health Mission, National Health Portal, Ayushman Bharat Digital Mission; UN SDGs 3, 9 and 10.

| Challenge | Our solution |
|---|---|
| Signal noise and sensor reliability | IMU-gated audio analysis, sealed enclosures, periodic auto-calibration |
| Limited labelled clinical data | Semi-supervised learning on unlabeled data, then clinical validation with healthcare partners |
| Clinical trust and compliance | Clinical partnerships, ethics approval, regulatory compliance, secure health-data management |
| Accessibility and deployment | Seated/standing pathways needing minimal space and a stable chair |

## 🗺️ Status and Roadmap

- ✅ Web app with clinician accounts, patient records, seven languages, 40/60 scoring, real TreeSHAP explanations and branded PDF reports
- ✅ Simulator mode and hardware ingest API with automatic fallback
- ✅ Dual BMI270 knee-extension firmware
- 🔄 Connect the ESP32 / Raspberry Pi adapter to the live assessment contract with real serial packets
- 🔄 FSR insole and piezoelectric VAG acquisition in firmware
- 🔄 Clinical validation, and authorised translations of the official questionnaire wording
- 🔄 Fill in BOM, pinout, docs and validation content
- 🔜 Offline-first SQLite storage on the device with cloud sync, trend charts and CSV export

---

## 📚 References

1. "Musculoskeletal health and occupational hazards in Northeast Indian farmers: A cross-sectional analysis," *Work*, PMID 41697781, 2026. https://pubmed.ncbi.nlm.nih.gov/41697781/
2. C. R. Buragohain et al., "Prevalence of primary osteoarthritis of knee in tea garden community of Jorhat District, Assam," *IP Int. J. Orthop. Rheumatol.*, 9(1), 25–29, 2023. https://doi.org/10.18231/j.ijor.2023.004
3. Ministry of Health and Family Welfare, Government of India, *Rural Health Statistics 2021–22*, 2022.
4. E. M. Roos et al., "Knee Injury and Osteoarthritis Outcome Score (KOOS)," *J. Orthop. Sports Phys. Ther.*, 28(2), 88–96, 1998. https://doi.org/10.2519/jospt.1998.28.2.88
5. F. Dobson et al., "OARSI recommended performance-based tests to assess physical function in people diagnosed with hip or knee osteoarthritis," *Osteoarthritis Cartilage*, 21(8), 1042–1052, 2013. https://doi.org/10.1016/j.joca.2013.05.002
6. Measurement Specialties, Inc., "CM-01B Contact Microphone" datasheet, 2011.
7. Bosch Sensortec GmbH, "BMI270 — Ultra-Low Power IMU for Wearable Applications," datasheet BST-BMI270-DS000.
8. A. Machrowska et al., "Application of EEMD-DFA algorithms and ANN classification for detection of knee osteoarthritis using vibroarthrography," *Applied Computer Science*, 20(2), 90–108, 2024. https://doi.org/10.35784/acs-2024-18
9. N. Befrui et al., "Vibroarthrography for early detection of knee osteoarthritis using normalized frequency features," *Med. Biol. Eng. Comput.*, 56(8), 1499–1514, 2018. https://doi.org/10.1007/s11517-018-1785-4
10. World Health Organization, "Osteoarthritis," WHO Fact Sheet, 14 Jul 2023.
11. Interlink Electronics, "FSR 400 Series Force Sensing Resistor Data Sheet," 2010.
12. WOMAC® 3.1 Index, "Knee and Hip Osteoarthritis Index," WOMAC – AUSCAN – Osteoarthritis Global Index.

---

## 👥 Team

**Team Rocket** — Smart India Hackathon 2026 (SIH26004: AI-Assisted Early Detection System for Osteoarthritis Risk Markers in the North Eastern Region).

> ⚠️ JointSense is a screening aid and research prototype. It is not a diagnostic device and does not replace evaluation by a qualified clinician.
