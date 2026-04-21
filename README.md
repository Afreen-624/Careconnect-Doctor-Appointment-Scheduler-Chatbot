# 🏥 CareConnect — AI Telemedicine Appointment Scheduler Chatbot

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/Flask-3.0-green?style=for-the-badge&logo=flask" />
  <img src="https://img.shields.io/badge/Deployed-Railway-purple?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Project-INT428-orange?style=for-the-badge" />
</div>

<br/>

> **CareConnect** is an AI-powered telemedicine chatbot that enables patients to **book, reschedule, and cancel doctor appointments** through a conversational interface, powered by NLP and a rule-based state machine.

---

## 🚀 Live Deployment

🌐 **Live App:**  
`https://your-app-name.up.railway.app`

> Hosted on Railway with Gunicorn production server

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🤖 AI Chatbot | Conversational appointment booking system |
| 🧑‍⚕️ Patient Management | New & existing patient handling |
| 🏥 Multi-City Support | Hospitals across multiple cities |
| 📅 Smart Scheduling | Doctor availability & slot booking |
| 🔄 Reschedule | Modify appointment easily |
| ❌ Cancel | Cancel with reason tracking |
| 📊 Dashboard | View all appointments |
| 🎟️ Token System | Unique appointment ID generation |

---

## 🏗️ Architecture
Frontend (HTML/CSS/JS)
↓
Flask Backend (app.py)
↓
State Machine + NLP Layer
↓
JSON Data Storage

---


## ⚙️ Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Server:** Gunicorn (Production)
- **Deployment:** Railway
- **Data Storage:** JSON files

---

## 📦 Project Structure
├── app.py
├── sarvam_client.py
├── data/
│ ├── doctors.json
│ ├── hospitals.json
│ ├── patients.json
│ └── appointments.json
├── static/
├── templates/
├── requirements.txt
├── Procfile
└── README.md


---

## ▶️ Run Locally

### 1. Clone repo
```bash
git clone <your-repo-url>
cd Careconnect-Doctor-Appointment-Scheduler-Chatbot

### 2. Install dependencies
pip install -r requirements.txt

### 3. Create .env
SECRET_KEY=your_secret_key
SARVAM_API_KEY=your_api_key (optional)

### 4. Run
python app.py

👉 Open: http://127.0.0.1:5000

## 🚀 Deployment (Railway)

### Step 1: Push to GitHub
```bash
git add .
git commit -m "deployment ready"
git push

Step 2: Create Railway Project
Go to Railway dashboard
Click New Project
Select Deploy from GitHub Repo
Choose your repository
Step 3: Add Environment Variables

Go to Variables tab and add:

SECRET_KEY=your_secret_key
SARVAM_API_KEY=your_api_key (optional)

Step 4: Add Procfile

Ensure your project has a file named Procfile in root directory:

web: gunicorn app:app
Step 5: Install Dependencies

Ensure requirements.txt includes:

flask>=3.0.0
requests>=2.31.0
python-dotenv>=1.0.0
gunicorn>=21.2.0

Step 6: Deploy
Railway will automatically build and deploy your app
Wait for deployment to complete
Step 7: Generate Public URL
Go to Settings → Domains
Click Generate Domain

👉 Your app will be live at:

https://your-app-name.up.railway.app

Academic Submission

📘 Course: INT 428
🏫 Project: AI Telemedicine Appointment Scheduler Chatbot
👩‍💻 Developed by: Afee

