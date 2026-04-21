"""
CareConnect — Telemedicine Appointment Scheduler Chatbot
Flask Backend v2.0 — Multi-step patient registration, State/City/Branch selection,
DOB → Age conversion, Patient ID, Health issue options, Filtered doctors
"""
import os, json, random, string
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session
from sarvam_client import extract_intent, get_chatbot_response
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "careconnect-secret-2026-telemedicine")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ─── Health Issue → Specialization Mapping ────────────────────────────────────

HEALTH_ISSUES = [
    {"label": "🔍 General Checkup",              "value": "general_checkup",  "specialization": "General Physician"},
    {"label": "🩺 Skin / Hair / Nail Issues",     "value": "skin_issues",      "specialization": "Dermatologist"},
    {"label": "❤️ Heart / Blood Pressure",        "value": "heart_issues",     "specialization": "Cardiologist"},
    {"label": "🧠 Headache / Neuro / Brain",      "value": "neuro_issues",     "specialization": "Neurologist"},
    {"label": "🦴 Bone / Joint / Spine Pain",     "value": "bone_joint",       "specialization": "Orthopedist"},
    {"label": "👶 Child Health / Vaccination",    "value": "child_health",     "specialization": "Pediatrician"},
    {"label": "🤒 Fever / Cold / Flu",            "value": "fever_cold",       "specialization": "General Physician"},
    {"label": "🫁 Lungs / Breathing Issues",      "value": "respiratory",      "specialization": "Pulmonologist"},
    {"label": "👁️ Eye / Vision Problems",         "value": "eye_issues",       "specialization": "Ophthalmologist"},
    {"label": "💊 Diabetes / Thyroid / Hormones","value": "endocrine",        "specialization": "Endocrinologist"},
    {"label": "🫘 Kidney / Urinary Issues",       "value": "kidney_issues",    "specialization": "Nephrologist"},
    {"label": "🧘 Mental Health / Anxiety",       "value": "mental_health",    "specialization": "Psychiatrist"},
    {"label": "🫄 Stomach / Digestive Issues",    "value": "gastro",           "specialization": "Gastroenterologist"},
]

ISSUE_TO_SPEC = {i["value"]: i["specialization"] for i in HEALTH_ISSUES}
ISSUE_TO_LABEL = {i["value"]: i["label"] for i in HEALTH_ISSUES}

# ─── Data Helpers ─────────────────────────────────────────────────────────────

def load_data(filename):
    with open(os.path.join(DATA_DIR, filename)) as f:
        return json.load(f)

def save_data(filename, data):
    with open(os.path.join(DATA_DIR, filename), "w") as f:
        json.dump(data, f, indent=2)

def get_doctor(doctor_id):
    if not doctor_id: return None
    return next((d for d in load_data("doctors.json") if d["id"].upper() == str(doctor_id).strip().upper()), None)

def get_hospital(branch_id):
    if not branch_id: return None
    return next((h for h in load_data("hospitals.json") if h["id"].upper() == str(branch_id).strip().upper()), None)

def get_patient_by_phone(phone):
    return next((p for p in load_data("patients.json") if p.get("phone") == phone.strip()), None)

def get_appointment(apt_id):
    return next((a for a in load_data("appointments.json")
                 if a["appointment_id"] == apt_id.upper().strip()), None)

def generate_appointment_id():
    today = datetime.now().strftime("%Y-%m-%d")
    return f"APT-{today}-{''.join(random.choices(string.digits, k=4))}"

def generate_patient_id():
    patients = load_data("patients.json")
    return f"P{str(len(patients) + 1).zfill(3)}"

def parse_dob(dob_str):
    """Parse DOB string → (age_years, formatted_dob). Returns (None, None) on failure."""
    dob_str = dob_str.strip()
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
        "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y",
        "%d/%m/%y", "%d-%m-%y",
    ]
    for fmt in formats:
        try:
            dob = datetime.strptime(dob_str, fmt)
            today = datetime.now()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return age, dob.strftime("%d %B %Y")
        except ValueError:
            continue
    return None, None

def get_next_available_dates(doctor, num_days=5):
    """Generate next N working dates for a doctor (starting tomorrow)."""
    day_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
    working = set(day_map[d] for d in doctor.get("working_days", ["Mon","Tue","Wed","Thu","Fri","Sat"]) if d in day_map)
    dates, i = [], 1
    while len(dates) < num_days:
        candidate = datetime.now() + timedelta(days=i)
        if candidate.weekday() in working:
            dates.append(candidate.strftime("%d %B %Y"))
        i += 1
    return dates

def get_available_slots(doctor, date):
    """Return slots not yet booked for doctor on given date."""
    all_slots = doctor.get("available_slots", [])
    booked = doctor.get("booked_slots", {}).get(date, [])
    return [s for s in all_slots if s not in booked]

def book_slot(doctor_id, date, time_slot):
    doctors = load_data("doctors.json")
    for doc in doctors:
        if doc["id"] == doctor_id:
            doc.setdefault("booked_slots", {}).setdefault(date, []).append(time_slot)
            break
    save_data("doctors.json", doctors)

def release_slot(doctor_id, date, time_slot):
    doctors = load_data("doctors.json")
    for doc in doctors:
        if doc["id"] == doctor_id:
            booked = doc.get("booked_slots", {}).get(date, [])
            if time_slot in booked:
                booked.remove(time_slot)
            break
    save_data("doctors.json", doctors)

def get_doctors_for_branch(branch_id, specialization=None):
    hospital = get_hospital(branch_id)
    if not hospital:
        return []
    doc_ids = hospital.get("doctor_ids", [])
    doctors = [d for d in load_data("doctors.json") if d["id"] in doc_ids]
    if specialization:
        matched = [d for d in doctors if d["specialization"] == specialization]
        return matched if matched else doctors  # fallback to all if no match
    return doctors

def build_doctor_cards(doctors):
    cards = []
    for d in doctors:
        cards.append({
            "id": d["id"],
            "name": d["name"],
            "specialization": d["specialization"],
            "rating": d["rating"],
            "experience": d["experience"],
            "fee": d["fee"],
            "about": d.get("about", ""),
            "working_days": d.get("working_days", []),
        })
    return cards

def build_confirmation_report(apt):
    doctor = get_doctor(apt["doctor_id"])
    hospital = get_hospital(apt["branch_id"])
    patients = load_data("patients.json")
    patient = next((p for p in patients if p["id"] == apt["patient_id"]), None)
    return {
        "appointment_id": apt["appointment_id"],
        "patient_id": apt.get("patient_id", ""),
        "patient_name": apt["patient_name"],
        "patient_age": apt.get("patient_age", ""),
        "patient_dob": apt.get("patient_dob", ""),
        "health_issue": apt.get("health_issue_label", ""),
        "doctor_name": doctor["name"] if doctor else apt["doctor_id"],
        "specialization": doctor["specialization"] if doctor else "",
        "rating": doctor["rating"] if doctor else "",
        "about": doctor.get("about", "") if doctor else "",
        "hospital_name": hospital["name"] if hospital else apt["branch_id"],
        "hospital_address": hospital["address"] if hospital else "",
        "city": hospital["city"] if hospital else "",
        "state": hospital.get("state", "") if hospital else "",
        "date": apt["date"],
        "time": apt["time"],
        "status": apt["status"],
        "fee": doctor["fee"] if doctor else "",
    }

# ─── Session Helpers ──────────────────────────────────────────────────────────

def get_state():   return session.get("chat_state", "WELCOME")
def set_state(s):  session["chat_state"] = s
def get_ctx():     return session.get("ctx", {})
def set_ctx(c):    session["ctx"] = c
def update_ctx(**kw):
    c = get_ctx(); c.update(kw); set_ctx(c)
def reset_session(): session.clear()

def msg(text, msg_type="text", data=None):
    return {"type": msg_type, "text": text, "data": data or {}}

# ─── Conversation State Machine ───────────────────────────────────────────────

def handle_message(user_text):
    state = get_state()
    ctx = get_ctx()

    if user_text.lower().strip() in ["restart", "start over", "reset", "menu", "main menu"]:
        reset_session()
        return handle_welcome()

    handlers = {
        "WELCOME":              handle_welcome_input,
        "IDENTIFY_USER":        handle_identify_user,
        # New Patient (3-step)
        "NEW_PATIENT_NAME":     handle_new_patient_name,
        "NEW_PATIENT_DOB":      handle_new_patient_dob,
        "NEW_PATIENT_ISSUE":    handle_new_patient_issue,
        # Existing Patient
        "EXISTING_LOGIN":       handle_existing_login,
        "EXISTING_ISSUE":       handle_existing_issue,
        # Location selection (3-level)
        "STATE_SELECTION":      handle_state_selection,
        "CITY_SELECTION":       handle_city_selection,
        "BRANCH_SELECTION":     handle_branch_selection,
        # Doctor & Booking
        "DOCTOR_SELECTION":     handle_doctor_selection,
        "DATE_SELECTION":       handle_date_selection,
        "TIME_SLOT_SELECTION":  handle_time_slot,
        "CONFIRM_BOOKING":      handle_confirm_booking,
        "BOOKING_COMPLETE":     handle_booking_complete,
        # Reschedule
        "RESCHEDULE_ENTER_ID":  handle_reschedule_enter_id,
        "RESCHEDULE_CONFIRM_DETAILS": handle_reschedule_confirm_details,
        "RESCHEDULE_DATE":      handle_reschedule_date,
        "RESCHEDULE_TIME":      handle_reschedule_time,
        "RESCHEDULE_CONFIRM":   handle_reschedule_confirm,
        # Cancel
        "CANCEL_ENTER_ID":      handle_cancel_enter_id,
        "CANCEL_ENTER_REASON":  handle_cancel_enter_reason,
        "CANCEL_CONFIRM":       handle_cancel_confirm,
    }
    return handlers.get(state, handle_welcome_input)(user_text, ctx)


# ─── Welcome ──────────────────────────────────────────────────────────────────

def handle_welcome():
    set_state("WELCOME")
    set_ctx({})
    return [
        msg("👋 Hello! Welcome to <strong>CareConnect Telemedicine</strong><br>I'm your virtual hospital assistant. I can help you book, reschedule, or cancel doctor appointments."),
        msg("", "quick_reply", {"options": [
            {"label": "📅 Book Appointment", "value": "book"},
            {"label": "🔄 Reschedule",        "value": "reschedule"},
            {"label": "❌ Cancel Appointment", "value": "cancel"},
            {"label": "📋 View Dashboard",     "value": "dashboard"},
        ]})
    ]

def handle_welcome_input(user_text, ctx):
    m = user_text.lower().strip()
    if any(x in m for x in ["book","appointment","schedule","want","need","consult"]):
        set_state("IDENTIFY_USER")
        return [msg("Sure! Let's get started 😊<br>Are you a:", "quick_reply", {"options": [
            {"label": "🆕 New Patient",      "value": "new"},
            {"label": "🔁 Existing Patient", "value": "existing"},
        ]})]
    elif any(x in m for x in ["reschedule","change","modify","shift","postpone"]):
        set_state("RESCHEDULE_ENTER_ID")
        return [msg("Sure! Please enter your <strong>Appointment ID</strong> to reschedule:<br><em>Example: APT-2026-04-25-4582</em>")]
    elif any(x in m for x in ["cancel","delete"]):
        set_state("CANCEL_ENTER_ID")
        return [msg("Please enter your <strong>Appointment ID</strong> to cancel:")]
    elif "dashboard" in m:
        return [msg("🔗 Opening your dashboard...", "redirect", {"url": "/dashboard"})]
    else:
        return [msg("I didn't quite understand that 🤔 Please choose an option:", "quick_reply", {"options": [
            {"label": "📅 Book Appointment", "value": "book"},
            {"label": "🔄 Reschedule",        "value": "reschedule"},
            {"label": "❌ Cancel Appointment", "value": "cancel"},
        ]})]


# ─── Identify User ────────────────────────────────────────────────────────────

def handle_identify_user(user_text, ctx):
    m = user_text.lower().strip()
    if "new" in m:
        set_state("NEW_PATIENT_NAME")
        return [msg("Great! Let's register you as a new patient 😊<br><br>Please enter your <strong>Full Name</strong>:")]
    elif "existing" in m:
        set_state("EXISTING_LOGIN")
        return [msg("Welcome back! 😊<br>Please enter your <strong>Patient ID</strong> (e.g., P001):")]
    else:
        return [msg("Please select:", "quick_reply", {"options": [
            {"label": "🆕 New Patient",       "value": "new"},
            {"label": "🔁 Existing Patient",  "value": "existing"},
        ]})]


# ─── New Patient — 3-Step Registration ───────────────────────────────────────

def handle_new_patient_name(user_text, ctx):
    name = user_text.strip()
    if len(name) < 2 or any(c.isdigit() for c in name):
        return [msg("Please enter a valid <strong>Full Name</strong> (letters only):")]
    update_ctx(patient_name=name)
    set_state("NEW_PATIENT_DOB")
    return [msg(f"Nice to meet you, <strong>{name}</strong>! 👋<br><br>Please enter your <strong>Date of Birth</strong>:<br><em>Formats accepted: DD/MM/YYYY, DD-MM-YYYY, 21 April 2006</em>")]

def handle_new_patient_dob(user_text, ctx):
    age, dob_formatted = parse_dob(user_text.strip())
    if age is None:
        return [msg("❌ Could not parse that date. Please enter your Date of Birth in a valid format:<br><em>Examples: 21/04/2006 &nbsp;|&nbsp; 21-04-2006 &nbsp;|&nbsp; 21 April 2006</em>")]
    if age < 0 or age > 120:
        return [msg("❌ Please enter a valid Date of Birth.")]
    update_ctx(patient_age=age, patient_dob=dob_formatted)
    set_state("NEW_PATIENT_ISSUE")
    return [
        msg(f"Got it! Age: <strong>{age} years</strong> (DOB: {dob_formatted}) ✅<br><br>What health concern brings you in today?<br>Please select one:"),
        msg("", "issue_options", {"options": HEALTH_ISSUES})
    ]

def handle_new_patient_issue(user_text, ctx):
    m = user_text.lower().strip()
    issue_entry = next((i for i in HEALTH_ISSUES if i["value"] == m), None)
    if not issue_entry:
        return [
            msg("Please select your health concern from the options:"),
            msg("", "issue_options", {"options": HEALTH_ISSUES})
        ]
    specialization = issue_entry["specialization"]
    issue_label = issue_entry["label"]
    update_ctx(
        health_issue=issue_entry["value"],
        health_issue_label=issue_label,
        required_specialization=specialization,
    )

    # Save patient
    patients = load_data("patients.json")
    patient_id = generate_patient_id()
    patients.append({
        "id": patient_id,
        "name": ctx.get("patient_name"),
        "age": ctx.get("patient_age"),
        "dob": ctx.get("patient_dob"),
        "phone": "",
        "email": "",
        "issue": issue_label,
        "last_doctor_id": None,
        "last_branch_id": None,
        "appointment_history": []
    })
    save_data("patients.json", patients)
    update_ctx(patient_id=patient_id)

    # Go to state selection
    set_state("STATE_SELECTION")
    states = load_data("states.json")
    return [
        msg(f"Your Patient ID is <strong>{patient_id}</strong> 🆔<br>You're looking for a <strong>{specialization}</strong>.<br><br>Please select your <strong>State</strong>:"),
        msg("", "quick_reply", {"options": [{"label": f"📍 {s['name']}", "value": s["name"]} for s in states]})
    ]


# ─── Existing Patient ─────────────────────────────────────────────────────────

def handle_existing_login(user_text, ctx):
    pid = user_text.strip().upper()
    patients = load_data("patients.json")
    patient = next((p for p in patients if p["id"] == pid), None)
    if not patient:
        return [msg("❌ Patient ID not found.<br>Please try again or type <strong>new</strong> to register as a new patient.")]

    update_ctx(
        patient_id=patient["id"],
        patient_name=patient["name"],
        patient_age=patient.get("age", ""),
        patient_dob=patient.get("dob", ""),
    )
    responses = [msg(f"Welcome back, <strong>{patient['name']}</strong>! 😊")]

    if patient.get("last_doctor_id"):
        last_doc = get_doctor(patient["last_doctor_id"])
        if last_doc:
            update_ctx(branch_id=patient.get("last_branch_id"))
            responses.append(msg(
                f"Your last consultation was with <strong>{last_doc['name']}</strong> ({last_doc['specialization']})",
                "quick_reply",
                {"options": [
                    {"label": f"👨‍⚕️ Book with {last_doc['name']} again", "value": f"same_doctor_{last_doc['id']}"},
                    {"label": "🔍 Choose a different doctor",              "value": "choose_different"},
                ]}
            ))
            set_state("EXISTING_ISSUE")
            return responses

    # No history — ask issue
    set_state("EXISTING_ISSUE")
    responses.append(msg("What is your health concern today?"))
    responses.append(msg("", "issue_options", {"options": HEALTH_ISSUES}))
    return responses

def handle_existing_issue(user_text, ctx):
    m = user_text.lower().strip()

    # Same doctor shortcut
    if m.startswith("same_doctor_"):
        doctor_id = m.replace("same_doctor_", "").upper()
        doctor = get_doctor(doctor_id)
        if doctor:
            # Re-ask issue for correct specialization, then go straight to dates
            update_ctx(
                doctor_id=doctor_id,
                doctor_name=doctor["name"],
                health_issue_label=doctor["specialization"],
                required_specialization=doctor["specialization"],
                branch_id=ctx.get("branch_id", doctor["branch_id"]),
            )
            dates = get_next_available_dates(doctor)
            set_state("DATE_SELECTION")
            hosp = get_hospital(doctor["branch_id"])
            return [
                msg(f"Booking with <strong>{doctor['name']}</strong> ({doctor['specialization']}) again 😊"),
                msg("", "doctor_profile", {
                    "doctor": {**build_doctor_cards([doctor])[0], "about": doctor.get("about", ""),
                               "hospital": hosp["name"] if hosp else "", "address": hosp["address"] if hosp else ""}
                }),
                msg(f"Please select your preferred date:", "date_picker", {"dates": dates}),
            ]

    if m == "choose_different":
        set_state("EXISTING_ISSUE")
        return [
            msg("What is your health concern today?"),
            msg("", "issue_options", {"options": HEALTH_ISSUES})
        ]

    # Selecting issue
    issue_entry = next((i for i in HEALTH_ISSUES if i["value"] == m), None)
    if not issue_entry:
        return [
            msg("Please select your health concern:"),
            msg("", "issue_options", {"options": HEALTH_ISSUES})
        ]
    update_ctx(
        health_issue=issue_entry["value"],
        health_issue_label=issue_entry["label"],
        required_specialization=issue_entry["specialization"],
    )
    set_state("STATE_SELECTION")
    states = load_data("states.json")
    return [
        msg("Please select your <strong>State</strong>:"),
        msg("", "quick_reply", {"options": [{"label": f"📍 {s['name']}", "value": s["name"]} for s in states]})
    ]


# ─── Location: State → City → Branch ─────────────────────────────────────────

def handle_state_selection(user_text, ctx):
    m = user_text.strip()
    states = load_data("states.json")
    selected = next((s for s in states if s["name"].lower() == m.lower()), None)
    if not selected:
        return [msg("Please select a valid state:", "quick_reply", {
            "options": [{"label": f"📍 {s['name']}", "value": s["name"]} for s in states]
        })]
    update_ctx(state=selected["name"])
    set_state("CITY_SELECTION")
    cities = selected.get("cities", [])
    # Only show cities where we have hospitals
    hospitals = load_data("hospitals.json")
    valid_cities = [c for c in cities if any(h["city"] == c and h["state"] == selected["name"] for h in hospitals)]
    if not valid_cities:
        valid_cities = cities[:3]
    return [
        msg(f"Great! You selected <strong>{selected['name']}</strong>. Now choose your <strong>City</strong>:"),
        msg("", "quick_reply", {"options": [{"label": f"🏙️ {c}", "value": c} for c in valid_cities]})
    ]

def handle_city_selection(user_text, ctx):
    m = user_text.strip()
    hospitals = load_data("hospitals.json")
    state = ctx.get("state", "")
    city_branches = [h for h in hospitals
                     if h["city"].lower() == m.lower() and h["state"].lower() == state.lower()]

    if not city_branches:
        # Try without state filter
        city_branches = [h for h in hospitals if h["city"].lower() == m.lower()]

    if not city_branches:
        # Re-ask
        states = load_data("states.json")
        sel_state = next((s for s in states if s["name"] == state), None)
        cities = sel_state["cities"] if sel_state else []
        return [msg("Please select a valid city:", "quick_reply", {
            "options": [{"label": f"🏙️ {c}", "value": c} for c in cities]
        })]

    update_ctx(city=m)
    set_state("BRANCH_SELECTION")
    return [
        msg(f"📍 Here are our <strong>{m}</strong> branches:"),
        msg("", "branch_list", {"branches": [
            {"id": b["id"], "name": b["name"], "address": b["address"]} for b in city_branches
        ]}),
    ]

def handle_branch_selection(user_text, ctx):
    m = user_text.lower().strip()
    hospitals = load_data("hospitals.json")
    city = ctx.get("city", "")
    city_branches = [h for h in hospitals if h["city"].lower() == city.lower()]

    selected = None
    for i, b in enumerate(city_branches):
        if (str(i + 1) == m or b["name"].lower() in m or
                m in b["name"].lower() or b["id"].lower() == m):
            selected = b
            break
    if not selected:
        selected = next((h for h in hospitals if h["id"].lower() == m), None)

    if not selected:
        return [msg("Please select a branch by clicking one:", "branch_list", {
            "branches": [{"id": b["id"], "name": b["name"], "address": b["address"]} for b in city_branches]
        })]

    update_ctx(branch_id=selected["id"], branch_name=selected["name"])
    spec = ctx.get("required_specialization")
    branch_doctors = get_doctors_for_branch(selected["id"], spec)
    branch_doctors.sort(key=lambda d: d["rating"], reverse=True)
    update_ctx(available_doctors=[d["id"] for d in branch_doctors])
    set_state("DOCTOR_SELECTION")

    has_spec = any(d["specialization"] == spec for d in branch_doctors)
    note = f"Showing <strong>{spec}</strong> specialists" if has_spec else "No exact specialists found — showing all available doctors"
    return [
        msg(f"<strong>{selected['name']}</strong> — {note}:"),
        msg("", "doctor_cards", {"doctors": build_doctor_cards(branch_doctors)}),
    ]


# ─── Doctor Selection ─────────────────────────────────────────────────────────

def handle_doctor_selection(user_text, ctx):
    m = user_text.lower().strip()
    docs = load_data("doctors.json")
    avail_ids = ctx.get("available_doctors", [])
    avail_docs = [d for d in docs if d["id"] in avail_ids]

    selected = None

    if m.startswith("select_doctor_"):
        doc_id = m.replace("select_doctor_", "").upper()
        selected = next((d for d in avail_docs if d["id"].upper() == doc_id), None)
    else:
        for d in avail_docs:
            if d["name"].lower() in m or any(p in m for p in d["name"].lower().split()):
                selected = d
                break
        if not selected:
            for i, d in enumerate(avail_docs):
                if str(i + 1) == m:
                    selected = d; break

    if not selected:
        return [msg("Please select a doctor by clicking their card:", "doctor_cards", {
            "doctors": build_doctor_cards(avail_docs)
        })]

    update_ctx(doctor_id=selected["id"], doctor_name=selected["name"])
    dates = get_next_available_dates(selected)
    hosp = get_hospital(ctx.get("branch_id", selected.get("branch_id", "")))
    set_state("DATE_SELECTION")

    return [
        msg(""),  # empty to trigger doctor profile render
        msg("", "doctor_profile", {
            "doctor": {
                **build_doctor_cards([selected])[0],
                "about": selected.get("about", ""),
                "hospital": hosp["name"] if hosp else "",
                "address": hosp["address"] if hosp else "",
                "working_days": ", ".join(selected.get("working_days", [])),
            }
        }),
        msg(f"You've selected <strong>{selected['name']}</strong>.<br>Please choose your preferred date:", "date_picker", {"dates": dates}),
    ]


# ─── Date & Time ──────────────────────────────────────────────────────────────

def handle_date_selection(user_text, ctx):
    doctor = get_doctor(ctx.get("doctor_id"))
    if not doctor:
        set_state("WELCOME")
        return [msg("Session error — let's start over.", "quick_reply", {"options": [{"label": "🏠 Start Over", "value": "book"}]})]

    m = user_text.strip()
    dates = get_next_available_dates(doctor)

    selected_date = None
    for d in dates:
        if d.lower() == m.lower() or d.split()[0] == m:
            selected_date = d; break

    if not selected_date:
        return [msg("Please select a valid date:", "date_picker", {"dates": dates})]

    slots = get_available_slots(doctor, selected_date)
    if not slots:
        return [msg(f"Sorry 😔 No slots on <strong>{selected_date}</strong>. Choose another date:", "date_picker", {"dates": dates})]

    update_ctx(date=selected_date)
    set_state("TIME_SLOT_SELECTION")
    return [msg(f"Available time slots for <strong>{selected_date}</strong>:", "time_slots", {
        "slots": slots, "date": selected_date
    })]

def handle_time_slot(user_text, ctx):
    doctor = get_doctor(ctx.get("doctor_id"))
    selected_date = ctx.get("date")
    if not doctor or not selected_date:
        set_state("WELCOME")
        return [msg("Session error.", "quick_reply", {"options": [{"label": "🏠 Start Over", "value": "book"}]})]

    slots = get_available_slots(doctor, selected_date)
    m = user_text.strip()
    selected_slot = None

    for s in slots:
        if s.lower() == m.lower():
            selected_slot = s; break
    if not selected_slot:
        for i, s in enumerate(slots):
            if str(i + 1) == m:
                selected_slot = s; break
    if not selected_slot:
        if "morning" in m.lower():
            am = [s for s in slots if "AM" in s]
            selected_slot = am[0] if am else None
        elif "afternoon" in m.lower():
            pm = [s for s in slots if "PM" in s and int(s.split(":")[0]) < 5]
            selected_slot = pm[0] if pm else None
        elif "evening" in m.lower():
            eve = [s for s in slots if "PM" in s and int(s.split(":")[0]) >= 4]
            selected_slot = eve[0] if eve else None

    if not selected_slot:
        return [msg("Please select a valid time slot:", "time_slots", {"slots": slots, "date": selected_date})]

    update_ctx(time=selected_slot)
    set_state("CONFIRM_BOOKING")
    branch = get_hospital(ctx.get("branch_id"))
    return [msg(
        f"Please confirm your appointment details:<br><br>"
        f"👤 <strong>Name:</strong> {ctx.get('patient_name', 'N/A')}<br>"
        f"🎂 <strong>Age:</strong> {ctx.get('patient_age', 'N/A')} yrs<br>"
        f"🩺 <strong>Concern:</strong> {ctx.get('health_issue_label', 'N/A')}<br>"
        f"👨‍⚕️ <strong>Doctor:</strong> {doctor['name']} ({doctor['specialization']})<br>"
        f"🏥 <strong>Hospital:</strong> {branch['name'] if branch else 'N/A'}<br>"
        f"📅 <strong>Date:</strong> {selected_date}<br>"
        f"⏰ <strong>Time:</strong> {selected_slot}<br>"
        f"💰 <strong>Fee:</strong> ₹{doctor['fee']}",
        "confirm",
        {"options": [
            {"label": "✅ Confirm Booking", "value": "yes"},
            {"label": "❌ Cancel",           "value": "no"},
        ]}
    )]


# ─── Confirm Booking ──────────────────────────────────────────────────────────

def handle_confirm_booking(user_text, ctx):
    m = user_text.lower().strip()
    if m in ["yes", "confirm", "✅ confirm booking"]:
        apt_id = generate_appointment_id()
        appointment = {
            "appointment_id": apt_id,
            "patient_id":     ctx.get("patient_id", "GUEST"),
            "patient_name":   ctx.get("patient_name", "Patient"),
            "patient_age":    ctx.get("patient_age", ""),
            "patient_dob":    ctx.get("patient_dob", ""),
            "health_issue_label": ctx.get("health_issue_label", ""),
            "doctor_id":  ctx.get("doctor_id"),
            "branch_id":  ctx.get("branch_id"),
            "date":       ctx.get("date"),
            "time":       ctx.get("time"),
            "status":     "Confirmed",
            "created_at": datetime.now().isoformat(),
        }
        apts = load_data("appointments.json")
        apts.append(appointment)
        save_data("appointments.json", apts)
        book_slot(ctx["doctor_id"], ctx["date"], ctx["time"])

        # Update patient record
        if ctx.get("patient_id") and ctx["patient_id"] != "GUEST":
            patients = load_data("patients.json")
            for p in patients:
                if p["id"] == ctx["patient_id"]:
                    p["last_doctor_id"]  = ctx["doctor_id"]
                    p["last_branch_id"]  = ctx["branch_id"]
                    p.setdefault("appointment_history", []).append(apt_id)
                    break
            save_data("patients.json", patients)

        report = build_confirmation_report(appointment)
        set_state("BOOKING_COMPLETE")
        return [
            msg("🎉 Your appointment is successfully booked!"),
            msg("", "appointment_report", {"report": report}),
        ]
    elif m in ["no", "cancel", "❌ cancel"]:
        set_state("WELCOME")
        return [msg("Booking cancelled. Anything else I can help with?", "quick_reply", {"options": [
            {"label": "📅 Book Again", "value": "book"},
            {"label": "🏠 Home",        "value": "menu"},
        ]})]
    else:
        return [msg("Please confirm:", "quick_reply", {"options": [
            {"label": "✅ Yes, Confirm", "value": "yes"},
            {"label": "❌ No, Cancel",   "value": "no"},
        ]})]

def handle_booking_complete(user_text, ctx):
    reset_session()
    return handle_welcome()


# ─── Reschedule Flow ──────────────────────────────────────────────────────────

def handle_reschedule_enter_id(user_text, ctx):
    apt = get_appointment(user_text.strip().upper())
    if not apt:
        return [msg("❌ Appointment ID not found.<br><em>Format: APT-YYYY-MM-DD-XXXX</em>")]
    if apt["status"] == "Cancelled":
        return [msg("This appointment is already cancelled. Type <strong>book</strong> to schedule a new one.")]
    doctor = get_doctor(apt["doctor_id"])
    update_ctx(reschedule_apt_id=apt["appointment_id"], doctor_id=apt["doctor_id"], branch_id=apt["branch_id"])
    set_state("RESCHEDULE_CONFIRM_DETAILS")
    return [msg(
        f"Previous appointment details:<br><br>"
        f"👨‍⚕️ <strong>{doctor['name'] if doctor else 'Doctor'}</strong><br>"
        f"📅 Date: {apt['date']}<br>"
        f"⏰ Time: {apt['time']}<br><br>"
        f"Do you want to reschedule this appointment?",
        "confirm", {"options": [{"label": "✅ Yes, Reschedule", "value": "yes"}, {"label": "❌ No", "value": "no"}]}
    )]

def handle_reschedule_confirm_details(user_text, ctx):
    if user_text.lower().strip() not in ["yes", "confirm", "yes, reschedule"]:
        set_state("WELCOME")
        return [msg("Reschedule aborted. Your appointment is unchanged.", "quick_reply", {"options": [{"label": "🏠 Home", "value": "menu"}]})]
    doctor = get_doctor(ctx.get("doctor_id"))
    dates = get_next_available_dates(doctor) if doctor else []
    set_state("RESCHEDULE_DATE")
    return [msg("Please select a new date:", "date_picker", {"dates": dates})]

def handle_reschedule_date(user_text, ctx):
    doctor = get_doctor(ctx.get("doctor_id"))
    dates = get_next_available_dates(doctor) if doctor else []
    m = user_text.strip()
    selected = next((d for d in dates if d.lower() == m.lower()), None)
    if not selected:
        return [msg("Please select a valid date:", "date_picker", {"dates": dates})]
    slots = get_available_slots(doctor, selected)
    if not slots:
        return [msg(f"No slots on {selected}. Choose another date:", "date_picker", {"dates": dates})]
    update_ctx(new_date=selected)
    set_state("RESCHEDULE_TIME")
    return [msg(f"Available slots for <strong>{selected}</strong>:", "time_slots", {"slots": slots, "date": selected})]

def handle_reschedule_time(user_text, ctx):
    doctor = get_doctor(ctx.get("doctor_id"))
    new_date = ctx.get("new_date")
    slots = get_available_slots(doctor, new_date)
    m = user_text.strip()
    selected = next((s for s in slots if s.lower() == m.lower()), None)
    if not selected:
        return [msg("Please select a valid time:", "time_slots", {"slots": slots, "date": new_date})]
    update_ctx(new_time=selected)
    set_state("RESCHEDULE_CONFIRM")
    return [msg(f"Confirm reschedule?<br><br>📅 <strong>New Date:</strong> {new_date}<br>⏰ <strong>New Time:</strong> {selected}",
                "confirm", {"options": [{"label": "✅ Confirm", "value": "yes"}, {"label": "❌ Cancel", "value": "no"}]})]

def handle_reschedule_confirm(user_text, ctx):
    if user_text.lower().strip() not in ["yes", "confirm"]:
        set_state("WELCOME")
        return [msg("Reschedule cancelled.", "quick_reply", {"options": [{"label": "🏠 Home", "value": "menu"}]})]
    apts = load_data("appointments.json")
    apt_id = ctx.get("reschedule_apt_id")
    for apt in apts:
        if apt["appointment_id"] == apt_id:
            release_slot(apt["doctor_id"], apt["date"], apt["time"])
            book_slot(ctx["doctor_id"], ctx["new_date"], ctx["new_time"])
            apt["date"] = ctx["new_date"]
            apt["time"] = ctx["new_time"]
            apt["status"] = "Rescheduled"
            break
    save_data("appointments.json", apts)
    report = build_confirmation_report(next(a for a in apts if a["appointment_id"] == apt_id))
    set_state("WELCOME")
    return [msg("✅ Appointment successfully rescheduled!"), msg("", "appointment_report", {"report": report})]


# ─── Cancel Flow ──────────────────────────────────────────────────────────────

def handle_cancel_enter_id(user_text, ctx):
    apt = get_appointment(user_text.strip().upper())
    if not apt:
        return [msg("❌ Appointment ID not found. Please check and try again.")]
    if apt["status"] == "Cancelled":
        return [msg("This appointment is already cancelled.")]
    doctor = get_doctor(apt["doctor_id"])
    update_ctx(cancel_apt_id=apt["appointment_id"])
    set_state("CANCEL_ENTER_REASON")
    return [msg(
        f"You selected to cancel appointment:<br>"
        f"👨‍⚕️ <strong>{doctor['name'] if doctor else 'Doctor'}</strong><br>"
        f"📅 Date: {apt['date']}<br>"
        f"⏰ Time: {apt['time']}<br><br>"
        f"Please briefly tell us the <strong>reason for cancellation</strong>:"
    )]

def handle_cancel_enter_reason(user_text, ctx):
    update_ctx(cancel_reason=user_text.strip())
    set_state("CANCEL_CONFIRM")
    return [msg(
        "Are you sure you want to cancel the appointment definitively?",
        "confirm",
        {"options": [{"label": "✅ Yes, Cancel", "value": "yes"}, {"label": "🔙 No, Keep It", "value": "no"}]}
    )]

def handle_cancel_confirm(user_text, ctx):
    if user_text.lower().strip() not in ["yes", "confirm"]:
        set_state("WELCOME")
        return [msg("Cancellation aborted. Your appointment is still active 😊", "quick_reply", {
            "options": [{"label": "🏠 Home", "value": "menu"}]
        })]
    apts = load_data("appointments.json")
    apt_id = ctx.get("cancel_apt_id")
    for apt in apts:
        if apt["appointment_id"] == apt_id:
            release_slot(apt["doctor_id"], apt["date"], apt["time"])
            apt["status"] = "Cancelled"
            break
    save_data("appointments.json", apts)
    set_state("WELCOME")
    return [msg("❌ Your appointment has been successfully cancelled.<br>You can book again anytime 😊", "quick_reply", {
        "options": [{"label": "📅 Book New", "value": "book"}, {"label": "🏠 Home", "value": "menu"}]
    })]


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    apts = load_data("appointments.json")
    doctors  = {d["id"]: d for d in load_data("doctors.json")}
    hospitals = {h["id"]: h for h in load_data("hospitals.json")}
    enriched = []
    for apt in apts:
        doc  = doctors.get(apt["doctor_id"], {})
        hosp = hospitals.get(apt["branch_id"], {})
        enriched.append({
            **apt,
            "doctor_name":    doc.get("name", "Unknown"),
            "specialization": doc.get("specialization", ""),
            "rating":         doc.get("rating", ""),
            "hospital_name":  hosp.get("name", "Unknown"),
            "city":           hosp.get("city", ""),
            "state":          hosp.get("state", ""),
            "patient_id":     apt.get("patient_id", "")
        })
    enriched.sort(key=lambda x: x["created_at"], reverse=True)
    return render_template("dashboard.html", appointments=enriched)

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_text = (data.get("message") or "").strip()
    if not user_text:
        return jsonify({"responses": [msg("Please type a message.")]})
    if get_state() == "WELCOME" and not session.get("greeted"):
        session["greeted"] = True
        responses = handle_welcome()
        if user_text.lower() not in ["hi","hello","hey","start","help",""]:
            responses += handle_message(user_text)
    else:
        responses = handle_message(user_text)
    return jsonify({"responses": responses})

@app.route("/api/start")
def start():
    reset_session()
    return jsonify({"responses": handle_welcome()})

@app.route("/api/appointments")
def list_appointments():
    return jsonify(load_data("appointments.json"))

@app.route("/api/appointments/<apt_id>")
def get_appointment_detail(apt_id):
    apt = get_appointment(apt_id)
    if not apt:
        return jsonify({"error": "Not found"}), 404
    return jsonify(build_confirmation_report(apt))

@app.route("/api/sidebar")
def sidebar_data():
    states = load_data("states.json")
    return jsonify({"states": [s["name"] for s in states]})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

