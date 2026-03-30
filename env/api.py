from flask import Flask, request, jsonify
from env.environment import MaritimeEnv, Action

app = Flask(__name__)
env = MaritimeEnv()

@app.route("/")
def home():
    return jsonify({"status": "running"})

@app.route("/reset", methods=["POST"])
def reset():
    try:
        state = env.reset()
        return jsonify({"obs": state})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/step", methods=["POST"])
def step():
    try:
        action = request.json.get("action")
        obs, reward, done, info = env.step(Action(**action))
        return jsonify({
            "obs": obs,
            "reward": reward,
            "done": done,
            "info": info
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/state", methods=["GET"])
def state():
    try:
        return jsonify(env.state())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
