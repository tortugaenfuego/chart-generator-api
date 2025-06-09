from flask import Flask, request, jsonify
from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib.const import SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN, ASC
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pytz
from datetime import datetime

app = Flask(__name__)

tf = TimezoneFinder()
geolocator = Nominatim(user_agent="chart-generator")

TRADITIONAL_PLANETS = [SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN]

@app.route("/generate_chart", methods=["POST"])
def generate_chart():
    data = request.json
    birth_date = data.get("date")       # format: YYYY-MM-DD
    birth_time = data.get("time")       # format: HH:MM (24h)
    location = data.get("location")     # e.g., "Philadelphia, PA"

    if not (birth_date and birth_time and location):
        return jsonify({"error": "Missing required fields"}), 400

    # Geocode location
    geo = geolocator.geocode(location)
    if not geo:
        return jsonify({"error": "Location not found"}), 400

    lat = geo.latitude
    lon = geo.longitude

    # Determine timezone
    tzname = tf.timezone_at(lat=lat, lng=lon)
    if not tzname:
        return jsonify({"error": "Could not determine timezone"}), 400

    local_tz = pytz.timezone(tzname)
    dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    localized_dt = local_tz.localize(dt)

    # Convert to UTC
    utc_dt = localized_dt.astimezone(pytz.utc)
    
    # Flatlib expects 'YYYY/MM/DD'
    date_str = utc_dt.strftime('%Y/%m/%d')
    time_str = utc_dt.strftime('%H:%M')
    
    # Create Flatlib datetime object
    flat_dt = Datetime(date_str, time_str, '+00:00')

    # Clean lat/lon for Flatlib
    lat_str = f"{lat:.4f}"
    lon_str = f"{lon:.4f}"
    
    # Use raw float values
    pos = GeoPos(lat, lon)
    
    # Generate chart
    chart = Chart(flat_dt, pos, hsys='W')  # Whole sign

    # Ascendant
    asc = chart.get(ASC)
    asc_deg = round(asc.lon % 30, 2)
    asc_sign = asc.sign

    results = {
        "ascendant": {
            "degree": asc_deg,
            "sign": asc_sign,
            "house": 1
        },
        "planets": {}
    }

    # Traditional planets
    for planet in TRADITIONAL_PLANETS:
        obj = chart.get(planet)
        degree = round(obj.lon % 30, 2)
        sign = obj.sign
        house = int(obj.house)

        results["planets"][planet] = {
            "degree": degree,
            "sign": sign,
            "house": house
        }

    return jsonify(results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
