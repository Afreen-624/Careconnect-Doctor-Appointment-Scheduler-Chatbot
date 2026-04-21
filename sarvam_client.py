"""
Sarvam AI API Client for CareConnect Telemedicine Chatbot
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_BASE_URL = "https://api.sarvam.ai"

SPECIALTY_KEYWORDS = {
    "Dermatologist": ["skin", "rash", "acne", "eczema", "dermat", "itching", "pimple", "allergy", "hair fall"],
    "Cardiologist": ["heart", "chest", "cardiac", "blood pressure", "bp", "cardio", "palpitation"],
    "Neurologist": ["brain", "headache", "migraine", "nervous", "neuro", "seizure", "memory", "dizziness"],
    "Orthopedist": ["bone", "joint", "knee", "back", "ortho", "fracture", "spine", "muscle", "shoulder"],
    "Pediatrician": ["child", "baby", "infant", "kid", "pediatric", "fever child", "vaccination"],
    "General Physician": ["fever", "cold", "cough", "flu", "general", "stomach", "vomiting", "weakness", "fatigue"]
}

DATE_KEYWORDS = {
    "today": "25 April",
    "tomorrow": "26 April",
    "day after tomorrow": "27 April",
    "this week": "26 April",
    "next week": "28 April",
    "25 april": "25 April",
    "26 april": "26 April",
    "27 april": "27 April",
    "28 april": "28 April",
    "29 april": "29 April",
    "25th": "25 April",
    "26th": "26 April",
    "27th": "27 April"
}

TIME_KEYWORDS = {
    "morning": "10:00 AM",
    "afternoon": "1:30 PM",
    "evening": "5:30 PM",
    "night": "5:30 PM",
    "10 am": "10:00 AM",
    "10am": "10:00 AM",
    "1 pm": "1:30 PM",
    "5 pm": "5:30 PM",
    "5:30": "5:30 PM",
    "early": "9:00 AM"
}


def extract_intent(user_message: str) -> dict:
    """
    Extract intent from user message using Sarvam AI or fallback to rule-based.
    Returns dict with: intent, specialization, date_hint, time_hint
    """
    msg_lower = user_message.lower().strip()

    # Try Sarvam AI first
    if SARVAM_API_KEY:
        try:
            result = _call_sarvam_intent(user_message)
            if result:
                return result
        except Exception as e:
            print(f"[Sarvam AI] Intent extraction failed: {e}. Using rule-based fallback.")

    # Rule-based fallback
    return _rule_based_intent(msg_lower)


def _call_sarvam_intent(user_message: str) -> dict:
    """Call Sarvam AI chat endpoint to extract intent."""
    system_prompt = """You are an intent extraction system for a telemedicine chatbot.
Extract the following from the user message and return ONLY valid JSON (no markdown, no explanation):
{
  "intent": "book|reschedule|cancel|recommend|greet|unknown",
  "specialization": "Dermatologist|Cardiologist|Neurologist|Orthopedist|Pediatrician|General Physician|null",
  "date_hint": "today|tomorrow|<specific date>|null",
  "time_hint": "morning|afternoon|evening|<specific time>|null"
}"""

    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sarvam-m",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.1,
        "max_tokens": 200
    }

    response = requests.post(
        f"{SARVAM_BASE_URL}/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=10
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()

    # Clean potential markdown wrapping
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    return json.loads(content)


def get_chatbot_response(conversation_history: list, user_message: str) -> str:
    """
    Get a contextual chatbot response from Sarvam AI.
    Falls back to rule-based if API is unavailable.
    """
    if not SARVAM_API_KEY:
        return None

    try:
        system_prompt = """You are CareConnect, a friendly and professional telemedicine chatbot assistant.
You help patients book doctor appointments. Be concise, warm, and helpful.
Use emojis sparingly. Never make up doctor names or appointment IDs.
If the user asks something outside medical booking, politely redirect them."""

        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history[-6:]:  # Last 6 messages for context
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})

        headers = {
            "Authorization": f"Bearer {SARVAM_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "sarvam-m",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 300
        }

        response = requests.post(
            f"{SARVAM_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Sarvam AI] Chat response failed: {e}")
        return None


def _rule_based_intent(msg: str) -> dict:
    """Rule-based intent extraction as fallback."""
    intent = "unknown"
    specialization = None
    date_hint = None
    time_hint = None

    # Intent detection
    if any(word in msg for word in ["book", "appointment", "schedule", "see a doctor", "consult", "want"]):
        intent = "book"
    elif any(word in msg for word in ["reschedule", "change", "modify", "shift", "postpone"]):
        intent = "reschedule"
    elif any(word in msg for word in ["cancel", "delete", "remove"]):
        intent = "cancel"
    elif any(word in msg for word in ["recommend", "suggest", "best", "top"]):
        intent = "recommend"
    elif any(word in msg for word in ["hi", "hello", "hey", "start", "help"]):
        intent = "greet"

    # Specialization detection
    for spec, keywords in SPECIALTY_KEYWORDS.items():
        if any(keyword in msg for keyword in keywords):
            specialization = spec
            if intent == "unknown":
                intent = "book"
            break

    # Date detection
    for keyword, date_value in DATE_KEYWORDS.items():
        if keyword in msg:
            date_hint = date_value
            break

    # Time detection
    for keyword, time_value in TIME_KEYWORDS.items():
        if keyword in msg:
            time_hint = time_value
            break

    return {
        "intent": intent,
        "specialization": specialization,
        "date_hint": date_hint,
        "time_hint": time_hint
    }


def detect_specialization_from_issue(issue: str) -> str:
    """Detect recommended specialization from patient's health issue."""
    issue_lower = issue.lower()
    for spec, keywords in SPECIALTY_KEYWORDS.items():
        if any(keyword in issue_lower for keyword in keywords):
            return spec
    return "General Physician"
