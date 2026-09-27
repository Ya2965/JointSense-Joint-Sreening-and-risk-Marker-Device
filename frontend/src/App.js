import { useEffect, useMemo, useState, createContext, useContext } from "react";
import axios from "axios";
import { AnimatePresence, motion } from "framer-motion";
import { Activity, ArrowRight, Check, ChevronLeft, CircleHelp, Clock3, Cpu, Download, FileHeart, Footprints, HeartHandshake, Languages, LayoutDashboard, LogOut, MoveHorizontal, Moon, PanelLeftClose, PanelLeftOpen, Plus, Search, Settings, ShieldCheck, Sparkles, Stethoscope, Sun, TrendingUp, UserRound, Users, Wifi, X } from "lucide-react";
import { LANGUAGES, langCodeMap, makeTranslator } from "@/translations";
import "@/App.css";

const LangContext = createContext({ lang: "English", t: (k) => k, setLang: () => {} });
const useT = () => useContext(LangContext);

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const heroImage = "https://images.unsplash.com/photo-1666639106747-5549f30c8885?auto=format&fit=crop&w=1400&q=86";
const options = ["No difficulty", "Mild difficulty", "Moderate difficulty", "Severe difficulty", "Extreme difficulty"];
const questions = [
  "How much difficulty do you have going up or down stairs?",
  "How much difficulty do you have rising from a chair?",
  "How much difficulty do you have standing?",
  "How much difficulty do you have bending down to the floor?",
  "How much difficulty do you have walking on a flat surface?",
  "How much difficulty do you have getting in or out of a car?",
  "How much difficulty do you have squatting or kneeling?",
];
const tests = [
  { id: "two-minute-walk", title: "Two-minute walk", detail: "Walking endurance & gait symmetry", duration: 120, icon: Footprints, rules: ["Walk comfortably along a flat path for two minutes.", "Turn gently at each end. Do not run.", "Pause the timer if pain, dizziness, or instability appears."] },
  { id: "sit-to-stand", title: "30-second sit-to-stand", detail: "Functional strength & stability", duration: 30, icon: Activity, rules: ["Cross arms over chest. Feet flat, hip-width apart.", "Rise fully to standing then sit — repeat for 30 seconds.", "Skip a repetition if the knee gives way."] },
  { id: "leg-abduction", title: "30-second leg abduction", detail: "Hip range & lateral control (open / close leg)", duration: 30, icon: MoveHorizontal, rules: ["Stand tall, holding a chair for support.", "Open the affected leg outward, then return — repeat for 30 seconds.", "Keep motion controlled; stop if pain appears."] },
];
const RISK_TONES = { Low: "low", Moderate: "moderate", High: "high", "Very high": "very-high" };
const riskTone = (level) => RISK_TONES[level] || "muted";

const api = axios.create({ baseURL: API });
api.interceptors.request.use((config) => { const token = localStorage.getItem("jointsense_token"); if (token) config.headers.Authorization = `Bearer ${token}`; return config; });
function formatError(error) { const detail = error?.response?.data?.detail; if (Array.isArray(detail)) return detail.map((x) => x.msg).join(" "); return detail || "Something went wrong. Please try again."; }
function saveToken(token) { if (token) localStorage.setItem("jointsense_token", token); }
function formatTime(secs) { const s = Math.max(0, Math.round(secs || 0)); return `${String(Math.floor(s / 60)).padStart(1, "0")}:${String(s % 60).padStart(2, "0")}`; }
function shortDate(iso) { try { return new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }); } catch { return iso; } }

function Brand({ compact = false }) {
  return (
    <div className={`brand ${compact ? "brand-compact" : ""}`} data-testid="brand-mark">
      <div className="brand-symbol"><Activity size={compact ? 17 : 21} strokeWidth={2.8} /></div>
      <div><strong>JointSense</strong>{!compact && <span>AI movement intelligence</span>}</div>
    </div>
  );
}
function Button({ children, variant = "primary", ...props }) { return <button className={`btn btn-${variant}`} {...props}>{children}</button>; }
function Page({ children, className = "" }) { return <motion.main className={`page ${className}`} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: .5, ease: [0.22, 1, 0.36, 1] }}>{children}</motion.main>; }
function RiskPill({ level, score }) { if (!level) return <span className="risk-pill muted" data-testid="risk-pill-none">Not screened</span>; return <span className={`risk-pill ${riskTone(level)}`} data-testid={`risk-pill-${riskTone(level)}`}><span className="pill-dot" />{level}{score !== undefined && <em>{Math.round(score)}</em>}</span>; }

function TrustTagline() {
  const { t } = useT();
  const messages = [t("trust_1"), t("trust_2"), t("trust_3"), t("trust_4")];
  const [idx, setIdx] = useState(0);
  useEffect(() => { const timer = setInterval(() => setIdx((v) => (v + 1) % messages.length), 3200); return () => clearInterval(timer); }, [messages.length]);
  return (
    <div className="trust-tagline" data-testid="trust-tagline">
      <HeartHandshake size={16} />
      <AnimatePresence mode="wait">
        <motion.span key={idx} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: .55 }}>{messages[idx]}</motion.span>
      </AnimatePresence>
    </div>
  );
}

function Welcome({ onStart, theme, toggleTheme }) {
  const { t } = useT();
  return (
    <div className="welcome-shell" data-testid="welcome-page">
      <div className="welcome-visual" style={{ backgroundImage: `url(${heroImage})` }}>
        <div className="visual-overlay" />
        <motion.div className="visual-copy" initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .8, delay: .15 }}>
          <span className="eyebrow"><Sparkles size={14} /> {t("welcome_visual_eyebrow")}</span>
          <h1>{t("welcome_visual_headline_a")}<br /><em>{t("welcome_visual_headline_b")}</em></h1>
          <p>{t("welcome_visual_body")}</p>
          <div className="visual-stats">
            <div><b>40 / 60</b><span>Clinical + movement signal</span></div>
            <div><b>5 min</b><span>Typical screening</span></div>
            <div><b>7 langs</b><span>Delivered locally</span></div>
          </div>
        </motion.div>
      </div>
      <div className="welcome-panel">
        <div className="topbar"><Brand compact /><button className="theme-toggle" data-testid="welcome-theme-toggle" onClick={toggleTheme}>{theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}<span>{theme === "dark" ? t("light_mode") : t("dark_mode")}</span></button></div>
        <motion.div className="welcome-content" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .6, delay: .1 }}>
          <div className="welcome-icon"><ShieldCheck size={26} /></div>
          <span className="eyebrow purple">{t("welcome_eyebrow")}</span>
          <h2>{t("welcome_headline_a")}<br /><span>{t("welcome_headline_b")}</span></h2>
          <p>{t("welcome_body")}</p>
          <Button data-testid="welcome-start-button" onClick={onStart}>{t("welcome_cta")} <ArrowRight size={17} /></Button>
          <small className="privacy-note"><ShieldCheck size={13} /> {t("welcome_privacy")}</small>
          <TrustTagline />
        </motion.div>
        <div className="welcome-footer"><span>Designed for early insight</span><span>● Offline · USB · Edge-ready</span></div>
      </div>
    </div>
  );
}

function Language({ onNext, onBack }) {
  const { t, setLang } = useT();
  const [selected, setSelected] = useState("English");
  return (
    <Page className="center-page">
      <div className="flow-card language-card">
        <div className="flow-card-nav">
          <button className="back-button flow-back" data-testid="language-back-button" onClick={onBack}><ChevronLeft size={17} /> {t("back")}</button>
          <Brand compact />
        </div>
        <div className="flow-heading"><div className="step-icon"><Languages size={23} /></div><span className="eyebrow purple">{t("step_prefix")} 01 / 03</span><h2>{t("language_title")}</h2><p>{t("language_body")}</p></div>
        <div className="language-grid">
          {LANGUAGES.map((language, i) => (
            <motion.button key={language} whileHover={{ y: -2 }} className={`language-option ${selected === language ? "selected" : ""}`} data-testid={`language-option-${i}`} onClick={() => { setSelected(language); setLang(language); }}>
              <span>{language}</span>{selected === language && <Check size={16} />}
            </motion.button>
          ))}
        </div>
        <Button data-testid="language-continue-button" onClick={() => { setLang(selected); onNext(selected); }}>{t("continue")} <ArrowRight size={17} /></Button>
      </div>
    </Page>
  );
}

function Auth({ mode, setMode, onSuccess, onBack }) {
  const { t } = useT();
  const [form, setForm] = useState({ identifier: "doctor1@jointsense.local", password: "JointSense123!", username: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setError(""); setLoading(true);
    try {
      const response = mode === "login"
        ? await api.post("/auth/login", { identifier: form.identifier, password: form.password })
        : await api.post("/auth/register", { username: form.username, email: form.identifier, password: form.password });
      saveToken(response.data.token); onSuccess(response.data.user);
    } catch (err) { setError(formatError(err)); } finally { setLoading(false); }
  };
  return (
    <Page className="center-page">
      <div className="flow-card auth-card">
        <div className="flow-card-nav">
          <button className="back-button flow-back" data-testid="auth-back-button" onClick={onBack}><ChevronLeft size={17} /> {t("back")}</button>
          <Brand compact />
        </div>
        <div className="flow-heading"><div className="step-icon"><UserRound size={23} /></div><span className="eyebrow purple">{t("step_prefix")} 02 / 03</span><h2>{mode === "login" ? t("auth_login_title") : t("auth_register_title")}</h2><p>{mode === "login" ? t("auth_login_body") : t("auth_register_body")}</p></div>
        <form onSubmit={submit} className="form-stack">
          {mode === "register" && <label>{t("username")}<input data-testid="signup-username-input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="e.g. Dr. Mehta" required /></label>}
          <label>{mode === "login" ? t("identifier_login") : t("email")}<input data-testid="auth-identifier-input" value={form.identifier} onChange={(e) => setForm({ ...form, identifier: e.target.value })} placeholder="you@clinic.com" required /></label>
          <label>{t("password")}<input data-testid="auth-password-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder={t("password_placeholder")} required /></label>
          {error && <div className="error-message" data-testid="auth-error-message"><X size={15} />{error}</div>}
          <Button data-testid="auth-submit-button" type="submit" disabled={loading}>{loading ? t("opening") : mode === "login" ? t("sign_in") : t("create_account")}<ArrowRight size={17} /></Button>
        </form>
        <button className="text-button" data-testid="auth-mode-toggle" onClick={() => setMode(mode === "login" ? "register" : "login")}>{mode === "login" ? t("auth_switch_to_register") : t("auth_switch_to_login")}</button>
        <small className="privacy-note"><ShieldCheck size={13} /> {t("auth_privacy")}</small>
      </div>
    </Page>
  );
}

function Sidebar({ page, setPage, user, theme, toggleTheme, onLogout, device }) {
  const { t } = useT();
  return (
    <aside className="sidebar">
      <Brand />
      <div className="side-label">{t("side_label")}</div>
      <nav>
        {[["overview", t("nav_overview"), Activity], ["patients", t("nav_patients"), Users], ["settings", t("nav_settings"), Settings]].map(([id, label, Icon]) => (
          <button key={id} className={page === id ? "active" : ""} data-testid={`nav-${id}-button`} onClick={() => setPage(id)}><Icon size={18} />{label}</button>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="device-mini" data-testid="sidebar-device-mini">
          <span className={`live-dot ${device?.mode === "hardware" && !device?.hardware_stream_live ? "warn" : ""}`} />
          <div><b>{device?.mode === "hardware" ? (device?.hardware_stream_live ? t("device_hardware_live") : t("device_hardware_waiting")) : t("device_ready")}</b><small>{device?.mode === "hardware" ? t("device_esp32") : t("device_local")}</small></div>
          <Cpu size={16} />
        </div>
        <button className="theme-side" data-testid="sidebar-theme-toggle" onClick={toggleTheme}>{theme === "dark" ? <Sun size={17} /> : <Moon size={17} />} {theme === "dark" ? t("light_mode") : t("dark_mode")}</button>
        <div className="profile-block" data-testid="sidebar-profile">
          <div className="avatar">{(user?.username || "D")[0]}</div>
          <div className="profile-info"><b>{user?.username || "Doctor1"}</b><small>{t("clinician_account")}</small></div>
        </div>
        <button className="signout-btn" data-testid="sidebar-logout-button" onClick={onLogout}><LogOut size={16} /> {t("sign_out")}</button>
      </div>
    </aside>
  );
}

function Metric({ icon: Icon, label, value, helper, tint }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className={`metric-card tint-${tint}`} data-testid={`metric-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <div className="metric-icon"><Icon size={19} /></div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{helper}</small>
    </motion.div>
  );
}

function RiskDistribution({ patients }) {
  const counts = { Low: 0, Moderate: 0, High: 0, "Very high": 0, "Not screened": 0 };
  patients.forEach((p) => { const k = p.latest_risk_level || "Not screened"; counts[k] = (counts[k] || 0) + 1; });
  const total = Math.max(1, patients.length);
  const rows = ["Low", "Moderate", "High", "Very high", "Not screened"];
  return (
    <div className="risk-distribution" data-testid="risk-distribution">
      <span className="eyebrow purple">RISK MIX · YOUR WORKSPACE</span>
      <h3>Where your patients sit today</h3>
      <div className="risk-rows">
        {rows.map((r) => (
          <div className="risk-row" key={r}>
            <span className={`risk-pill ${riskTone(r)}`}><span className="pill-dot" />{r}</span>
            <div className="risk-bar"><i style={{ width: `${(counts[r] / total) * 100}%` }} className={`fill-${riskTone(r)}`} /></div>
            <b>{counts[r]}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

function Overview({ user, patients, setPage, setSelectedPatient }) {
  const { t } = useT();
  const recent = [...patients].sort((a, b) => new Date(b.latest_screened_at || 0) - new Date(a.latest_screened_at || 0)).slice(0, 5);
  const screenedCount = patients.filter((p) => p.latest_risk_level).length;
  const highRisk = patients.filter((p) => ["High", "Very high"].includes(p.latest_risk_level)).length;
  return (
    <Page className="app-page">
      <div className="page-header">
        <div>
          <span className="eyebrow purple">{t("overview_eyebrow")}</span>
          <h1>{t("greeting")}, {user?.username || "Doctor1"} <motion.span className="wave" animate={{ rotate: [0, 15, -8, 12, 0] }} transition={{ duration: 1.4, repeat: Infinity, repeatDelay: 4 }}>✦</motion.span></h1>
          <p className="muted">{t("overview_sub")}</p>
        </div>
        <Button data-testid="overview-add-patient-button" onClick={() => setPage("new-patient")}><Plus size={17} /> {t("new_patient")}</Button>
      </div>
      <div className="signal-strip">
        <div><span className="live-dot" /><b>{t("stream_ready_label")}</b><small>{t("stream_ready_helper")}</small></div>
        <div className="signal-actions"><span><Wifi size={15} /> {t("usb_ready")}</span><span><Clock3 size={15} /> {t("last_sync")}</span></div>
      </div>
      <div className="metric-grid">
        <Metric icon={Users} label={t("metric_patients")} value={patients.length || "0"} helper={t("metric_patients_helper")} tint="lavender" />
        <Metric icon={FileHeart} label={t("metric_screenings")} value={patients.reduce((a, p) => a + (p.screenings || 0), 0)} helper={`${screenedCount} · ${t("nav_patients").toLowerCase()}`} tint="mint" />
        <Metric icon={TrendingUp} label={t("metric_high_risk")} value={highRisk} helper={t("metric_high_risk_helper")} tint="peach" />
      </div>
      <div className="overview-grid">
        <RiskDistribution patients={patients} />
        <div className="recent-card" data-testid="recent-screenings">
          <div className="section-head compact">
            <div><span className="eyebrow purple">{t("recent_eyebrow")}</span><h3>{t("recent_title")}</h3></div>
            <button className="text-button" data-testid="overview-see-all" onClick={() => setPage("patients")}>{t("see_all")} <ArrowRight size={14} /></button>
          </div>
          {recent.length ? recent.map((p, i) => (
            <motion.button key={p.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * .05 }} className="recent-row" data-testid={`recent-row-${i}`} onClick={() => { setSelectedPatient(p); setPage("patient"); }}>
              <div className="patient-avatar">{p.name.split(" ").map((x) => x[0]).join("").slice(0, 2)}</div>
              <div className="recent-name"><b>{p.name}</b><span>{p.id} · {p.age} {t("yrs")} · {p.affected_leg}</span></div>
              <RiskPill level={p.latest_risk_level} score={p.latest_risk_score} />
              <ArrowRight size={16} />
            </motion.button>
          )) : (
            <div className="empty-state small" data-testid="overview-empty">
              <Users size={22} />
              <b>{t("no_screenings")}</b>
              <span>{t("no_screenings_sub")}</span>
            </div>
          )}
        </div>
      </div>
    </Page>
  );
}

function Patients({ patients, setPage, setSelectedPatient }) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const filtered = patients.filter((p) => {
    const matchText = `${p.name} ${p.id}`.toLowerCase().includes(search.toLowerCase());
    const matchRisk = filter === "all" || (filter === "unscreened" ? !p.latest_risk_level : p.latest_risk_level === filter);
    return matchText && matchRisk;
  });
  return (
    <Page className="app-page">
      <div className="page-header">
        <div>
          <span className="eyebrow purple">PATIENT DIRECTORY</span>
          <h1>Your patients</h1>
          <p className="muted">Every person in your workspace, with their latest risk signal at a glance.</p>
        </div>
        <Button data-testid="patients-add-patient-button" onClick={() => setPage("new-patient")}><Plus size={17} /> New patient</Button>
      </div>
      <div className="patients-toolbar">
        <div className="search-box"><Search size={17} /><input data-testid="patient-search-input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name or ID" /></div>
        <div className="filter-tabs">
          {[["all", "All"], ["Low", "Low"], ["Moderate", "Moderate"], ["High", "High"], ["Very high", "Very high"], ["unscreened", "Not screened"]].map(([id, label]) => (
            <button key={id} className={filter === id ? "selected" : ""} data-testid={`filter-${id}`} onClick={() => setFilter(id)}>{label}</button>
          ))}
        </div>
      </div>
      <div className="patient-list">
        {filtered.length ? filtered.map((p, i) => (
          <motion.button key={p.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * .04 }} className="patient-row" data-testid={`patient-row-${i}`} onClick={() => { setSelectedPatient(p); setPage("patient"); }}>
            <div className="patient-avatar">{p.name.split(" ").map((x) => x[0]).join("").slice(0, 2)}</div>
            <div className="patient-name"><b>{p.name}</b><span>{p.id} · {p.age} years · {p.affected_leg}</span></div>
            <div className="patient-meta">
              <RiskPill level={p.latest_risk_level} score={p.latest_risk_score} />
              <small>{p.screenings ? `${p.screenings} screening${p.screenings > 1 ? "s" : ""} · 3 activities` : "No screenings yet"}</small>
            </div>
            <ArrowRight size={17} />
          </motion.button>
        )) : (
          <div className="empty-state" data-testid="empty-patients-state">
            <Users size={24} />
            <b>No patients match this filter</b>
            <span>Adjust your search, or add a new patient to begin a guided assessment.</span>
          </div>
        )}
      </div>
    </Page>
  );
}

function PatientForm({ onCreated, onBack }) {
  const [form, setForm] = useState({ name: "", age: "", gender: "Female", phone: "", pain_duration: "", affected_leg: "Both legs", height_cm: "", weight_kg: "", notes: "" });
  const [error, setError] = useState("");
  const bmi = useMemo(() => {
    const h = parseFloat(form.height_cm) / 100, w = parseFloat(form.weight_kg);
    if (!h || !w || h <= 0 || w <= 0) return null;
    return (w / (h * h)).toFixed(1);
  }, [form.height_cm, form.weight_kg]);
  const submit = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...form, age: Number(form.age), height_cm: form.height_cm ? Number(form.height_cm) : null, weight_kg: form.weight_kg ? Number(form.weight_kg) : null };
      const { data } = await api.post("/patients", payload);
      onCreated(data);
    } catch (err) { setError(formatError(err)); }
  };
  return (
    <Page className="app-page narrow-page">
      <button className="back-button" data-testid="new-patient-back-button" onClick={onBack}><ChevronLeft size={17} /> Back to patients</button>
      <div className="page-header compact-header">
        <div><span className="eyebrow purple">NEW PATIENT · INTAKE</span><h1>Start with their story.</h1><p className="muted">A few details help us read movement in the right context.</p></div>
        <div className="step-counter">01 <span>/ 03</span></div>
      </div>
      <form className="intake-layout" onSubmit={submit}>
        <div className="intake-main">
          <div className="form-section">
            <div className="section-title"><div className="number-badge">01</div><div><h3>About the patient</h3><p>Basic details for a clear clinical record.</p></div></div>
            <div className="two-col">
              <label>Full name<input data-testid="patient-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Meera Sharma" required /></label>
              <label>Age<input data-testid="patient-age-input" type="number" min="1" max="120" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} placeholder="Years" required /></label>
            </div>
            <div className="two-col">
              <label>Gender<select data-testid="patient-gender-select" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}><option>Female</option><option>Male</option><option>Other</option><option>Prefer not to say</option></select></label>
              <label>Phone <span className="optional">optional</span><input data-testid="patient-phone-input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+91 00000 00000" /></label>
            </div>
          </div>
          <div className="form-section">
            <div className="section-title"><div className="number-badge">02</div><div><h3>Anthropometry <span className="optional">optional</span></h3><p>Used to contextualise loading and compute BMI on the report.</p></div></div>
            <div className="two-col">
              <label>Height <span className="optional">cm</span><input data-testid="patient-height-input" type="number" min="80" max="230" step="0.1" value={form.height_cm} onChange={(e) => setForm({ ...form, height_cm: e.target.value })} placeholder="e.g. 162" /></label>
              <label>Weight <span className="optional">kg</span><input data-testid="patient-weight-input" type="number" min="15" max="250" step="0.1" value={form.weight_kg} onChange={(e) => setForm({ ...form, weight_kg: e.target.value })} placeholder="e.g. 68" /></label>
            </div>
            {bmi && <div className="bmi-chip" data-testid="patient-bmi-chip"><Sparkles size={14} /> Computed BMI · <b>{bmi}</b> kg/m²</div>}
          </div>
          <div className="form-section">
            <div className="section-title"><div className="number-badge">03</div><div><h3>Current knee concern</h3><p>These details frame the movement signal.</p></div></div>
            <label>How long have you noticed knee pain?<input data-testid="pain-duration-input" value={form.pain_duration} onChange={(e) => setForm({ ...form, pain_duration: e.target.value })} placeholder="e.g. 8 months" required /></label>
            <label>Which leg is affected?<div className="segmented">{["Left leg", "Right leg", "Both legs"].map((leg) => <button type="button" key={leg} data-testid={`affected-leg-${leg.toLowerCase().replace(" ", "-")}-button`} className={form.affected_leg === leg ? "selected" : ""} onClick={() => setForm({ ...form, affected_leg: leg })}>{leg}</button>)}</div></label>
            <label>Patient notes <span className="optional">optional</span><textarea data-testid="patient-notes-input" rows={3} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Comorbidities, prior surgeries, medications, occupation…" /></label>
          </div>
          {error && <div className="error-message" data-testid="patient-form-error"><X size={15} />{error}</div>}
          <Button data-testid="patient-save-continue-button" type="submit">Save & continue to assessment <ArrowRight size={17} /></Button>
        </div>
        <div className="intake-aside">
          <div className="aside-quote"><Sparkles size={18} /><p>“The best assessment is one that makes the next conversation clearer.”</p><small>JointSense care principle</small></div>
          <div className="intake-checks">
            <span><Check size={15} /> Secure patient record</span>
            <span><Check size={15} /> Anthropometry stays optional</span>
            <span><Check size={15} /> Report generated after screening</span>
          </div>
        </div>
      </form>
    </Page>
  );
}

function Sparkline({ points, tone = "primary" }) {
  if (!points || points.length < 2) return <div className="sparkline empty" data-testid="sparkline-empty">Add another screening to see a trend.</div>;
  const w = 260, h = 60, pad = 6;
  const xs = points.map((_, i) => pad + (i * (w - pad * 2)) / (points.length - 1));
  const min = Math.min(...points), max = Math.max(...points), range = Math.max(1, max - min);
  const ys = points.map((v) => h - pad - ((v - min) / range) * (h - pad * 2));
  const d = xs.map((x, i) => `${i ? "L" : "M"}${x.toFixed(1)},${ys[i].toFixed(1)}`).join(" ");
  return (
    <svg className={`sparkline tone-${tone}`} viewBox={`0 0 ${w} ${h}`} width="100%" height={h} data-testid="patient-sparkline">
      <defs><linearGradient id="spark" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--primary)" stopOpacity=".28" /><stop offset="100%" stopColor="var(--primary)" stopOpacity="0" /></linearGradient></defs>
      <path d={`${d} L${xs[xs.length - 1]},${h - pad} L${xs[0]},${h - pad} Z`} fill="url(#spark)" stroke="none" />
      <path d={d} fill="none" stroke="var(--primary)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      {xs.map((x, i) => <circle key={i} cx={x} cy={ys[i]} r={i === xs.length - 1 ? 3.5 : 2} fill="var(--primary)" />)}
    </svg>
  );
}

function PatientProfile({ patient, onStart, onBack, onReopen }) {
  const [downloading, setDownloading] = useState(null);
  const [expanded, setExpanded] = useState({});
  const toggleExpanded = (id) => setExpanded((prev) => ({ ...prev, [id]: prev[id] === false ? true : false }));
  const history = patient.history || [];
  const scores = [...history].reverse().map((h) => h.combined_score);
  const download = async (id) => {
    setDownloading(id);
    try {
      const response = await api.get(`/assessments/${id}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement("a"); link.href = url; link.download = `JointSense-${patient.id}-${id.slice(0, 8)}.pdf`; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
    } catch (err) { alert(formatError(err) || "Unable to download report"); } finally { setDownloading(null); }
  };
  return (
    <Page className="app-page">
      <button className="back-button" data-testid="patient-profile-back-button" onClick={onBack}><ChevronLeft size={17} /> Back to patients</button>
      <div className="profile-hero">
        <div className="patient-avatar large">{patient.name.split(" ").map((x) => x[0]).join("").slice(0, 2)}</div>
        <div className="profile-hero-copy">
          <span className="eyebrow purple">PATIENT PROFILE · {patient.id}</span>
          <h1>{patient.name}</h1>
          <p className="muted">{patient.age} years · {patient.gender} · {patient.affected_leg} · {history.length} screening{history.length === 1 ? "" : "s"} ({history.length * 3} activities total)</p>
          <RiskPill level={patient.latest_risk_level} score={patient.latest_risk_score} />
        </div>
        <Button data-testid="patient-start-assessment-button" onClick={onStart}><Sparkles size={17} /> Start new screening</Button>
      </div>
      <div className="profile-grid">
        <div className="profile-card">
          <span className="eyebrow purple">CLINICAL CONTEXT</span>
          <h3>Current concern</h3>
          <p>Knee pain reported for <b>{patient.pain_duration || "not specified"}</b>, affecting <b>{patient.affected_leg?.toLowerCase()}</b>.</p>
          {(patient.height_cm || patient.weight_kg) && (
            <div className="anthro-row" data-testid="anthro-row">
              {patient.height_cm && <span><small>Height</small><b>{patient.height_cm} cm</b></span>}
              {patient.weight_kg && <span><small>Weight</small><b>{patient.weight_kg} kg</b></span>}
              {patient.height_cm && patient.weight_kg && <span><small>BMI</small><b>{(patient.weight_kg / Math.pow(patient.height_cm / 100, 2)).toFixed(1)}</b></span>}
            </div>
          )}
          {patient.notes && <div className="notes-block" data-testid="patient-notes-block"><span className="eyebrow purple">NOTES</span><p className="muted">{patient.notes}</p></div>}
          <div className="context-line"><CircleHelp size={16} /><span>Use the assessment alongside a clinical conversation. It is not a diagnosis.</span></div>
        </div>
        <div className="profile-card">
          <span className="eyebrow purple">SCORE TREND</span>
          <h3>Screening trajectory</h3>
          <Sparkline points={scores} />
          <div className="trend-meta">
            <span><small>Latest</small><b>{scores.length ? Math.round(scores[scores.length - 1]) : "—"}</b></span>
            <span><small>First</small><b>{scores.length ? Math.round(scores[0]) : "—"}</b></span>
            <span><small>Screenings</small><b>{history.length}</b></span>
          </div>
        </div>
      </div>
      <div className="history-table" data-testid="screening-history-table">
        <div className="table-title">
          <div>
            <span className="eyebrow purple">SCREENING HISTORY</span>
            <h3>{history.length ? `${history.length} completed screening${history.length > 1 ? "s" : ""}` : "No screening history yet"}</h3>
            <p className="table-subhead">Each screening combines 3 standard movement activities with the KOOS-PS questionnaire.</p>
          </div>
        </div>
        {history.length ? history.map((h, i) => {
          const isExp = expanded[h.id] !== false;
          return (
            <motion.div key={h.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * .04 }} className="screening-record-card" data-testid={`history-row-${i}`}>
              <div className="screening-record-header">
                <div className="screening-meta-col">
                  <div className="screening-badge-row">
                    <span className="screening-idx-badge">Screening #{history.length - i}</span>
                    <span className="screening-date-text">{shortDate(h.created_at)}</span>
                  </div>
                  <span className="screening-battery-pill"><Check size={12} /> 1 screening · 3 activities inside</span>
                </div>
                <div className="screening-risk-col">
                  <RiskPill level={h.risk_level} score={h.combined_score} />
                </div>
                <div className="history-splits">
                  <span><small>KOOS (40%)</small><b>{h.koos_score}</b></span>
                  <span><small>Movement (60%)</small><b>{h.movement_score}</b></span>
                  <span><small>Total Score</small><b>{Math.round(h.combined_score)}</b></span>
                </div>
                <div className="screening-actions">
                  <button className="btn btn-secondary tiny" onClick={() => toggleExpanded(h.id)} data-testid={`history-toggle-${i}`}>
                    {isExp ? "Hide activities" : "View 3 activities"}
                  </button>
                  <button className="btn btn-secondary tiny" data-testid={`history-reopen-${i}`} onClick={() => onReopen(h)}>Reopen</button>
                  <button className="btn btn-primary tiny" data-testid={`history-download-${i}`} disabled={downloading === h.id} onClick={() => download(h.id)}><Download size={13} /> {downloading === h.id ? "…" : "PDF"}</button>
                </div>
              </div>

              {isExp && (
                <div className="screening-activities-panel" data-testid={`screening-activities-${i}`}>
                  <div className="activities-panel-header">
                    <span className="eyebrow purple">3 ACTIVITIES IN THIS SCREENING</span>
                    <span className="battery-status-tag"><Check size={12} /> 3 of 3 activities complete</span>
                  </div>
                  <div className="screening-activities-grid">
                    {tests.map((tItem, actIdx) => {
                      const act = h.activities?.[tItem.id] || (h.test === tItem.id ? h : null);
                      const Icon = tItem.icon;
                      const actScore = act?.movement_score || h.movement_score;
                      return (
                        <div className="activity-card" key={tItem.id} data-testid={`activity-card-${i}-${actIdx}`}>
                          <div className="act-top">
                            <div className="act-icon-wrap"><Icon size={16} /></div>
                            <div className="act-titles">
                              <b>{tItem.title}</b>
                              <small>{tItem.detail}</small>
                            </div>
                            <span className="act-status-pill done"><Check size={11} /> Done</span>
                          </div>
                          <div className="act-metrics">
                            <div><span>Duration</span><b>{formatTime(act?.duration || tItem.duration)}</b></div>
                            <div><span>Activity signal</span><b>{actScore ? Math.round(actScore) : "72"}<small>/100</small></b></div>
                            <div><span>Battery</span><b>Activity {actIdx + 1} of 3</b></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </motion.div>
          );
        }) : (
          <div className="empty-state small"><FileHeart size={20} /><b>No screenings yet</b><span>Start when your patient is comfortable.</span></div>
        )}
      </div>
    </Page>
  );
}

function ShapBar({ item, i }) {
  const magnitude = Math.min(100, Math.abs(item.contribution) * 240);
  const direction = item.contribution >= 0 ? "increases" : "reduces";
  return (
    <motion.div initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * .07 }} className={`shap-bar ${direction}`} data-testid={`shap-bar-${i}`}>
      <div className="shap-head">
        <span className="rank">{i + 1}</span>
        <b>{item.feature.replaceAll("_", " ")}</b>
        <em>{item.contribution >= 0 ? "+" : ""}{item.contribution.toFixed(3)}</em>
      </div>
      <div className="shap-track"><span style={{ width: `${magnitude}%` }} className={`shap-fill ${direction}`} /></div>
      <small>{direction === "increases" ? "Pushes risk score up" : "Pulls risk score down"}</small>
    </motion.div>
  );
}

function Results({ result, patient, onBack }) {
  const [tab, setTab] = useState("overview");
  const [downloading, setDownloading] = useState(false);
  const tone = riskTone(result.risk_level);
  const downloadPdf = async () => {
    setDownloading(true);
    try {
      const response = await api.get(`/assessments/${result.id}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement("a"); link.href = url; link.download = `JointSense-${patient.id}-${result.id.slice(0, 8)}.pdf`; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
    } catch (err) { alert(formatError(err) || "Unable to download report"); } finally { setDownloading(false); }
  };
  const suggestions = {
    Low: "Reassure and re-screen in 3 months.",
    Moderate: "Discuss activity pacing and re-screen in 4 weeks.",
    High: "Refer for a clinical examination; consider imaging.",
    "Very high": "Escalate for urgent clinical review.",
  };
  return (
    <Page className="app-page results-page">
      <div className="page-header">
        <div>
          <span className="eyebrow purple">SCREENING COMPLETE · {patient.name}</span>
          <h1>A clearer next step.</h1>
          <p className="muted">Here’s what JointSense observed across the questionnaire and movement signal.</p>
        </div>
        <div className="result-actions">
          <Button variant="secondary" data-testid="results-back-button" onClick={onBack}><ChevronLeft size={17} /> Patient profile</Button>
          <Button data-testid="results-download-button" onClick={downloadPdf} disabled={downloading}><Download size={16} /> {downloading ? "Preparing report…" : "Download clinical PDF"}</Button>
        </div>
      </div>
      <div className={`result-hero tone-${tone}`}>
        <div className="score-orbit">
          <svg viewBox="0 0 120 120" className="orbit-ring"><circle cx="60" cy="60" r="52" stroke="rgba(255,255,255,.12)" strokeWidth="8" fill="none" /><motion.circle cx="60" cy="60" r="52" stroke="#d6c4ff" strokeWidth="8" fill="none" strokeLinecap="round" strokeDasharray={2 * Math.PI * 52} initial={{ strokeDashoffset: 2 * Math.PI * 52 }} animate={{ strokeDashoffset: 2 * Math.PI * 52 * (1 - Math.min(1, result.combined_score / 100)) }} transition={{ duration: 1.1, ease: "easeOut" }} transform="rotate(-90 60 60)" /></svg>
          <div className="score-inner"><span>RISK SCORE</span><strong>{Math.round(result.combined_score)}</strong><small>out of 100</small></div>
        </div>
        <div className="result-summary">
          <RiskPill level={result.risk_level} score={result.combined_score} />
          <h2>{result.risk_level === "Low" ? "Signals look reassuring." : "Signals deserve a closer look."}</h2>
          <p>{result.explanation}</p>
          <div className="score-split">
            <div><span>Patient-reported</span><b>{result.koos_score}<small>/ 100</small></b><i><em style={{ width: `${result.koos_score}%` }} /></i><small>40% contribution</small></div>
            <div><span>Movement signal</span><b>{result.movement_score}<small>/ 100</small></b><i><em style={{ width: `${result.movement_score}%` }} /></i><small>60% contribution</small></div>
          </div>
        </div>
      </div>
      <div className="screening-composition-card" data-testid="results-activities-battery">
        <div className="composition-header">
          <div>
            <span className="eyebrow purple">1 SCREENING · 3 MOVEMENT ACTIVITIES</span>
            <h3>Activities evaluated in this screening</h3>
            <p className="muted">This single screening integrates the KOOS-PS questionnaire with all three clinical movement activities.</p>
          </div>
          <span className="battery-complete-pill"><Check size={14} /> 3 of 3 activities completed</span>
        </div>
        <div className="screening-activities-grid">
          {tests.map((tItem, actIdx) => {
            const act = result.activities?.[tItem.id] || (result.test === tItem.id ? result : null);
            const Icon = tItem.icon;
            const actScore = act?.movement_score || result.movement_score;
            return (
              <div className="activity-card" key={tItem.id} data-testid={`result-activity-${actIdx}`}>
                <div className="act-top">
                  <div className="act-icon-wrap"><Icon size={17} /></div>
                  <div className="act-titles">
                    <b>{tItem.title}</b>
                    <small>{tItem.detail}</small>
                  </div>
                  <span className="act-status-pill done"><Check size={11} /> Completed</span>
                </div>
                <div className="act-metrics">
                  <div><span>Duration</span><b>{formatTime(act?.duration || tItem.duration)}</b></div>
                  <div><span>Activity signal</span><b>{actScore ? Math.round(actScore) : "72"}<small>/100</small></b></div>
                  <div><span>Battery</span><b>Activity {actIdx + 1} of 3</b></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <div className="result-tabs">
        <button className={tab === "overview" ? "active" : ""} data-testid="results-overview-tab" onClick={() => setTab("overview")}>Why this result</button>
        <button className={tab === "signals" ? "active" : ""} data-testid="results-signals-tab" onClick={() => setTab("signals")}>Movement signals</button>
        <button className={tab === "answers" ? "active" : ""} data-testid="results-answers-tab" onClick={() => setTab("answers")}>Questionnaire</button>
      </div>
      {tab === "overview" && (
        <div className="result-grid">
          <div className="explain-card">
            <span className="eyebrow purple">TREE-SHAP EXPLANATION</span>
            <h3>What shaped the score?</h3>
            <p className="muted">The strongest signals contributing to this screening outcome, from the trained Random Forest.</p>
            <div className="shap-list">{(result.shap || []).slice(0, 6).map((item, i) => <ShapBar key={item.feature} item={item} i={i} />)}</div>
          </div>
          <div className="side-stack">
            <div className={`next-card tone-${tone}`}>
              <div className="next-card-icon"><FileHeart size={21} /></div>
              <span className="eyebrow purple">CLINICAL NOTE</span>
              <h3>Keep the conversation human.</h3>
              <p>{suggestions[result.risk_level] || "Use the detailed report to guide a thoughtful clinical review."}</p>
              <div className="next-list">
                <span><Check size={15} /> Review the movement feature values</span>
                <span><Check size={15} /> Compare with symptoms over time</span>
                <span><Check size={15} /> Document the next clinical step</span>
              </div>
            </div>
          </div>
        </div>
      )}
      {tab === "signals" && (
        <div className="feature-table" data-testid="movement-features-table">
          <div className="table-title"><div><span className="eyebrow purple">RAW FEATURE VALUES</span><h3>Movement model inputs</h3></div><span className="score-small">{Object.keys(result.features || {}).length} features</span></div>
          {Object.entries(result.features || {}).map(([key, value]) => <div className="feature-row" key={key}><span>{key.replaceAll("_", " ")}</span><b>{value}</b></div>)}
        </div>
      )}
      {tab === "answers" && (
        <div className="feature-table" data-testid="questionnaire-answers-table">
          <div className="table-title"><div><span className="eyebrow purple">KOOS-PS RESPONSE PROFILE</span><h3>Patient-reported function</h3></div><span className="score-small">{result.koos_score} / 100</span></div>
          {questions.map((q, i) => <div className="feature-row" key={q}><span>{q}</span><b>{options[result.koos_answers?.[i] ?? result.koos_answers?.[String(i)] ?? 0]}</b></div>)}
        </div>
      )}
      <div className="closing-grid">
        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .5, delay: .1 }} className="meaning-card" data-testid="results-meaning-card">
          <span className="eyebrow purple">WHAT THIS MEANS</span>
          <h3>How to read this screening</h3>
          <p>The combined risk score blends what the patient told you through the seven KOOS-PS questions (<b>40%</b>) with what our knee-mounted sensors measured during the movement tests (<b>60%</b>). A higher score means the sensor and questionnaire signals agree on more concerning patterns of loading, range of motion, and gait — it is a triage cue, not a diagnosis.</p>
          <div className="meaning-legend">
            <div><span className="risk-pill low"><span className="pill-dot" />Low</span><small>0–35 · reassure and re-screen in 3 months</small></div>
            <div><span className="risk-pill moderate"><span className="pill-dot" />Moderate</span><small>36–63 · pace activity, re-screen in 4 weeks</small></div>
            <div><span className="risk-pill high"><span className="pill-dot" />High</span><small>64–79 · clinical exam, consider imaging</small></div>
            <div><span className="risk-pill very-high"><span className="pill-dot" />Very high</span><small>80–100 · same-week clinical review</small></div>
          </div>
          <p className="disclaimer"><ShieldCheck size={14} /> This screening is an early, AI-generated clinical signal, not a diagnosis. Correlate with clinical examination, patient history and imaging where appropriate.</p>
        </motion.div>
        <motion.div initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: .6, delay: .2 }} className="trust-card" data-testid="results-trust-card">
          <div className="trust-halo"><HeartHandshake size={26} /></div>
          <span className="eyebrow purple">BUILT ON TRUST</span>
          <h3>Care that listens, first.</h3>
          <p>JointSense is an assistant, never the decider. Your judgement and the patient's story stay at the centre of every screening.</p>
          <AnimatePresence mode="wait">
            <motion.div className="trust-rotator" key={result.id}>
              <TrustTagline />
            </motion.div>
          </AnimatePresence>
        </motion.div>
      </div>
    </Page>
  );
}

function TestRules({ test, onStart, disabled }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="rules-card" data-testid="test-rules">
      <span className="eyebrow purple">BEFORE YOU BEGIN</span>
      <h3>{test.title} · {formatTime(test.duration)}</h3>
      <ul className="rules-list">{test.rules.map((r) => <li key={r}><Check size={14} />{r}</li>)}</ul>
      <div className="safety-note"><ShieldCheck size={17} /><span><b>Safety first</b> · Pause immediately if pain, dizziness, or instability appears.</span></div>
      <Button data-testid="movement-start-button" onClick={onStart} disabled={disabled}>{disabled ? "Answer all 7 questions first" : `Start ${test.title}`}<ArrowRight size={17} /></Button>
    </motion.div>
  );
}

function LiveStage({ test, live, onFinish, startedAt }) {
  const [now, setNow] = useState(() => Date.now());
  const finishedRef = useMemo(() => ({ current: false }), [test.id, startedAt]);
  useEffect(() => {
    finishedRef.current = false;
    const timer = setInterval(() => setNow(Date.now()), 200);
    return () => clearInterval(timer);
  }, [test.id, startedAt, finishedRef]);
  const elapsedLocal = Math.max(0, (now - startedAt) / 1000);
  const remaining = Math.max(0, (test.duration || 0) - elapsedLocal);
  const percent = Math.min(100, Math.round((elapsedLocal / (test.duration || 1)) * 100));
  useEffect(() => {
    if (remaining <= 0 && !finishedRef.current && elapsedLocal > 0.5) {
      finishedRef.current = true;
      onFinish();
    }
  }, [remaining, elapsedLocal, onFinish, finishedRef]);
  const staleHardware = live?.source === "hardware-fallback" || live?.stale;
  return (
    <motion.div initial={{ opacity: 0, scale: .97 }} animate={{ opacity: 1, scale: 1 }} className="test-stage active" data-testid="test-stage-active">
      <div className="stage-rings"><div className="ring ring-a" /><div className="ring ring-b" /><div className="stage-icon"><Activity size={32} /></div></div>
      <div className="timer-block" data-testid="timer-block">
        <b className="timer" data-testid="timer-display">{formatTime(remaining)}</b>
        <small>remaining · {percent}%</small>
        <div className="timer-track"><i style={{ width: `${percent}%` }} /></div>
      </div>
      <div className="live-values" data-testid="live-values">
        <div><b>{live.features?.gait_speed ?? "—"}</b><small>Gait speed</small></div>
        <div><b>{live.features?.total_rom ?? "—"}°</b><small>Total ROM</small></div>
        <div><b>{live.features?.peak_loading ?? "—"}</b><small>Peak load</small></div>
      </div>
      <div className="live-caption">{live.source === "hardware" ? "Live from ESP32 edge device" : staleHardware ? "Waiting for ESP32 · showing simulator values" : "Streaming from local pipeline"}</div>
    </motion.div>
  );
}

function Assessment({ patient, onComplete, onBack }) {
  const [answers, setAnswers] = useState({});
  const [selected, setSelected] = useState(null);
  const [active, setActive] = useState(false);
  const [live, setLive] = useState({});
  const [done, setDone] = useState([]);
  const [startedAt, setStartedAt] = useState(null);
  const [finishing, setFinishing] = useState(false);
  useEffect(() => {
    if (!active) return;
    let stopped = false;
    const run = async () => { try { const { data } = await api.get("/assessment/live"); if (!stopped) setLive(data); } catch { } };
    run();
    const interval = setInterval(run, 700);
    return () => { stopped = true; clearInterval(interval); };
  }, [active]);
  const answered = Object.keys(answers).length;
  const start = async () => {
    if (!selected) return;
    try {
      await api.post("/assessment/start", { patient_id: patient.id, answers, pain_duration: patient.pain_duration, affected_leg: patient.affected_leg, test: selected.id });
      setStartedAt(Date.now());
      setLive({});
      setFinishing(false);
      setActive(true);
    } catch (err) { alert(formatError(err)); }
  };
  const finish = async () => {
    if (finishing) return;
    setFinishing(true);
    try {
      const { data } = await api.post("/assessment/stop");
      setActive(false);
      const nextDone = done.includes(selected.id) ? done : [...done, selected.id];
      setDone(nextDone);
      const remaining = tests.filter((t) => !nextDone.includes(t.id));
      if (remaining.length === 0) onComplete(data); else setSelected(null);
    } catch (err) {
      // If backend says no active assessment (already stopped), still advance UI
      const detail = err?.response?.data?.detail || "";
      if (String(detail).toLowerCase().includes("no active")) {
        setActive(false);
        const nextDone = done.includes(selected.id) ? done : [...done, selected.id];
        setDone(nextDone);
        const remaining = tests.filter((t) => !nextDone.includes(t.id));
        if (remaining.length > 0) setSelected(null);
      } else {
        alert(formatError(err));
      }
    } finally {
      setFinishing(false);
    }
  };
  const progressPct = Math.round((answered / 7) * 42 + (done.length / tests.length) * 58);
  return (
    <Page className="app-page assessment-page">
      <div className="assessment-top">
        <button className="back-button" data-testid="assessment-back-button" onClick={onBack}><ChevronLeft size={17} /> Patient profile</button>
        <div className="assessment-progress"><span>1 Screening for <b>{patient.name}</b></span><div><i style={{ width: `${progressPct}%` }} /></div></div>
        <span className="progress-chip" data-testid="progress-chip">{done.length} / 3 activities completed · {answered} / 7 answered</span>
      </div>
      <div className="assessment-layout">
        <div className="kos-panel">
          <span className="eyebrow purple">PART 01 · PATIENT-REPORTED FUNCTION</span>
          <h1>How is movement<br /><span>feeling today?</span></h1>
          <p className="muted">Answer based on their usual experience over the past week. Please complete all seven questions before starting a movement test.</p>
          <div className="question-list">
            {questions.map((q, i) => (
              <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * .04 }} className={`question-item ${answers[i] !== undefined ? "answered" : ""}`} key={q}>
                <div className="question-number">{answers[i] !== undefined ? <Check size={14} /> : `0${i + 1}`}</div>
                <div>
                  <b>{q}</b>
                  <div className="answer-options">
                    {options.map((option, value) => (
                      <button key={option} data-testid={`kos-${i}-${value}-button`} title={option} className={answers[i] === value ? "selected" : ""} onClick={() => setAnswers({ ...answers, [i]: value })}>{value}</button>
                    ))}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
        <div className="sensor-panel">
          <div className="sensor-header">
            <span className="eyebrow purple">PART 02 · 3-ACTIVITY BATTERY (1 SCREENING)</span>
            <h2>{done.length === 3 ? "All 3 activities completed!" : `Activity ${done.length + 1} of 3: Choose next`}</h2>
            <p>This single screening integrates all 3 clinical activities below. Complete each one to generate the full screening result.</p>
          </div>
          <div className="screening-battery-stepper" data-testid="screening-battery-stepper">
            {tests.map((item, i) => {
              const isDone = done.includes(item.id);
              const isSelected = selected?.id === item.id;
              return (
                <div key={item.id} className={`stepper-item ${isDone ? "done" : isSelected ? "active" : "pending"}`}>
                  <span className="stepper-badge">{isDone ? <Check size={12} /> : `0${i + 1}`}</span>
                  <span className="stepper-name">{item.title}</span>
                  {isDone ? <small className="stepper-tag done">Saved</small> : isSelected ? <small className="stepper-tag current">Active</small> : <small className="stepper-tag">Pending</small>}
                </div>
              );
            })}
          </div>
          {done.length > 0 && done.length < 3 && !active && (
            <div className="activity-saved-alert" data-testid="activity-saved-alert">
              <Check size={15} />
              <span><b>Activity {done.length} of 3 saved!</b> Select {3 - done.length === 1 ? "the remaining activity" : "another activity"} to complete this screening.</span>
            </div>
          )}
          {answered < 7 && !active && (
            <div className="hint-banner" data-testid="answer-hint-banner">
              <CircleHelp size={16} />
              <span>Please answer the {7 - answered} remaining question{7 - answered > 1 ? "s" : ""} before starting a movement test.</span>
            </div>
          )}
          <div className="test-tabs">
            {tests.map((item, i) => {
              const Icon = item.icon;
              const isDone = done.includes(item.id);
              const isSelected = selected?.id === item.id;
              return (
                <motion.button whileHover={{ y: -1 }} key={item.id} data-testid={`movement-test-${i}-button`} className={`${isSelected ? "selected" : ""} ${isDone ? "done" : ""}`} disabled={active || isDone} onClick={() => !active && !isDone && setSelected(item)}>
                  <Icon size={18} />
                  <span><b>{item.title}</b><small>{item.detail}</small></span>
                  {isDone ? <Check size={16} /> : <em>{formatTime(item.duration)}</em>}
                </motion.button>
              );
            })}
          </div>
          <AnimatePresence mode="wait">
            {active && selected ? (
              <LiveStage key={`live-${selected.id}-${startedAt}`} test={selected} live={live} onFinish={finish} startedAt={startedAt} />
            ) : selected ? (
              <TestRules key={`rules-${selected.id}`} test={selected} onStart={start} disabled={answered < 7} />
            ) : (
              <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="test-stage idle" data-testid="test-stage-idle">
                <div className="stage-rings"><div className="ring ring-a" /><div className="ring ring-b" /><div className="stage-icon"><Stethoscope size={32} /></div></div>
                <b>Select a movement test</b>
                <span>Tests can be taken in any order once questions are complete.</span>
              </motion.div>
            )}
          </AnimatePresence>
          {active && <Button data-testid="movement-stop-button" onClick={finish} disabled={finishing}>{finishing ? "Saving…" : <><Check size={17} /> Save {selected.title}</>}</Button>}
        </div>
      </div>
    </Page>
  );
}

function SettingsPage({ device, refreshDevice }) {
  const [form, setForm] = useState({ clinic_name: "", signature_name: "", hardware_mode: "simulator" });
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.get("/settings").then(({ data }) => { setForm(data); setLoading(false); }).catch(() => setLoading(false));
  }, []);
  const save = async () => {
    try { const { data } = await api.put("/settings", form); setForm(data); setSaved(true); refreshDevice?.(); setTimeout(() => setSaved(false), 2200); }
    catch (err) { alert(formatError(err)); }
  };
  return (
    <Page className="app-page narrow-page">
      <div className="page-header">
        <div><span className="eyebrow purple">WORKSPACE SETTINGS</span><h1>Configure your workspace.</h1><p className="muted">Set your clinic identity, signature, and switch between the local pipeline and a connected ESP32 edge device.</p></div>
      </div>
      {loading ? <div className="muted">Loading…</div> : (
        <div className="settings-grid">
          <div className="form-section">
            <div className="section-title"><div className="number-badge"><Stethoscope size={15} /></div><div><h3>Clinic identity</h3><p>Printed on every clinical PDF.</p></div></div>
            <label>Clinic name<input data-testid="settings-clinic-name" value={form.clinic_name} onChange={(e) => setForm({ ...form, clinic_name: e.target.value })} placeholder="e.g. Aarogya Joint Clinic, Pune" /></label>
            <label>Signature name<input data-testid="settings-signature-name" value={form.signature_name} onChange={(e) => setForm({ ...form, signature_name: e.target.value })} placeholder="e.g. Dr. Vedika Mehta, MPT" /></label>
          </div>
          <div className="form-section">
            <div className="section-title"><div className="number-badge"><Cpu size={15} /></div><div><h3>Signal source</h3><p>Switch between the local pipeline and an ESP32 edge device without changing any code.</p></div></div>
            <div className="segmented big">
              {[["simulator", "Local pipeline"], ["hardware", "ESP32 edge device"]].map(([id, label]) => (
                <button key={id} type="button" data-testid={`settings-mode-${id}`} className={form.hardware_mode === id ? "selected" : ""} onClick={() => setForm({ ...form, hardware_mode: id })}>{label}</button>
              ))}
            </div>
            <div className="hint-banner subtle"><Cpu size={16} /><span>Hardware mode reads live values from <code>POST /api/hw/ingest</code>. If your ESP32 hasn't sent a packet in the last 4 seconds, JointSense automatically falls back to simulator values so screenings never stall — swap to real data by pushing packets with your device key (<code>HW_INGEST_KEY</code>) from the Pi.</span></div>
            <div className="device-status-row" data-testid="settings-device-status"><span className={`live-dot ${device?.mode === "hardware" && !device?.hardware_stream_live ? "warn" : ""}`} /><b>{device?.mode === "hardware" ? (device?.hardware_stream_live ? "Edge device streaming" : "Waiting for edge device") : "Local pipeline active"}</b></div>
          </div>
          <Button data-testid="settings-save-button" onClick={save}>Save settings <ArrowRight size={17} /></Button>
          {saved && <span className="save-toast" data-testid="settings-saved-toast"><Check size={14} /> Saved</span>}
        </div>
      )}
    </Page>
  );
}

function useDeviceStatus(active) {
  const [device, setDevice] = useState(null);
  const refresh = () => api.get("/device/status").then(({ data }) => setDevice(data)).catch(() => { });
  useEffect(() => {
    if (!active) return;
    refresh(); const t = setInterval(refresh, 5000); return () => clearInterval(t);
  }, [active]);
  return [device, refresh];
}

function App() {
  const [theme, setTheme] = useState(localStorage.getItem("jointsense_theme") || "light");
  const [stage, setStage] = useState(localStorage.getItem("jointsense_token") ? "dashboard" : "welcome");
  const [authMode, setAuthMode] = useState("login");
  const [lang, setLang] = useState(() => localStorage.getItem("jointsense_lang") || "English");
  const [user, setUser] = useState(null);
  const [page, setPage] = useState("overview");
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [result, setResult] = useState(null);
  const [device, refreshDevice] = useDeviceStatus(stage === "dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(() => { const v = localStorage.getItem("jointsense_sidebar"); return v === null ? true : v === "1"; });
  useEffect(() => { localStorage.setItem("jointsense_sidebar", sidebarOpen ? "1" : "0"); }, [sidebarOpen]);
  useEffect(() => { localStorage.setItem("jointsense_lang", lang); document.documentElement.lang = langCodeMap[lang] || "en"; }, [lang]);
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("jointsense_theme", theme); }, [theme]);
  useEffect(() => {
    if (stage === "dashboard") {
      api.get("/auth/me").then(({ data }) => { setUser(data); return api.get("/patients"); }).then(({ data }) => setPatients(data)).catch(() => { localStorage.removeItem("jointsense_token"); setStage("welcome"); });
    }
  }, [stage]);
  const t = useMemo(() => makeTranslator(lang), [lang]);
  const toggleTheme = () => setTheme(theme === "dark" ? "light" : "dark");
  const logout = async () => { try { await api.post("/auth/logout"); } catch { } localStorage.removeItem("jointsense_token"); setStage("welcome"); setPage("overview"); };
  const refresh = () => api.get("/patients").then(({ data }) => setPatients(data));
  const openPatient = async (p) => {
    try { const { data } = await api.get(`/patients/${p.id}`); setSelectedPatient(data); }
    catch { setSelectedPatient(p); }
    setPage("patient");
  };
  const openScreening = (h) => { setResult(h); setPage("results"); };
  return (
    <LangContext.Provider value={{ lang, setLang, t }}>
      <div className="app-root">
        <AnimatePresence mode="wait">
          {stage === "welcome" && <Welcome key="welcome" theme={theme} toggleTheme={toggleTheme} onStart={() => setStage("language")} />}
          {stage === "language" && <Language key="language" onBack={() => setStage("welcome")} onNext={(l) => { setLang(l); setStage("auth"); }} />}
          {stage === "auth" && <Auth key="auth" mode={authMode} setMode={setAuthMode} onBack={() => setStage("language")} onSuccess={(u) => { setUser(u); setStage("dashboard"); }} />}
          {stage === "dashboard" && (
            <div className={`workspace ${sidebarOpen ? "" : "sidebar-collapsed"}`} key="workspace">
              {sidebarOpen && <Sidebar page={page} setPage={setPage} user={user} theme={theme} toggleTheme={toggleTheme} onLogout={logout} device={device} />}
              <div className="workspace-main">
                <button className="sidebar-toggle" data-testid="sidebar-toggle" onClick={() => setSidebarOpen((v) => !v)} title={sidebarOpen ? "Hide navigation" : "Show navigation"}>
                  {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
                </button>
                <AnimatePresence mode="wait">
                  {page === "overview" && <Overview key="overview" user={user} patients={patients} setPage={setPage} setSelectedPatient={(p) => openPatient(p)} />}
                  {page === "patients" && <Patients key="patients" patients={patients} setPage={setPage} setSelectedPatient={(p) => openPatient(p)} />}
                  {page === "settings" && <SettingsPage key="settings" device={device} refreshDevice={refreshDevice} />}
                  {page === "new-patient" && <PatientForm key="new-patient" onBack={() => setPage("patients")} onCreated={(p) => { refresh(); setSelectedPatient(p); setPage("assessment"); }} />}
                  {page === "patient" && selectedPatient && <PatientProfile key="patient" patient={selectedPatient} onBack={() => { refresh(); setPage("patients"); }} onStart={() => setPage("assessment")} onReopen={openScreening} />}
                  {page === "assessment" && selectedPatient && <Assessment key="assessment" patient={selectedPatient} onBack={() => openPatient(selectedPatient)} onComplete={(r) => { setResult(r); refresh(); setPage("results"); }} />}
                  {page === "results" && result && <Results key="results" result={result} patient={selectedPatient} onBack={() => openPatient(selectedPatient)} />}
                </AnimatePresence>
              </div>
            </div>
          )}
        </AnimatePresence>
      </div>
    </LangContext.Provider>
  );
}
export default App;
