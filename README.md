---
title: Maritime Environment System
emoji: 🌊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Maritime Environment System

## Overview

Maritime Environment System is a dual-layer application combining:

- A visualization layer for real-time maritime monitoring
- An environment layer for simulation and agent interaction

The system models vessel movement, routing behavior, and environmental uncertainty using a continuous state update loop.

---

## Architecture

The project is divided into two independent execution layers:

1. UI Layer (web/)
2. Environment Layer (env/)

Both operate independently but can be integrated through API calls.

---

## Directory Structure

maritime_env/

env/
- environment.py
- api.py
- grader.py
- tasks.py

web/
- app.py
- templates/index.html

services/
- ais.py
- routing.py

inference.py  
requirements.txt  
Dockerfile  
openenv.yaml  

---

## Environment Layer (Core Simulation)

File: env/environment.py

The environment defines the simulation state and transition logic.

### Internal State

The system maintains continuous variables:

- latitude (lat)
- longitude (lon)
- wind intensity
- conflict intensity
- step counter

### Reset Function

reset()

Initializes environment:

- randomizes position
- resets step counter
- returns initial state

State returned:

{
  lat: float,
  lon: float,
  wind: float,
  conflict: float
}

---

### Step Function

step(action)

Action input:

{
  heading: float,
  speed: float
}

State update logic:

lat = lat + cos(heading) * speed  
lon = lon + sin(heading) * speed  

Environmental updates:

wind = random value  
conflict = random value  

Reward calculation:

reward = - (wind * 2 + conflict * 3)

Episode termination:

done = True if step count exceeds threshold

Return:

{
  obs: updated state,
  reward: float,
  done: boolean,
  info: {}
}

---

## API Layer

File: env/api.py

Provides HTTP interface to environment.

### Endpoints

GET /state  
Returns current state

POST /reset  
Resets environment and returns initial state

POST /step  
Takes action and returns next state

---

### Request Flow

1. Client sends action
2. API converts JSON → Action object
3. Environment step() executed
4. Response serialized into JSON

---

## UI Layer

File: web/app.py

Runs Flask + SocketIO server for real-time updates.

### Responsibilities

- Generates ships
- Computes routes
- Fetches environmental data
- Emits updates via WebSocket

---

### Data Pipeline

1. Backend loop generates:
   - ship positions
   - routes
   - weather data
   - conflict events

2. Emits via socket  
   event: "update"

3. Frontend receives and renders:
   - markers
   - polylines
   - stats

---

## Frontend (Visualization)

File: web/templates/index.html

### Components

Map:
- Leaflet-based world map
- restricted zoom bounds

Ships:
- dynamic markers
- continuous movement using interpolation

Routes:
- polylines between coordinates
- animated dash offset for motion effect

Events:
- displayed as alerts
- rendered in panel

Chat:
- sends queries to backend
- receives contextual responses

---

### Animation Logic

Ships do not jump positions.

Instead:

new_position = lerp(current_position, target_position, factor)

This produces smooth motion.

---

## Routing Engine

File: services/routing.py

### Function

build_route(start, end)

Logic:

- divides path into steps
- interpolates latitude and longitude
- returns list of coordinates

Used for drawing routes on map.

---

## AIS Simulation

File: services/ais.py

Ships are simulated as persistent objects.

Each ship has:

- lat
- lon
- velocity components

Update rule:

lat += dlat  
lon += dlon  

This creates continuous movement instead of random jumps.

---

## Inference System

File: inference.py

Acts as a test agent interacting with API.

### Flow

1. Wait for server availability
2. Call /reset
3. Loop:
   - send action
   - receive response
   - accumulate reward

---

### Action Example

{
  heading: float,
  speed: float
}

---

### Output

Each step prints:

{
  obs,
  reward,
  done
}

---

## Data Flow Summary

Environment:

state → step(action) → new state

API:

HTTP request → environment → JSON response

UI:

backend emit → frontend render

---

## Execution Modes

### API Mode

python -m env.api

Provides:

- simulation API
- agent interaction

---

### UI Mode

python -m web.app

Provides:

- visualization
- animation
- interaction

---

## Server Specifications

Development server:

- Flask server
- single-threaded
- port 7860
- host 0.0.0.0

Execution characteristics:

- synchronous request handling
- lightweight simulation loop
- no external database dependency

---

## Testing

### API Test

curl http://127.0.0.1:7860/state

---

### Inference Test

python inference.py

Expected behavior:

- reset returns initial state
- step returns valid JSON
- reward values change dynamically

---

## System Properties

- deterministic structure with stochastic inputs
- continuous spatial simulation
- modular separation of UI and environment
- API-first design
- real-time visualization capability

---

## End