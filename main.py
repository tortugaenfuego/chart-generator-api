from flask import Flask, request, jsonify
import pyswisseph as swe
from datetime import datetime
from timezonefinder import TimezoneFinder
import pytz
import requests
from geopy.geocoders import Nominatim

app = Flask(__name__)

# Initialize Swiss Ephemeris path
swe.set_ephe_path(".")  # use current dir for ephemeris files

tf = TimezoneFinder()
geolocator = Nominatim(user_agent="chart-generator")

TRADITIONAL_PLANETS = {
    'Sun': swe.SUN,
    'Moon': swe.MOON,
    'Mercury': swe.MERCURY,
    'Venus': swe.VENUS,
    'Mars': swe.MARS,
    'Jupiter': swe.JUPITER,
    'Saturn': swe.SATURN
}

def get_sign_name(index):
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    return signs[index % 12]

@app.route("/generate_chart", methods=["POST"])
def generate_chart():
    data = request.json
    birth_date = data.get("date")       # format: YYYY-MM-DD
    birth_time = data.get("time")       # format: HH:MM
    location = data.get("location")     # City name

    if not (birth_date and birth_time and location):
        return jsonify({"error": "Missing required fields"}), 400

    # Geocode location
    geo = geolocator.geocode(location)
    if not geo:
        return jsonify({"error": "Location not found"}), 400

    lat = geo.latitude
    lon = geo.longitude

    # Find timezone
    tzname = tf.timezone_at(lat=lat, lng=lon)
    if not tzname:
        return jsonify({"error": "Could not determine timezone"}), 400

    dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    local_tz = pytz.timezone(tzname)
    localized_dt = local_tz.localize(dt)
    utc_dt = localized_dt.astimezone(pytz.utc)

    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day,
                    utc_dt.hour + utc_dt.minute / 60.0)

    # Ascendant and houses
    _, ascmc, _ = swe.houses(jd, lat, lon, b'A')
    asc_deg = ascmc[0]
    asc_sign = int(asc_deg // 30)

    result = {
        "ascendant": {
            "degree": round(asc_deg % 30, 2),
            "sign": get_sign_name(asc_sign),
            "house": 1
        },
        "planets": {}
    }

    for name, pid in TRADITIONAL_PLANETS.items():
        lon_deg, _ = swe.calc_ut(jd, pid)[0:2]
        sign = int(lon_deg // 30)
        deg = round(lon_deg % 30, 2)
        house = ((sign - asc_sign + 12) % 12) + 1

        result["planets"][name] = {
            "degree": deg,
            "sign": get_sign_name(sign),
            "house": house
        }

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
