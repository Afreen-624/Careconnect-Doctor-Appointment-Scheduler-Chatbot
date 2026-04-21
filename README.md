# 🏥 CareConnect — AI Telemedicine Appointment Scheduler Chatbot

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/Flask-3.0-green?style=for-the-badge&logo=flask" />
  <img src="https://img.shields.io/badge/Sarvam_AI-Powered-purple?style=for-the-badge" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" />
</div>

<br/>

> **CareConnect** is an AI-powered telemedicine chatbot that helps patients book, reschedule, and cancel doctor appointments through a conversational interface — backed by a smart NLP engine and real-time availability management.

---

## 🖥️ Screenshots

| Chat Interface | Patient Dashboard |
|---|---|
| Premium dark glassmorphism UI | Appointment tracker with full details |
| AI-powered conversational booking | Reschedule & Cancel from dashboard |

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🤖 **AI Chatbot** | Sarvam AI NLP + rule-based fallback state machine |
| 🧑‍⚕️ **New & Existing Patients** | Registration + phone-based login with history |
| ⭐ **Doctor Recommendations** | Ranked by rating & specialization matching |
| 🏥 **Multi-City Branches** | 6 branches across Hyderabad, Bangalore, Delhi |
| 🎟️ **Appointment Token** | Unique ID: `APT-YYYY-MM-DD-XXXX` |
| 📋 **Confirmation Report** | Inline report card + QR code for digital check-in |
| 🔄 **Reschedule / Cancel** | Full lifecycle management |
| 📊 **Dashboard** | View and manage all appointments |
| 🧠 **Smart NLP** | "I need a skin doctor tomorrow evening" → Dermatologist booking |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd "Telemedicine Appointment Scheduler Chatbot"
pip3 install -r requirements.txt
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and add your Sarvam AI API key
```

```env
SARVAM_API_KEY=your_sarvam_api_key_here
SECRET_KEY=your-secure-secret-key
```

> **Note:** The chatbot works fully without an API key using rule-based NLP fallback. The Sarvam AI key enables enhanced free-text understanding.

### 3. Run

```bash
python3 app.py
```

Visit: **http://127.0.0.1:5000**

---

## 💬 Sample Conversation Flow

```
Bot:  👋 Hello! Welcome to CareConnect Telemedicine
      📅 Book | 🔄 Reschedule | ❌ Cancel

User: I need a skin doctor tomorrow evening

Bot:  Great! Are you a New or Existing Patient?

User: New Patient

Bot:  Please share: Name, Age, Health Issue

User: Ganesh, 20, skin problem

Bot:  Thanks Ganesh! I recommend a Dermatologist.
      Select your city: Hyderabad | Bangalore | Delhi

User: Hyderabad

Bot:  Branches: CareConnect – Punjagutta | Madhapur

User: Punjagutta

Bot:  [Doctor Cards] Dr. Priya Sharma ⭐4.8 | Dr. Ramesh ⭐4.5
      Or type "recommend" for top pick

User: recommend

Bot:  👉 Dr. Priya Sharma (4.8⭐) — recommended!
      [25 April] [26 April] [27 April]

User: 25 April

Bot:  ⏰ [10:00 AM] [1:30 PM] [5:30 PM]

User: 5:30 PM

Bot:  📋 Booking Summary — Confirm?

User: Yes

Bot:  🎉 Appointment booked!
      🎟️ APT-2026-04-25-4582
      [Full confirmation report with QR code]
```

---

## 🏗️ Architecture

```
Frontend (HTML/CSS/JS)
    ↕ Fetch API
Flask Backend (app.py)
    ├── Conversation State Machine (17 states)
    ├── sarvam_client.py (NLP + Intent Extraction)
    └── JSON Data Layer (doctors, hospitals, patients, appointments)
```

### State Machine

```
WELCOME → IDENTIFY_USER → NEW_PATIENT_INFO / EXISTING_LOGIN
       → BRANCH_SELECTION → DOCTOR_MODE → SHOW_DOCTORS
       → DATE_SELECTION → TIME_SLOT_SELECTION
       → CONFIRM_BOOKING → BOOKING_COMPLETE

WELCOME → RESCHEDULE_ENTER_ID → RESCHEDULE_DATE → RESCHEDULE_TIME → RESCHEDULE_CONFIRM
WELCOME → CANCEL_ENTER_ID → CANCEL_CONFIRM
```

---

## 🗂️ Project Structure

```
├── app.py                  # Flask app + conversation state machine
├── sarvam_client.py        # Sarvam AI API wrapper + NLP fallback
├── data/
│   ├── doctors.json        # 16 doctors across 6 branches
│   ├── hospitals.json      # 6 hospital branches (3 cities)
│   ├── patients.json       # Patient registry
│   └── appointments.json   # Booked appointments
├── static/
│   ├── css/style.css       # Premium dark glassmorphism UI
│   └── js/chat.js          # Interactive chat logic
├── templates/
│   ├── index.html          # Chat interface
│   └── dashboard.html      # Appointment management
├── requirements.txt
├── .env.example
└── README.md
```

---

## 👨‍⚕️ Available Doctors

| City | Specializations |
|---|---|
| Hyderabad | Dermatologist, Cardiologist, Neurologist, Pediatrician, Orthopedist, General Physician |
| Bangalore | Cardiologist, Dermatologist, Orthopedist, Neurologist, General Physician |
| Delhi | Cardiologist, Pediatrician, Dermatologist, General Physician |

---

## 🏥 Hospital Branches

- **Hyderabad:** CareConnect – Punjagutta | CareConnect – Madhapur
- **Bangalore:** CareConnect – Koramangala | CareConnect – Whitefield
- **Delhi:** CareConnect – Connaught Place | CareConnect – Dwarka

---

## 🎟️ Appointment Token System

Every booking generates a unique token:

```
Format:  APT-YYYY-MM-DD-XXXX
Example: APT-2026-04-25-4582
```

Each token stores: Patient · Doctor · Hospital · Date · Time · Status

---

## 🔒 Security

- Session-based state management with secret key
- Input sanitization on all endpoints
- Slot double-booking prevention
- Patient data stored locally (no cloud required)

---

## 🚀 Deployment

| Component | Recommended Platform |
|---|---|
| Frontend + Backend | Render / Railway / Heroku |
| Static Files | Cloudflare |
| Data | Upgrade to MongoDB Atlas for production |

---

## 🛠️ Tech Stack

- **Backend:** Python 3.9+, Flask 3.x
- **AI:** Sarvam AI API (sarvam-m model) + rule-based NLP
- **Frontend:** Vanilla HTML5, CSS3, JavaScript (ES6+)
- **UI:** Dark glassmorphism, Inter font, QR code generation
- **Data:** JSON file store (production: MongoDB/PostgreSQL)

---

## 📈 Future Scope

- [ ] SMS/Email notifications via Twilio
- [ ] Voice input support
- [ ] Multi-language (Hindi, Telugu, English)
- [ ] WhatsApp Bot integration
- [ ] Live queue tracking
- [ ] Insurance authentication
- [ ] Teleconsultation (video call)

---

## 👨‍💻 Developer

Built with ❤️ for hackathon submission — CareConnect Telemedicine System  
Powered by **Sarvam AI** for intelligent Indian healthcare conversations.
