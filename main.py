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

SIGN_RULERS = {
    'ARIES': 'MARS', 'TAURUS': 'VENUS', 'GEMINI': 'MERCURY', 'CANCER': 'MOON',
    'LEO': 'SUN', 'VIRGO': 'MERCURY', 'LIBRA': 'VENUS', 'SCORPIO': 'MARS',
    'SAGITTARIUS': 'JUPITER', 'CAPRICORN': 'SATURN', 'AQUARIUS': 'SATURN', 'PISCES': 'JUPITER'
}

def get_whole_sign_house(planet_sign, asc_sign):
    asc_index = ZODIAC_SIGNS.index(asc_sign.upper())
    planet_index = ZODIAC_SIGNS.index(planet_sign.upper())
    house = (planet_index - asc_index) % 12 + 1
    return house

@app.route("/generate_chart", methods=["POST"])
def generate_chart():
    data = request.json
    birth_date = data.get("date")
    birth_time = data.get("time")
    location = data.get("location")

    if not (birth_date and birth_time and location):
        return jsonify({"error": "Missing required fields"}), 400

    geo = geolocator.geocode(location)
    if not geo:
        return jsonify({"error": "Location not found"}), 400

    lat = geo.latitude
    lon = geo.longitude

    tzname = tf.timezone_at(lat=lat, lng=lon)
    if not tzname:
        return jsonify({"error": "Could not determine timezone"}), 400

    local_tz = pytz.timezone(tzname)
    dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    localized_dt = local_tz.localize(dt)
    utc_dt = localized_dt.astimezone(pytz.utc)

    date_str = utc_dt.strftime('%Y/%m/%d')
    time_str = utc_dt.strftime('%H:%M')
    flat_dt = Datetime(date_str, time_str, '+00:00')
    pos = GeoPos(lat, lon)

    chart = Chart(flat_dt, pos, hsys=const.HOUSES_PLACIDUS)

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

    # Traditional planets with safety checks
    for planet in TRADITIONAL_PLANETS:
        obj = chart.get(planet)
        if obj:
            degree = round(obj.lon % 30, 2)
            sign = obj.sign
            house = get_whole_sign_house(sign, asc_sign)
            results["planets"][planet] = {
                "degree": degree,
                "sign": sign,
                "house": house
            }
        else:
            results["planets"][planet] = {"error": f"{planet} not found"}

    # Helper to normalize longitudes
    def to360(obj): return obj.lon if obj.lon >= 0 else obj.lon + 360

    sun = chart.get(SUN)
    moon = chart.get(MOON)

    if sun and moon:
        asc_lon = to360(asc)
        sun_lon = to360(sun)
        moon_lon = to360(moon)

        # Sect
        is_day = sun_lon > asc_lon and sun_lon < (asc_lon + 180) % 360
        results["sect"] = "day" if is_day else "night"

        # Lot of Spirit
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

        # Lot of Fortune
        fortune_lon = (asc_lon + moon_lon - sun_lon) % 360
        fortune_sign_index = int(fortune_lon // 30)
        fortune_deg = round(fortune_lon % 30, 2)
        fortune_sign = ZODIAC_SIGNS[fortune_sign_index]
        fortune_house = get_whole_sign_house(fortune_sign, asc.sign)

        results["lot_of_fortune"] = {
            "degree": fortune_deg,
            "sign": fortune_sign,
            "house": fortune_house
        }

    else:
        results["sect"] = "error"
        results["lot_of_spirit"] = {"error": "Missing Sun or Moon"}
        results["lot_of_fortune"] = {"error": "Missing Sun or Moon"}

    # Chart Ruler
    ruler_name = SIGN_RULERS.get(asc_sign.upper())
    ruler = chart.get(ruler_name.title())  # Flatlib expects "Mars", not "MARS"
    if ruler:
        ruler_deg = round(ruler.lon % 30, 2)
        ruler_sign = ruler.sign
        ruler_house = get_whole_sign_house(ruler_sign, asc_sign)
    
        results["chart_ruler"] = {
            "planet": ruler_name,
            "degree": ruler_deg,
            "sign": ruler_sign,
            "house": ruler_house
        }
    else:
        results["chart_ruler"] = {"error": f"{ruler_name} not found in chart"}


    return jsonify(results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
