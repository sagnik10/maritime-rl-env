"""Marlin Ops: simulated fleet, live open environmental and geocoding data."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import math
import random
import threading
import time

import requests
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_socketio import SocketIO

from services.routing import build_route

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "MarlinOps/1.0 local maritime console"})
STATE_LOCK, PORT_LOCK = threading.Lock(), threading.Lock()
LAST_PORT_REQUEST = 0.0
CACHE = {"conditions": {}, "ports": {}, "traffic": {}}

CORRIDORS = [
    {"id":"MRO-241","name":"Arabian Gateway","vessel":"MV Meridian","callsign":"9VMT8","type":"Container","origin":"Mumbai","destination":"Singapore","speed":17.8,"waypoints":[[18.96,72.95],[8.2,76.7],[5.5,82],[5.8,95.2],[1.26,103.84]]},
    {"id":"MRO-317","name":"Red Sea Link","vessel":"Ocean Atlas","callsign":"V7A29","type":"Bulk carrier","origin":"Suez","destination":"Colombo","speed":14.2,"waypoints":[[29.95,32.55],[18.4,39.1],[12.7,43.2],[11.5,52],[6.95,79.84]]},
    {"id":"MRO-508","name":"South China Express","vessel":"Nordic Pearl","callsign":"3EPL6","type":"LNG carrier","origin":"Singapore","destination":"Shanghai","speed":18.6,"waypoints":[[1.26,103.84],[6.2,105.4],[13.2,112.1],[21.5,116.2],[31.23,121.47]]},
    {"id":"MRO-632","name":"North Atlantic","vessel":"Asteria Dawn","callsign":"C6DX4","type":"Ro-Ro","origin":"Gibraltar","destination":"New York","speed":16.4,"waypoints":[[36.14,-5.35],[37.5,-16.5],[39.2,-32],[40.4,-52],[40.68,-74.04]]},
    {"id":"MRO-744","name":"West Africa Run","vessel":"Cape Horizon","callsign":"5BCH2","type":"Tanker","origin":"Cape Town","destination":"Rotterdam","speed":13.7,"waypoints":[[-33.92,18.42],[-15.2,5.1],[2,-5],[17,-17.2],[36,-9],[51.92,4.48]]},
    {"id":"MRO-889","name":"East Africa Feeder","vessel":"Blue Kestrel","callsign":"A8BK7","type":"General cargo","origin":"Dubai","destination":"Mombasa","speed":15.1,"waypoints":[[25.27,55.29],[23.8,58.5],[16,58],[5,52],[-4.04,39.65]]},
]

# Names used to annotate each manually planned maritime corridor.  Live AIS and
# ADS-B contacts are deliberately not assigned these routes.
ROUTE_STOPS = {
    "MRO-241": ["Mumbai", "Arabian Sea", "Colombo Passage", "Malacca Strait", "Singapore"],
    "MRO-317": ["Suez", "Red Sea", "Bab el-Mandeb", "Gulf of Aden", "Colombo"],
    "MRO-508": ["Singapore", "South China Sea", "Luzon Strait", "Taiwan Strait", "Shanghai"],
    "MRO-632": ["Gibraltar", "Azores", "Mid-Atlantic", "Newfoundland Approach", "New York"],
    "MRO-744": ["Cape Town", "Namibian Coast", "Gulf of Guinea", "Dakar Approach", "Bay of Biscay", "Rotterdam"],
    "MRO-889": ["Dubai", "Gulf of Oman", "Arabian Sea", "Somali Basin", "Mombasa"],
}

EVENTS = [
    {"id":"SEC-104","severity":"high","title":"Enhanced watchkeeping advised","zone":"Bab el-Mandeb","detail":"Scenario advisory intersects the Red Sea Link corridor.","lat":12.6,"lon":43.4},
    {"id":"WX-228","severity":"medium","title":"Elevated sea state","zone":"North Atlantic","detail":"Check current Open-Meteo wave data before route decisions.","lat":40,"lon":-36},
    {"id":"OPS-091","severity":"low","title":"Traffic density watch","zone":"Singapore Strait","detail":"Maintain CPA monitoring through the approach lane.","lat":1.2,"lon":103.8},
]

USE_CASES = [
    {"id":"overview","icon":"radar","title":"Fleet overview","prompt":"Give me a fleet overview","description":"Live vessel and voyage health"},
    {"id":"optimize","icon":"route","title":"Route optimization","prompt":"Optimize the selected route","description":"Balance risk, time, and fuel"},
    {"id":"weather","icon":"cloud-sun","title":"Marine weather","prompt":"Check marine weather","description":"Wind, waves, visibility"},
    {"id":"collision","icon":"triangle-alert","title":"Collision screening","prompt":"Screen collision risk","description":"Closest-point risk triage"},
    {"id":"eta","icon":"clock-3","title":"ETA prediction","prompt":"Predict ETA","description":"Progress-adjusted arrival"},
    {"id":"fuel","icon":"fuel","title":"Fuel efficiency","prompt":"Analyze fuel efficiency","description":"Consumption opportunity"},
    {"id":"emissions","icon":"leaf","title":"CO₂ estimate","prompt":"Estimate emissions","description":"Voyage carbon estimate"},
    {"id":"security","icon":"shield-alert","title":"Security exposure","prompt":"Review security exposure","description":"Corridor advisory context"},
    {"id":"ports","icon":"anchor","title":"Port discovery","prompt":"Find a nearby port","description":"OpenStreetMap geocoding"},
    {"id":"incident","icon":"siren","title":"Incident response","prompt":"Create an incident response","description":"Immediate action checklist"},
]

def haversine_nm(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    x = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 3440.065 * 2 * math.atan2(math.sqrt(x), math.sqrt(1-x))

def path_for(points):
    path = []
    for a, b in zip(points, points[1:]):
        part = build_route(a, b)
        path.extend(part if not path else part[1:])
    return path

FLEET = [{"route": path_for(item["waypoints"]), "index": i * 21} for i, item in enumerate(CORRIDORS)]
STATE = {"ships": [], "routes": [], "events": EVENTS, "updated_at": None, "mode": "simulation"}

def refresh_state():
    ships, routes = [], []
    for spec, memory in zip(CORRIDORS, FLEET):
        memory["index"] = (memory["index"] + 1) % len(memory["route"])
        position, progress = memory["route"][memory["index"]], memory["index"] / (len(memory["route"])-1)
        total = sum(haversine_nm(a,b) for a,b in zip(spec["waypoints"],spec["waypoints"][1:]))
        remaining = total * (1-progress)
        risk = 78 if spec["id"] == "MRO-317" and progress < .56 else (48 if spec["id"] in {"MRO-508","MRO-632"} else 24 + int(progress*100)%17)
        status = "At risk" if risk >= 70 else "Watch" if risk >= 45 else "On schedule"
        course = math.degrees(math.atan2(spec["waypoints"][-1][1]-position[1],spec["waypoints"][-1][0]-position[0])) % 360
        ships.append({"id":spec["id"],"name":spec["vessel"],"callsign":spec["callsign"],"type":spec["type"],"lat":round(position[0],5),"lon":round(position[1],5),"speed":spec["speed"],"course":round(course),"progress":round(progress*100),"status":status,"risk":risk})
        fuel = total * (.0062 if spec["type"] == "Container" else .0054)
        routes.append({"id":spec["id"],"name":spec["name"],"vessel":spec["vessel"],"origin":spec["origin"],"destination":spec["destination"],"stops":ROUTE_STOPS[spec["id"]],"path":memory["route"],"waypoints":spec["waypoints"],"start":spec["waypoints"][0],"end":spec["waypoints"][-1],"distance_nm":round(total),"remaining_nm":round(remaining),"eta_hours":round(remaining/spec["speed"],1),"fuel_tonnes":round(fuel,1),"co2_tonnes":round(fuel*3.114,1),"risk":risk,"progress":round(progress*100),"status":status})
    with STATE_LOCK:
        STATE.update(ships=ships, routes=routes, updated_at=datetime.now(timezone.utc).isoformat())

def snapshot():
    with STATE_LOCK: return deepcopy(STATE)

def emitter():
    while True:
        refresh_state(); socketio.emit("update", snapshot()); time.sleep(2)

refresh_state()
threading.Thread(target=emitter, daemon=True).start()

def fallback(lat, lon):
    r = random.Random(int((lat+90)*1000+(lon+180)*100))
    return {"temperature":round(21+r.random()*9,1),"wind_speed":round(6+r.random()*18,1),"wind_direction":r.randrange(360),"wind_gusts":round(12+r.random()*22,1),"visibility_km":round(8+r.random()*22,1),"wave_height":round(.6+r.random()*2.8,1),"wave_direction":r.randrange(360),"wave_period":round(5+r.random()*6,1),"sea_surface_temperature":round(19+r.random()*10,1),"current_velocity":round(.1+r.random()*1.1,1),"source":"Model fallback","sources":[],"is_live":False}

def get_json(url, params):
    response = HTTP.get(url, params=params, timeout=7); response.raise_for_status(); return response.json()

def sample_contacts(items, limit=3500):
    """Keep the browser responsive while preserving an even geographic sample."""
    if len(items) <= limit: return items, False
    stride = len(items) / limit
    return [items[int(index * stride)] for index in range(limit)], True

def traffic_for_view(south, west, north, east):
    """Retrieve real AIS and ADS-B contacts for the requested map viewport.

    Open Waters publishes current AIS GeoJSON without a token. OpenSky publishes
    current aircraft state vectors; both sources are cached briefly to respect
    their public-service limits.
    """
    key = tuple(round(value, 1) for value in (south, west, north, east))
    cached = CACHE["traffic"].get(key)
    if cached and time.time() - cached["at"] < 25: return cached["data"]

    sea_params = {"bbox": f"{south:.4f},{west:.4f},{north:.4f},{east:.4f}"}
    air_params = {"lamin": south, "lomin": west, "lamax": north, "lomax": east}
    sea, air, sea_error, air_error = [], [], None, None
    with ThreadPoolExecutor(max_workers=2) as pool:
        sea_future = pool.submit(get_json, "https://ais.openwaters.io/v1/vessels", sea_params)
        air_future = pool.submit(get_json, "https://opensky-network.org/api/states/all", air_params)
        try:
            raw_sea = sea_future.result()
            for feature in raw_sea.get("features", []):
                coords, props = feature.get("geometry", {}).get("coordinates", []), feature.get("properties", {})
                if len(coords) < 2: continue
                sea.append({"id": f"ais-{props.get('mmsi', feature.get('id'))}", "lat": coords[1], "lon": coords[0], "name": props.get("name") or f"MMSI {props.get('mmsi', 'unknown')}", "speed": props.get("sog"), "course": props.get("cog") or props.get("heading"), "type": props.get("type"), "seen": props.get("seen"), "source": "Open Waters AIS"})
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            sea_error = str(error)
        try:
            raw_air = air_future.result()
            for item in raw_air.get("states") or []:
                if len(item) < 11 or item[5] is None or item[6] is None: continue
                air.append({"id": f"adsb-{item[0]}", "lat": item[6], "lon": item[5], "name": (item[1] or item[0]).strip(), "country": item[2] or "Unknown", "altitude_m": item[13] or item[7], "speed_kn": round((item[9] or 0) * 1.94384, 1), "course": item[10], "on_ground": bool(item[8]), "seen": item[4], "source": "OpenSky ADS-B"})
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            air_error = str(error)

    sea_total, air_total = len(sea), len(air)
    sea, sea_sampled = sample_contacts(sea)
    air, air_sampled = sample_contacts(air)
    data = {"sea": sea, "air": air, "sea_total": sea_total, "air_total": air_total, "sea_sampled": sea_sampled, "air_sampled": air_sampled, "sea_live": sea_error is None, "air_live": air_error is None, "updated_at": datetime.now(timezone.utc).isoformat()}
    CACHE["traffic"][key] = {"at": time.time(), "data": data}
    return data

def conditions(lat, lon):
    key, cached = (round(lat,2),round(lon,2)), CACHE["conditions"].get((round(lat,2),round(lon,2)))
    if cached and time.time()-cached["at"] < 600: return cached["data"]
    data, sources = fallback(lat,lon), []
    weather = {"latitude":lat,"longitude":lon,"current":"temperature_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,visibility,weather_code","wind_speed_unit":"kn","timezone":"UTC"}
    marine = {"latitude":lat,"longitude":lon,"current":"wave_height,wave_direction,wave_period,sea_surface_temperature,ocean_current_velocity","timezone":"UTC"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        wf, mf = pool.submit(get_json,"https://api.open-meteo.com/v1/forecast",weather), pool.submit(get_json,"https://marine-api.open-meteo.com/v1/marine",marine)
        try:
            item = wf.result()["current"]; data.update(temperature=item.get("temperature_2m"),wind_speed=item.get("wind_speed_10m"),wind_direction=item.get("wind_direction_10m"),wind_gusts=item.get("wind_gusts_10m"),visibility_km=round((item.get("visibility") or 0)/1000,1),weather_code=item.get("weather_code")); sources.append("Open-Meteo Weather")
        except (requests.RequestException, KeyError, ValueError): pass
        try:
            item = mf.result()["current"]; data.update(wave_height=item.get("wave_height"),wave_direction=item.get("wave_direction"),wave_period=item.get("wave_period"),sea_surface_temperature=item.get("sea_surface_temperature"),current_velocity=item.get("ocean_current_velocity")); sources.append("Open-Meteo Marine")
        except (requests.RequestException, KeyError, ValueError): pass
    data.update(latitude=round(lat,4),longitude=round(lon,4),source=" + ".join(sources) if sources else "Model fallback",sources=sources,is_live=bool(sources),observed_at=datetime.now(timezone.utc).isoformat())
    CACHE["conditions"][key] = {"at":time.time(),"data":data}; return data

def active_route(route_id):
    routes = snapshot()["routes"]
    return next((x for x in routes if x["id"] == route_id), routes[0])

def intent_for(text):
    text = text.lower()
    for key, words in {"optimize":["optimiz","route","reroute"],"weather":["weather","wind","wave"],"collision":["collision","cpa"],"eta":["eta","arrival"],"fuel":["fuel","burn"],"emissions":["emission","carbon","co2"],"security":["security","piracy","conflict"],"ports":["port","harbour","harbor"],"incident":["incident","emergency"],"overview":["fleet","ship","vessel","overview","status"]}.items():
        if any(word in text for word in words): return key
    return "overview"

def copilot(intent, route):
    low = route["status"].lower(); labels = {
        "overview":("Fleet posture is stable",f"{len(CORRIDORS)} simulated vessels are active. {route['vessel']} is currently {low}.",[f"{len(CORRIDORS)} active","1 priority","2 advisories"]),
        "optimize":(f"Optimization brief · {route['id']}",f"Hold the current corridor and reassess at the next waypoint. {route['remaining_nm']:,} nm remain with risk {route['risk']}/100.",[f"{route['eta_hours']:.1f} h ETA",f"{route['remaining_nm']:,} nm left",f"Risk {route['risk']}/100"]),
        "weather":("Live conditions ready","Select a vessel or click the map to retrieve current wind, visibility, waves, and ocean conditions from Open-Meteo.",["10 min cache","Global models","Point forecast"]),
        "collision":("CPA screening complete",f"No immediate simulated collision alert for {route['vessel']}. Validate all maneuvers against certified bridge systems.",["0 critical","1 watch zone","Demo screening"]),
        "eta":(f"ETA model · {route['vessel']}",f"The current model estimates {route['eta_hours']:.1f} hours to {route['destination']}.",[f"{route['progress']}% complete",f"{route['remaining_nm']:,} nm",f"To {route['destination']}"]),
        "fuel":("Fuel opportunity identified",f"Voyage baseline is {route['fuel_tonnes']:.1f} t. A small speed adjustment on the next low-risk leg may reduce burn.",[f"{route['fuel_tonnes']:.1f} t baseline","Slow-steam option","Validate with vessel data"]),
        "emissions":("Voyage carbon estimate",f"Estimated voyage emissions are {route['co2_tonnes']:.1f} t CO₂ using a 3.114 fuel-to-CO₂ factor.",[f"{route['co2_tonnes']:.1f} t CO₂",f"{route['fuel_tonnes']:.1f} t fuel","Estimate"]),
        "security":("Security exposure reviewed",f"{route['name']} is {low} in this scenario layer. Cross-check official maritime advisories before action.",[f"Risk {route['risk']}/100","3 watch zones","Scenario layer"]),
        "ports":("Port search is available","Use port search above the map to locate a real port through OpenStreetMap, then inspect its live conditions.",["Global coverage","OpenStreetMap","On demand"]),
        "incident":("Immediate response checklist","Acknowledge the alert, establish vessel contact, confirm position, preserve the event log, then escalate through the approved response plan.",["1 Acknowledge","2 Verify","3 Escalate"]),
    }[intent]
    return {"title":labels[0],"response":labels[1],"metrics":labels[2]}

@app.route("/")
def home(): return render_template("index.html", use_cases=USE_CASES)

@app.route("/favicon.ico")
def favicon(): return send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")

@app.route("/api/state")
def api_state(): return jsonify(snapshot())

@app.route("/api/traffic")
def api_traffic():
    try:
        south, west, north, east = [float(value) for value in request.args["bbox"].split(",")]
    except (KeyError, ValueError):
        return jsonify(error="bbox must be south,west,north,east."), 400
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        return jsonify(error="bbox is outside WGS84 bounds."), 400
    return jsonify(traffic_for_view(south, west, north, east))

@app.route("/api/conditions")
def api_conditions():
    try: lat, lon = float(request.args["lat"]), float(request.args["lon"])
    except (KeyError, ValueError): return jsonify(error="Valid latitude and longitude are required."), 400
    if not -90 <= lat <= 90 or not -180 <= lon <= 180: return jsonify(error="Coordinates are outside WGS84 bounds."), 400
    return jsonify(conditions(lat,lon))

@app.route("/api/ports")
def api_ports():
    global LAST_PORT_REQUEST
    query = request.args.get("q", "").strip()[:80]
    if len(query) < 2: return jsonify(results=[], source="OpenStreetMap Nominatim")
    cached = CACHE["ports"].get(query.casefold())
    if cached and time.time()-cached["at"] < 3600: return jsonify(cached["data"])
    try:
        with PORT_LOCK:
            time.sleep(max(0, 1.05-(time.time()-LAST_PORT_REQUEST)))
            raw = get_json("https://nominatim.openstreetmap.org/search", {"q":f"{query} port","format":"jsonv2","addressdetails":1,"limit":6}); LAST_PORT_REQUEST=time.time()
        data = {"results":[{"name":x.get("display_name","Unknown port"),"lat":float(x["lat"]),"lon":float(x["lon"]),"type":x.get("type","place").replace("_"," ").title()} for x in raw if x.get("lat") and x.get("lon")],"source":"OpenStreetMap Nominatim","is_live":True}
        CACHE["ports"][query.casefold()]={"at":time.time(),"data":data}; return jsonify(data)
    except (requests.RequestException, ValueError, KeyError): return jsonify(results=[],source="OpenStreetMap Nominatim",is_live=False,message="Port search is temporarily unavailable.")

@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}; query = str(payload.get("q", ""))[:500]
    intent = str(payload.get("intent") or intent_for(query)); valid = {x["id"] for x in USE_CASES}
    if intent not in valid: intent = intent_for(query)
    route = active_route(str(payload.get("route_id", ""))); answer = copilot(intent,route)
    answer.update(intent=intent,route_id=route["id"],generated_at=datetime.now(timezone.utc).isoformat()); return jsonify(answer)

if __name__ == "__main__": socketio.run(app, host="0.0.0.0", port=7860, allow_unsafe_werkzeug=True)
