from flask import Flask, request, jsonify
from flatlib import const
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

ZODIAC_SIGNS = [
    'ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO',
    'LIBRA', 'SCORPIO', 'SAGITTARIUS', 'CAPRICORN', 'AQUARIUS', 'PISCES'
]

def get_whole_sign_house(planet_sign, asc_sign):
    asc_index = ZODIAC_SIGNS.index(asc_sign.upper())
    planet_index = ZODIAC_SIGNS.index(planet_sign.upper())
    house = (planet_index - asc_index) % 12 + 1
    return house

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
    utc_dt = localized_dt.astimezone(pytz.utc)

    # Format for Flatlib
    date_str = utc_dt.strftime('%Y/%m/%d')
    time_str = utc_dt.strftime('%H:%M')
    flat_dt = Datetime(date_str, time_str, '+00:00')
    pos = GeoPos(lat, lon)

    # Use Placidus for planetary positions (house system won't matter)
    chart = Chart(flat_dt, pos, hsys=const.HOUSES_PLACIDUS)

    # Ascendant
    asc = chart.get(ASC)
    asc_sign = asc.sign
    asc_deg = round(asc.lon % 30, 2)

    results = {
        "ascendant": {
            "degree": asc_deg,
            "sign": asc_sign,
            "house": 1
        },
        "planets": {}
    }

    # Traditional planets and calculated whole sign houses
    for planet in TRADITIONAL_PLANETS:
        obj = chart.get(planet)
        degree = round(obj.lon % 30, 2)
        sign = obj.sign
        house = get_whole_sign_house(sign, asc_sign)

        results["planets"][planet] = {
            "degree": degree,
            "sign": sign,
            "house": house
        }

    # Manual Lot of Spirit calculation (diurnal)
    sun = chart.get(SUN)
    moon = chart.get(MOON)
    asc = chart.get(ASC)
    
    # Convert longitudes to numeric values (0–360°)
    def to360(obj): return obj.lon if obj.lon >= 0 else obj.lon + 360
    
    asc_lon = to360(asc)
    sun_lon = to360(sun)
    moon_lon = to360(moon)
    
    # Lot of Spirit formula for day chart: Asc + Sun - Moon
    spirit_lon = (asc_lon + sun_lon - moon_lon) % 360
    spirit_sign_index = int(spirit_lon // 30)
    spirit_deg = round(spirit_lon % 30, 2)
    spirit_sign = ZODIAC_SIGNS[spirit_sign_index]
    spirit_house = get_whole_sign_house(spirit_sign, asc.sign)
    
    results["lot_of_spirit"] = {
        "degree": spirit_deg,
        "sign": spirit_sign,
        "house": spirit_house
    }

    return jsonify(results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
