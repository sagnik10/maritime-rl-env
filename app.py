from flask import Flask, request, jsonify

app = Flask(__name__)

state = {}

@app.route("/")
def home():
    return "Maritime Environment Ready"

@app.route("/reset", methods=["POST"])
def reset():
    global state
    state = {}
    return jsonify({
        "status": "environment reset",
        "state": state
    })

@app.route("/step", methods=["POST"])
def step():
    data = request.json

    action = data.get("action", None)

    response = {
        "observation": "simulated maritime observation",
        "reward": 0,
        "done": False,
        "info": {"action_taken": action}
    }

    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)