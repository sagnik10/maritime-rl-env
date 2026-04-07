import requests
import time
import sys

BASE_URL = "http://localhost:7860"

def wait_for_env():
    """Wait for the environment container to become ready."""
    for _ in range(30):  # try for ~30 seconds
        try:
            r = requests.post(f"{BASE_URL}/reset", timeout=5)
            if r.status_code == 200:
                print("Environment ready")
                return True
        except Exception as e:
            print("Waiting for environment...", str(e))

        time.sleep(1)

    print("Environment not reachable")
    return False


def run_episode():
    done = False

    while not done:
        action = {
            "action": {
                "heading": 1.0,
                "speed": 1.0
            }
        }

        try:
            r = requests.post(f"{BASE_URL}/step", json=action, timeout=5)

            if r.status_code != 200:
                print("Step request failed:", r.status_code)
                return

            data = r.json()
            print(data)

            done = data.get("done", True)

        except Exception as e:
            print("Step error:", str(e))
            return


def main():
    try:
        if not wait_for_env():
            sys.exit(0)

        run_episode()

    except Exception as e:
        print("Unexpected error:", str(e))
        sys.exit(0)


if __name__ == "__main__":
    main()