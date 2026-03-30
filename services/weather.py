import random

def weather_points():
    pts=[]
    for _ in range(20):
        pts.append({
            "lat":random.uniform(-60,60),
            "lon":random.uniform(-180,180),
            "severity":random.random()
        })
    return pts
