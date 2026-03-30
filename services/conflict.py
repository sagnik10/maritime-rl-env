import random

def get_conflicts():
    zones=[]
    for _ in range(6):
        zones.append({
            "lat":random.uniform(-60,60),
            "lon":random.uniform(-180,180)
        })
    return zones
