from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

FAQ_PATH = os.path.join(DATA_DIR, "faqs.json")
APPOINTMENT_PATH = os.path.join(DATA_DIR, "appointments.csv")

# Ensure appointments file exists
if not os.path.exists(APPOINTMENT_PATH):
    with open(APPOINTMENT_PATH, "w", encoding="utf-8") as f:
        f.write("timestamp,name,date,time,purpose,raw_message\n")


def load_faqs():
    if os.path.exists(FAQ_PATH):
        try:
            with open(FAQ_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # corrupted or empty JSON — use empty list but log a warning
            print("Warning: data/faqs.json is not valid JSON. Using empty FAQs.")
            return []
        except Exception as e:
            print(f"Warning: failed to load faqs.json: {e}")
            return []
    return []


FAQs = load_faqs()


def match_faq(user_message: str):
    msg = user_message.lower()
    for faq in FAQs:
        if any(kw.lower() in msg for kw in faq.get("keywords", [])):
            return faq.get("answer")
    return None


def is_greeting(message: str):
    words = ["hi", "hello", "hey", "good morning", "good afternoon"]
    message = message.lower()
    return any(w in message for w in words)


def is_thanks(message: str):
    words = ["thanks", "thank you", "thx"]
    message = message.lower()
    return any(w in message for w in words)


def parse_appointment(message: str):
    if "book appointment" not in message.lower():
        return None

    try:
        parts = message.split(":", 1)
        details = parts[1].strip()
        segments = [s.strip() for s in details.split(",")]

        if len(segments) < 3:
            return None

        dt_str = segments[0]      # "2025-12-03 16:00"
        name = segments[1]
        purpose = ", ".join(segments[2:])

        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")

        return {
            "name": name,
            "date": dt.date().isoformat(),
            "time": dt.strftime("%H:%M"),
            "purpose": purpose
        }

    except:
        return None


def save_appointment(appt, raw_message):
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
    user_message = request.json.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": "Please type something 😊"})

    if is_greeting(user_message):
        return jsonify({"reply":
            "Hello! 👋 I'm your AI Receptionist.\n"
            "Ask me anything or book an appointment!"
        })

    if is_thanks(user_message):
        return jsonify({"reply": "You're welcome! 😊"})

    appt = parse_appointment(user_message)
    if appt:
        save_appointment(appt, user_message)
        return jsonify({"reply":
            f"✅ Appointment booked!\n\n"
            f"Name: {appt['name']}\n"
            f"Date: {appt['date']}\n"
            f"Time: {appt['time']}\n"
            f"Purpose: {appt['purpose']}"
        })

    faq = match_faq(user_message)
    if faq:
        return jsonify({"reply": faq})

    return jsonify({"reply":
        "Sorry, I didn't understand that 🤔\n\n"
        "Try asking about timings, location, contact, or:\n"
        "`book appointment: 2025-12-03 16:00, Your Name, purpose`"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

