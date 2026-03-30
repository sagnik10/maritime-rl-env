SHIPS = [
    {"lat":10,"lon":60,"dlat":0.2,"dlon":0.5,"name":"Vessel-1"},
    {"lat":-5,"lon":80,"dlat":0.15,"dlon":0.4,"name":"Vessel-2"},
    {"lat":20,"lon":30,"dlat":0.1,"dlon":0.3,"name":"Vessel-3"},
    {"lat":-10,"lon":120,"dlat":0.2,"dlon":0.6,"name":"Vessel-4"}
]

def get_ships():
    for s in SHIPS:
        s["lat"] += s["dlat"]
        s["lon"] += s["dlon"]

        if s["lon"] > 180:
            s["lon"] = -180

    return SHIPS
