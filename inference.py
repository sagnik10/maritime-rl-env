import requests
import time

URL = "http://127.0.0.1:7860"

def safe_json(r):
    try:
        return r.json()
    except:
        print("RAW RESPONSE:", r.text)
        return {}

def wait():
    for _ in range(10):
        try:
            requests.get(URL + "/state")
            return
        except:
            time.sleep(1)
    raise Exception("Server not running")

def run():
    wait()

    print("Resetting...")
    r = requests.post(URL + "/reset")
    print(safe_json(r))

    for i in range(5):
        r = requests.post(URL + "/step", json={
            "action": {"dx": 1, "dy": 1}
        })
        print(safe_json(r))

if __name__ == "__main__":
    run()
