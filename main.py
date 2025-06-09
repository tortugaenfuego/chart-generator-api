from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

API_KEY = "0VdjDI1u5O57b2oPrdKDQVBHZx1w9YR6j7xyoHKj"
API_BASE_URL = "https://json.freeastrologyapi.com/v1"

@app.route("/generate_chart", methods=["POST"])
def generate_chart():
    data = request.json
    birth_date = data.get("date")       # format: YYYY-MM-DD
    birth_time = data.get("time")       # format: HH:MM (24h)
    location = data.get("location")     # City name (e.g., "Philadelphia, PA")

    # Fixed coordinates for Philadelphia, PA (can upgrade later)
    latitude = 39.9526
    longitude = -75.1652
    timezone = -5

    payload = {
        "date": birth_date,
        "time": birth_time,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "house": "1",       # Whole sign houses
        "ayanamsa": "1"     # Tropical zodiac
    }

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(f"{API_BASE_URL}/planets", json=payload, headers=headers)

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to retrieve chart", "details": response.text}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
