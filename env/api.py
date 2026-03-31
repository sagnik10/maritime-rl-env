from flask import Flask, request, jsonify
from env.environment import MaritimeEnv, Action

app = Flask(__name__)
env = MaritimeEnv()

@app.route("/")
def home():
    return jsonify({"status": "running"})

@app.route("/reset", methods=["POST"])
def reset():
    state = env.reset()
    return jsonify({"obs": state})

@app.route("/step", methods=["POST"])
def step():
    data = request.get_json()
    action = Action(**data["action"])
    obs, reward, done, info = env.step(action)
    return jsonify({
        "obs": obs,
        "reward": reward,
        "done": done,
        "info": info
    })

@app.route("/state", methods=["GET"])
def state():
    return jsonify(env.state())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)