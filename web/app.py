from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import threading, time, random, math
from services.routing import build_route

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

STATE={"ships":[],"routes":[],"events":[],"weather":[]}

LANES=[
(12,72,25,120),
(1,103,25,55),
(30,32,20,72),
(35,-5,40,-70)
]

ships_memory=[]

def haversine(a,b):
    R=6371
    lat1,lon1=map(math.radians,a)
    lat2,lon2=map(math.radians,b)
    dlat=lat2-lat1
    dlon=lon2-lon1
    x=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R*2*math.atan2(math.sqrt(x),math.sqrt(1-x))

def init():
    global ships_memory
    for lane in LANES:
        route=build_route([lane[0],lane[1]],[lane[2],lane[3]])
        ships_memory.append({"route":route,"idx":0})

init()

def generate():

    while True:

        ships=[]
        routes=[]

        for i,lane in enumerate(LANES):

            start=[lane[0],lane[1]]
            end=[lane[2],lane[3]]

            route=build_route(start,end)
            dist=haversine(start,end)

            routes.append({
                "path":route,
                "start":start,
                "end":end,
                "distance":round(dist,1),
                "wind":random.randint(5,30)
            })

            # MOVE SHIP ALONG ROUTE
            mem=ships_memory[i]
            mem["idx"]=(mem["idx"]+1)%len(mem["route"])

            pos=mem["route"][mem["idx"]]

            ships.append({"lat":pos[0],"lon":pos[1]})

        STATE["ships"]=ships
        STATE["routes"]=routes
        STATE["weather"]=["Wind stable","Minor turbulence Indian Ocean"]
        STATE["events"]=["Red Sea tension","South China Sea monitoring"]

        socketio.emit("update",STATE)

        time.sleep(2)

threading.Thread(target=generate,daemon=True).start()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat",methods=["POST"])
def chat():
    q=request.json.get("q","").lower()

    if "@route" in q:
        return jsonify({"response":"Routes optimized over maritime corridors"})
    if "@ships" in q:
        return jsonify({"response":str(len(STATE["ships"]))+" ships active"})
    if "@weather" in q:
        return jsonify({"response":"Weather integrated into routing risk"})

    return jsonify({"response":"Use @route @ships @weather"})

if __name__=="__main__":
    socketio.run(app,host="0.0.0.0",port=7860)
