from pydantic import BaseModel
import random, math

class Action(BaseModel):
    heading: float
    speed: float

class Observation(BaseModel):
    lat: float
    lon: float
    wind: float
    conflict: float

class MaritimeEnv:

    def __init__(self):
        self.reset()

    def reset(self):
        self.lat = random.uniform(-20,20)
        self.lon = random.uniform(0,100)
        self.steps = 0
        return self.state()

    def state(self):
        return {
            "lat": self.lat,
            "lon": self.lon,
            "wind": random.random(),
            "conflict": random.random()
        }

    def step(self, action: Action):
        self.lat += math.cos(action.heading) * action.speed
        self.lon += math.sin(action.heading) * action.speed

        wind = random.random()
        conflict = random.random()

        reward = - (abs(wind)*2 + abs(conflict)*3)

        self.steps += 1
        done = self.steps > 50

        return {
            "observation": {
                "lat": self.lat,
                "lon": self.lon,
                "wind": wind,
                "conflict": conflict
            },
            "reward": reward,
            "done": done,
            "info": {}
        }
