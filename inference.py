import requests
import time

base = "http://localhost:7860"

while True:
    try:
        r = requests.post(base + "/reset")
        if r.status_code == 200:
            break
    except:
        pass
    time.sleep(1)

done = False

while not done:
    action = {
        "action": {
            "heading": 1.0,
            "speed": 1.0
        }
    }

    r = requests.post(base + "/step", json=action)
    data = r.json()
    print(data)
    done = data["done"]