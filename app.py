from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAQ_PATH = os.path.join(BASE_DIR, "data", "faqs.json")
APPOINTMENT_PATH = os.path.join(BASE_DIR, "data", "appointments.csv")

# Make sure data folder & appointments file exist
if not os.path.exists(os.path.join(BASE_DIR, "data")):
    os.makedirs(os.path.join(BASE_DIR, "data"))

if not os.path.exists(APPOINTMENT_PATH):
    with open(APPOINTMENT_PATH, "w", encoding="utf-8") as f:
        f.write("timestamp,name,date,time,purpose,raw_message\n")


def load_faqs():
    if os.path.exists(FAQ_PATH):
        with open(FAQ_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


FAQs = load_faqs()


def match_faq(user_message: str):
    msg = user_message.lower()
    for faq in FAQs:
        keywords = faq.get("keywords", [])
        if any(kw.lower() in msg for kw in keywords):
            return faq.get("answer")
    return None


def is_greeting(message: str) -> bool:
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
    message = message.lower()
    return any(g in message for g in greetings)


def is_thanks(message: str) -> bool:
    words = ["thank you", "thanks", "thx"]
    message = message.lower()
    return any(w in message for w in words)


def parse_appointment(message: str):
    """
    Example:
    book appointment: 2025-12-03 16:00, Tarun, demo meeting
    """
    if "book appointment" not in message.lower():
        return None

    try:
        parts = message.split(":", 1)
        if len(parts) < 2:
            return None

        details = parts[1].strip()
        segments = [s.strip() for s in details.split(",")]

        if len(segments) < 3:
            return None

        date_time_str = segments[0]          # "2025-12-03 16:00"
        name = segments[1]                   # "Tarun"
        purpose = ", ".join(segments[2:])    # "demo meeting"

        dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
        date_str = dt.date().isoformat()
        time_str = dt.strftime("%H:%M")

        return {
            "name": name,
            "date": date_str,
            "time": time_str,
            "purpose": purpose,
            "date_time_raw": date_time_str,
        }
    except Exception:
        return None


def save_appointment(appt: dict, raw_message: str):
    with open(APPOINTMENT_PATH, "a", encoding="utf-8") as f:
        f.write(
            f"{datetime.now().isoformat()},{appt['name']},{appt['date']},"
            f"{appt['time']},{appt['purpose']},{raw_message.replace(',', ';')}\n"
        )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": "Please type something so I can help you 😊"})

    if is_greeting(user_message):
        return jsonify({
            "reply": (
                "Hello! 👋 I'm your virtual receptionist.\n\n"
                "I can help you with:\n"
                "• Basic information (timings, location, contact)\n"
                "• FAQs\n"
                "• Booking appointments\n\n"
                "You can ask me anything!"
            )
        })

    if is_thanks(user_message):
        return jsonify({"reply": "You're welcome! 😊 Anything else I can help you with?"})

    appt = parse_appointment(user_message)
    if appt:
        save_appointment(appt, user_message)
        return jsonify({
            "reply": (
                f"✅ Appointment booked!\n\n"
                f"Name: {appt['name']}\n"
                f"Date: {appt['date']}\n"
                f"Time: {appt['time']}\n"
                f"Purpose: {appt['purpose']}\n\n"
                "We’ll get back to you with confirmation soon."
            )
        })

    faq_answer = match_faq(user_message)
    if faq_answer:
        return jsonify({"reply": faq_answer})

    default_reply = (
        "I'm not sure I understood that fully 🤔\n\n"
        "You can try:\n"
        "• Ask about: timings, location, courses, fees, contact\n"
        "• Or book appointment like:\n"
        "  book appointment: 2025-12-03 16:00, Your Name, purpose"
    )
    return jsonify({"reply": default_reply})


if __name__ == "__main__":
    app.run(debug=True)
