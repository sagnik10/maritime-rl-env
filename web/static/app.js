/* Marlin Ops client: fleet is simulated; conditions and port lookup use open APIs. */
const HOME_VIEW = { center: [18, 42], zoom: 3 };
const state = { data: null, selectedId: null, selectedLive: null, map: null, routes: {}, ships: {}, places: {}, events: [], portMarker: null, riskVisible: false, traffic: { sea: {}, air: {} }, trafficHistory: { sea: {}, air: {} }, courseVectors: { sea: null, air: null }, trafficLayers: { sea: null, air: null, places: null, tracks: null }, layers: { sea: true, air: true, places: true, tracks: true, risk: false }, trafficTimer: null, trafficRequest: null, trafficRequestId: 0, liveProjection: null };
const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#039;","\"":"&quot;"}[char]));

function bootMap() {
  state.map = L.map("map", {
    zoomControl: false, minZoom: 2, maxZoom: 8, worldCopyJump: true, preferCanvas: true,
    zoomSnap: .25, zoomDelta: .5, wheelPxPerZoomLevel: 90, zoomAnimation: true,
    zoomAnimationThreshold: 6, fadeAnimation: false, markerZoomAnimation: false,
    inertia: true, inertiaDeceleration: 2400, inertiaMaxSpeed: 1800, easeLinearity: .22,
    keyboard: true, boxZoom: true, doubleClickZoom: true, touchZoom: true
  }).setView(HOME_VIEW.center, HOME_VIEW.zoom);
  L.control.zoom({ position: "bottomright" }).addTo(state.map);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap contributors" }).addTo(state.map);
  state.trafficLayers.sea = L.layerGroup().addTo(state.map);
  state.trafficLayers.air = L.layerGroup().addTo(state.map);
  state.trafficLayers.places = L.layerGroup().addTo(state.map);
  state.trafficLayers.tracks = L.layerGroup().addTo(state.map);
  state.map.on("click", (event) => showConditions(event.latlng.lat, event.latlng.lng, "Map point"));
  state.map.on("movestart", () => { clearTimeout(state.trafficTimer); });
  state.map.on("moveend", () => { clearTimeout(state.trafficTimer); state.trafficTimer = setTimeout(loadTraffic, 500); });
}

function statusClass(status) { return `status-${String(status).toLowerCase().replaceAll(" ", "-")}`; }
function markerColor(ship) { return ship.risk >= 70 ? "#d5524e" : ship.risk >= 45 ? "#db8b11" : "#0aa49c"; }
function vesselIcon(ship) { return L.divIcon({ className: "", iconSize: [32, 32], iconAnchor: [16, 16], html: `<div class="ship-marker" style="--ship:${markerColor(ship)};--course:${ship.course}deg"><span>▲</span></div>` }); }

function setupRoutes(data) {
  if (Object.keys(state.routes).length) return;
  data.routes.forEach(route => {
    const line = L.polyline(route.path, { color: route.risk >= 70 ? "#d5524e" : "#168f8b", weight: route.risk >= 70 ? 3 : 2, opacity: .68, dashArray: route.risk >= 70 ? "8 8" : null }).addTo(state.map);
    state.routes[route.id] = line;
    state.places[route.id] = [];
    (route.waypoints || [route.start, route.end]).forEach((point, index) => {
      const name = route.stops?.[index] || (index === 0 ? route.origin : index === route.waypoints.length - 1 ? route.destination : "Route waypoint");
      const marker = L.circleMarker(point, { radius: index === 0 || index === route.waypoints.length - 1 ? 5 : 3.5, color: "#fff", weight: 1.5, fillColor: index === 0 ? "#0aa49c" : index === route.waypoints.length - 1 ? "#d5524e" : "#0f7185", fillOpacity: .96 })
        .bindTooltip(`${esc(name)} · ${esc(route.vessel)}`, { permanent: false, direction: "top", offset: [0, -6], className: "place-label" })
        .on("click", () => selectVessel(route.id, true));
      marker.addTo(state.trafficLayers.places);
      state.places[route.id].push(marker);
    });
  });
  state.events = data.events.map(event => L.circleMarker([event.lat, event.lon], { radius: 7, color: "#fff", weight: 2, fillColor: event.severity === "high" ? "#d5524e" : event.severity === "medium" ? "#db8b11" : "#0aa49c", fillOpacity: .95 }).bindTooltip(`${esc(event.zone)} · ${esc(event.title)}`, { direction: "top" }));
}

function setSelectedPlaceLabels(routeId) {
  Object.entries(state.places).forEach(([id, markers]) => markers.forEach(marker => {
    const tooltip = marker.getTooltip();
    if (!tooltip) return;
    const content = tooltip.getContent();
    marker.unbindTooltip().bindTooltip(content, { permanent: id === routeId, direction: "top", offset: [0, -6], className: "place-label" });
  }));
}

function updateMap(data) {
  setupRoutes(data);
  data.ships.forEach(ship => {
    if (!state.ships[ship.id]) {
      state.ships[ship.id] = L.marker([ship.lat, ship.lon], { icon: vesselIcon(ship), keyboard: true, title: ship.name }).addTo(state.map).on("click", () => selectVessel(ship.id, true));
    } else {
      state.ships[ship.id].setLatLng([ship.lat, ship.lon]).setIcon(vesselIcon(ship));
    }
    state.ships[ship.id].bindTooltip(`<strong>${esc(ship.name)}</strong><br>${esc(ship.status)} · ${ship.speed} kn`, { direction: "top", offset: [0, -13] });
  });
}

function trafficStyle(kind, contact) {
  if (kind === "sea") return { radius: 3, color: "#0b817d", weight: 1, fillColor: "#23c5b6", fillOpacity: .72, interactive: true };
  return { radius: contact.on_ground ? 2 : 2.7, color: "#6c48bc", weight: 1, fillColor: "#9a72ec", fillOpacity: .72, interactive: true };
}

function trafficTooltip(kind, contact) {
  if (kind === "sea") return `<strong>${esc(contact.name)}</strong><br>Live AIS · ${contact.speed ?? "—"} kn`;
  const altitude = contact.altitude_m ? `${Math.round(contact.altitude_m * 3.28084).toLocaleString()} ft` : "Altitude unavailable";
  return `<strong>${esc(contact.name)}</strong><br>Live ADS-B · ${altitude} · ${contact.speed_kn ?? "—"} kn`;
}

function projectedPoint(lat, lon, course, distanceNm) {
  const radians = Math.PI / 180; const angularDistance = distanceNm / 3440.065; const bearing = (course || 0) * radians;
  const lat1 = lat * radians; const lon1 = lon * radians;
  const lat2 = Math.asin(Math.sin(lat1) * Math.cos(angularDistance) + Math.cos(lat1) * Math.sin(angularDistance) * Math.cos(bearing));
  const lon2 = lon1 + Math.atan2(Math.sin(bearing) * Math.sin(angularDistance) * Math.cos(lat1), Math.cos(angularDistance) - Math.sin(lat1) * Math.sin(lat2));
  return [lat2 / radians, ((lon2 / radians + 540) % 360) - 180];
}

function projectedTrack(contact, kind, minutes = 18) {
  const speed = Number(kind === "sea" ? contact.speed : contact.speed_kn) || 0;
  return projectedPoint(contact.lat, contact.lon, contact.course, Math.max(1.5, speed * minutes / 60));
}

function rememberContact(kind, contact) {
  const history = state.trafficHistory[kind][contact.id] ||= [];
  const point = [contact.lat, contact.lon]; const last = history.at(-1);
  if (!last || Math.abs(last[0] - point[0]) > .00005 || Math.abs(last[1] - point[1]) > .00005) history.push(point);
  if (history.length > 12) history.splice(0, history.length - 12);
  return history;
}

function renderCourseVectors(kind, contacts) {
  const paths = contacts.map(contact => [[contact.lat, contact.lon], projectedTrack(contact, kind)]);
  const line = state.courseVectors[kind];
  if (line) { line.setLatLngs(paths); return; }
  state.courseVectors[kind] = L.polyline(paths, { color: kind === "sea" ? "#0a8f89" : "#7952c7", weight: 1.1, opacity: .48, dashArray: "3 5", interactive: false, renderer: L.canvas() }).addTo(state.trafficLayers.tracks);
}

function renderRouteInspector() {
  const live = state.selectedLive; const route = selectedRoute();
  if (live) {
    const contact = live.contact; const speed = live.kind === "sea" ? contact.speed : contact.speed_kn; const distance = Math.max(2, Number(speed || 0) * .5);
    $("#route-kind").textContent = "Live course projection"; $("#route-title").textContent = contact.name || "Live contact";
    const history = state.trafficHistory[live.kind][contact.id] || [];
    $("#route-description").textContent = `Observed ${history.length > 1 ? `${history.length}-point track` : "live position"} plus a 30-minute course projection. It is not a filed voyage or flight plan.`;
    $("#route-stops").innerHTML = `<span class="route-stop live-stop">Observed track</span><i></i><span class="route-stop">Current position</span><i></i><span class="route-stop">Projected ${Math.round(distance)} nm</span>`;
    $("#route-summary").innerHTML = `<span>${speed ?? "—"} ${live.kind === "sea" ? "kn" : "kn"}</span><span>${Math.round(contact.course ?? 0)}° course</span><span>${contact.source}</span>`;
    const end = projectedPoint(contact.lat, contact.lon, contact.course, distance);
    if (state.liveProjection) state.map.removeLayer(state.liveProjection);
    state.liveProjection = L.polyline([...history, [contact.lat, contact.lon], end], { color: live.kind === "sea" ? "#0aa49c" : "#7047ba", weight: 3.5, dashArray: "6 7", opacity: .95 }).addTo(state.map);
    return;
  }
  if (!route) return;
  $("#route-kind").textContent = "Managed planned route"; $("#route-title").textContent = `${route.origin} to ${route.destination}`;
  $("#route-description").textContent = `${route.vessel} · named route places are shown on the map.`;
  $("#route-stops").innerHTML = (route.stops || [route.origin, route.destination]).map((place, index, all) => `<span class="route-stop ${index === 0 || index === all.length - 1 ? "terminal-stop" : ""}">${esc(place)}</span>${index < all.length - 1 ? "<i></i>" : ""}`).join("");
  $("#route-summary").innerHTML = `<span>${route.distance_nm.toLocaleString()} nm</span><span>${route.eta_hours}h ETA</span><span>Risk ${route.risk}/100</span>`;
  if (state.liveProjection) { state.map.removeLayer(state.liveProjection); state.liveProjection = null; }
}

function selectLiveContact(kind, contact) {
  state.selectedLive = { kind, contact }; setSelectedPlaceLabels(null); renderVessel(); renderRouteInspector();
  state.map.flyTo([contact.lat, contact.lon], Math.max(state.map.getZoom(), 5), { duration: .55 });
  showConditions(contact.lat, contact.lon, contact.name || "Live contact");
}

function syncTraffic(kind, contacts) {
  const markers = state.traffic[kind]; const seen = new Set(); const layer = state.trafficLayers[kind];
  contacts.forEach(contact => {
    seen.add(contact.id);
    rememberContact(kind, contact);
    if (!markers[contact.id]) {
      markers[contact.id] = L.circleMarker([contact.lat, contact.lon], trafficStyle(kind, contact)).bindTooltip(trafficTooltip(kind, contact), { direction: "top", offset: [0, -4] }).on("click", () => selectLiveContact(kind, contact)).addTo(layer);
    } else {
      markers[contact.id].setLatLng([contact.lat, contact.lon]).setStyle(trafficStyle(kind, contact)).setTooltipContent(trafficTooltip(kind, contact));
    }
    markers[contact.id]._marlinMisses = 0;
  });
  // Public feeds are sampled and can briefly omit a contact during a pan/zoom.
  // Keep a contact through two accepted snapshots so markers do not blink.
  Object.keys(markers).forEach(id => {
    if (seen.has(id)) return;
    markers[id]._marlinMisses = (markers[id]._marlinMisses || 0) + 1;
    if (markers[id]._marlinMisses >= 3) { layer.removeLayer(markers[id]); delete markers[id]; }
  });
}

function trafficLabel(total, sampled, label) { return sampled ? `${total.toLocaleString()} ${label} · density sampled` : `${total.toLocaleString()} ${label}`; }

function renderTraffic(payload) {
  // Never clear an already-visible layer because one upstream public API timed out.
  if (payload.sea_live) { syncTraffic("sea", payload.sea || []); renderCourseVectors("sea", payload.sea || []); }
  if (payload.air_live) { syncTraffic("air", payload.air || []); renderCourseVectors("air", payload.air || []); }
  $("#sea-status").innerHTML = `<i data-lucide="waves"></i> ${payload.sea_live ? "AIS live" : "AIS unavailable"}`;
  $("#air-status").innerHTML = `<i data-lucide="plane"></i> ${payload.air_live ? "ADS-B live" : "ADS-B unavailable"}`;
  $("#traffic-readout").textContent = `${trafficLabel(payload.sea_total || 0, payload.sea_sampled, "AIS vessels")} · ${trafficLabel(payload.air_total || 0, payload.air_sampled, "aircraft")} in this view`;
  lucide.createIcons();
}

async function loadTraffic() {
  if (!state.map) return;
  const bounds = state.map.getBounds();
  const bbox = [bounds.getSouth(), bounds.getWest(), bounds.getNorth(), bounds.getEast()].map(value => value.toFixed(3)).join(",");
  const requestId = ++state.trafficRequestId;
  if (state.trafficRequest) state.trafficRequest.abort();
  const controller = new AbortController(); state.trafficRequest = controller;
  try {
    const response = await fetch(`/api/traffic?bbox=${encodeURIComponent(bbox)}`, { signal: controller.signal });
    if (!response.ok) throw new Error("Traffic request failed");
    const payload = await response.json();
    // A response for an older viewport must not replace markers in the newer view.
    if (requestId !== state.trafficRequestId) return;
    renderTraffic(payload);
  } catch (error) {
    if (error.name === "AbortError") return;
    $("#traffic-readout").textContent = `Live traffic is temporarily unavailable (${error.message}). The voyage simulation remains active.`;
  } finally {
    if (requestId === state.trafficRequestId) state.trafficRequest = null;
  }
}

function renderVoyages(data) {
  const list = $("#voyage-list");
  list.innerHTML = data.routes.map(route => `<button class="voyage ${route.id === state.selectedId ? "selected" : ""}" data-id="${route.id}"><div class="voyage-top"><span>${esc(route.vessel)}</span><span class="${statusClass(route.status)}">${esc(route.status)}</span></div><p>${esc(route.origin)} → ${esc(route.destination)} · ${route.eta_hours}h</p><div class="progress-track"><i style="width:${route.progress}%"></i></div></button>`).join("");
  list.querySelectorAll(".voyage").forEach(button => button.addEventListener("click", () => selectVessel(button.dataset.id, true)));
  $("#fleet-count").textContent = data.ships.length;
}

function renderAdvisories(events) {
  $("#advisory-count").textContent = events.length;
  $("#advisory-list").innerHTML = events.map(event => `<article class="advisory"><i class="sev-${esc(event.severity)}"></i><div><h3>${esc(event.title)}</h3><p>${esc(event.zone)} · ${esc(event.detail)}</p></div></article>`).join("");
}

function selected() { return state.data?.ships.find(ship => ship.id === state.selectedId); }
function selectedRoute() { return state.data?.routes.find(route => route.id === state.selectedId); }

function renderVessel() {
  if (state.selectedLive) {
    const { kind, contact } = state.selectedLive; const speed = kind === "sea" ? contact.speed : contact.speed_kn;
    $("#vessel-name").textContent = contact.name || "Live contact";
    $("#vessel-meta").textContent = `${kind === "sea" ? "Live AIS vessel" : "Live ADS-B aircraft"} · ${contact.source}`;
    $("#metric-speed").textContent = speed ?? "—";
    $("#metric-course").textContent = contact.course == null ? "—" : String(Math.round(contact.course)).padStart(3, "0");
    $("#metric-progress").textContent = kind === "air" && contact.altitude_m ? Math.round(contact.altitude_m * 3.28084).toLocaleString() : "LIVE";
    $("#vessel-icon").style.background = kind === "sea" ? "#d7f5f0" : "#eee8ff";
    return;
  }
  const ship = selected();
  if (!ship) return;
  $("#vessel-name").textContent = ship.name;
  $("#vessel-meta").textContent = `${ship.type} · ${ship.callsign} · ${ship.status}`;
  $("#metric-speed").textContent = ship.speed;
  $("#metric-course").textContent = String(ship.course).padStart(3, "0");
  $("#metric-progress").textContent = ship.progress;
  $("#vessel-icon").style.background = ship.risk >= 70 ? "#fee8e5" : ship.risk >= 45 ? "#fff0d6" : "#d7f5f0";
}

function selectVessel(id, requestConditions) {
  state.selectedId = id; state.selectedLive = null;
  setSelectedPlaceLabels(id);
  renderVessel(); renderVoyages(state.data); renderRouteInspector();
  const ship = selected();
  if (!ship) return;
  Object.entries(state.routes).forEach(([routeId, line]) => line.setStyle({ weight: routeId === id ? 4 : 2, opacity: routeId === id ? .95 : .35 }));
  if (requestConditions) { state.map.flyTo([ship.lat, ship.lon], Math.max(state.map.getZoom(), 4), { duration: .65 }); showConditions(ship.lat, ship.lon, ship.name); }
}

async function showConditions(lat, lon, label) {
  const badge = $("#conditions-badge");
  badge.textContent = "Updating…"; $("#conditions-location").textContent = `${label} · ${lat.toFixed(2)}, ${lon.toFixed(2)}`;
  try {
    const response = await fetch(`/api/conditions?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`);
    if (!response.ok) throw new Error("Conditions request failed");
    const item = await response.json();
    const values = [["WIND", `${item.wind_speed ?? "—"} kn`], ["WAVES", `${item.wave_height ?? "—"} m`], ["VISIBILITY", `${item.visibility_km ?? "—"} km`], ["SEA TEMP", `${item.sea_surface_temperature ?? "—"} °C`]];
    $("#conditions-grid").classList.remove("empty-state");
    $("#conditions-grid").innerHTML = values.map(([key, value]) => `<div class="condition"><span>${key}</span><strong>${esc(value)}</strong></div>`).join("");
    badge.textContent = item.is_live ? "LIVE OPEN DATA" : "MODEL FALLBACK";
    $("#conditions-source").textContent = `${item.source} · refreshed ${new Date(item.observed_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  } catch (_) { badge.textContent = "UNAVAILABLE"; $("#conditions-grid").innerHTML = "<span>Conditions are temporarily unavailable. Try again shortly.</span>"; }
}

function renderCopilot(answer) {
  const result = $("#copilot-result"); result.hidden = false;
  result.innerHTML = `<h3>${esc(answer.title)}</h3><p>${esc(answer.response)}</p><div class="copilot-metrics">${answer.metrics.map(metric => `<span>${esc(metric)}</span>`).join("")}</div>`;
}

async function askCopilot(intent, question) {
  const result = $("#copilot-result"); result.hidden = false; result.innerHTML = "<p>Preparing an operations brief…</p>";
  try {
    const response = await fetch("/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ intent, q: question, route_id: state.selectedId }) });
    if (!response.ok) throw new Error("Copilot request failed"); renderCopilot(await response.json());
  } catch (_) { result.innerHTML = "<p>The operations brief could not be generated. Please retry.</p>"; }
}

async function searchPorts(query) {
  const box = $("#port-results"); box.hidden = false; box.innerHTML = "<div class='search-result'><span>Searching OpenStreetMap…</span></div>";
  try {
    const response = await fetch(`/api/ports?q=${encodeURIComponent(query)}`); const payload = await response.json();
    if (!payload.results?.length) { box.innerHTML = `<div class="search-result"><span>${esc(payload.message || "No port found. Try a city or port name.")}</span></div>`; return; }
    box.innerHTML = "";
    payload.results.forEach(item => {
      const button = document.createElement("button"); button.className = "search-result"; button.innerHTML = `<strong>${esc(item.name.split(",")[0])}</strong><span>${esc(item.type)} · OpenStreetMap</span>`;
      button.addEventListener("click", () => { box.hidden = true; $("#port-search").value = item.name.split(",")[0]; if (state.portMarker) state.map.removeLayer(state.portMarker); state.portMarker = L.marker([item.lat,item.lon]).addTo(state.map).bindTooltip("Port search result", {permanent:false}).openTooltip(); state.map.flyTo([item.lat,item.lon], 7); showConditions(item.lat,item.lon,item.name.split(",")[0]); }); box.appendChild(button);
    });
  } catch (_) { box.innerHTML = "<div class='search-result'><span>Port search is unavailable. Please retry.</span></div>"; }
}

function bindUi() {
  $("#focus-vessel").addEventListener("click", () => { const ship = selected(); if (ship) selectVessel(ship.id, true); });
  $("#reset-map").addEventListener("click", () => state.map.flyTo(HOME_VIEW.center, HOME_VIEW.zoom, { duration: .55 }));
  document.addEventListener("keydown", event => {
    if (event.key === "Home" && !["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)) {
      event.preventDefault(); state.map.flyTo(HOME_VIEW.center, HOME_VIEW.zoom, { duration: .55 });
    }
  });
  document.querySelectorAll(".use-case").forEach(button => button.addEventListener("click", () => askCopilot(button.dataset.intent, button.dataset.prompt)));
  $("#copilot-form").addEventListener("submit", event => { event.preventDefault(); const input = $("#copilot-input"); const value = input.value.trim(); if (value) { askCopilot(null, value); input.value = ""; } });
  $("#port-search").addEventListener("keydown", event => { if (event.key === "Enter") { event.preventDefault(); const value = event.target.value.trim(); if (value) searchPorts(value); } if (event.key === "Escape") $("#port-results").hidden = true; });
  document.querySelectorAll(".map-action[data-layer]").forEach(button => button.addEventListener("click", () => {
    const kind = button.dataset.layer; state.layers[kind] = !state.layers[kind]; button.classList.toggle("active", state.layers[kind]); button.setAttribute("aria-pressed", String(state.layers[kind]));
    if (kind === "risk") state.events.forEach(marker => state.layers.risk ? marker.addTo(state.map) : state.map.removeLayer(marker));
    else if (state.layers[kind]) state.trafficLayers[kind].addTo(state.map); else state.map.removeLayer(state.trafficLayers[kind]);
  }));
}

function updateClock() { $("#utc-clock").textContent = new Date().toLocaleTimeString("en-GB", { hour:"2-digit", minute:"2-digit", timeZone:"UTC" }) + " UTC"; }
function receive(data) {
  const needsInitialConditions = !state.selectedId;
  state.data = data;
  if (!state.selectedId) state.selectedId = data.ships[0]?.id;
  updateMap(data); setSelectedPlaceLabels(state.selectedId); renderVoyages(data); renderAdvisories(data.events); renderVessel(); renderRouteInspector();
  if (needsInitialConditions && selected()) showConditions(selected().lat, selected().lon, selected().name);
}

async function start() {
  lucide.createIcons(); bootMap(); bindUi(); updateClock(); setInterval(updateClock, 1000);
  try { const response = await fetch("/api/state"); receive(await response.json()); } catch (_) { $("#connection-state").textContent = "OFFLINE"; }
  loadTraffic();
  const socket = io(); socket.on("update", receive); socket.on("connect", () => { $("#connection-state").innerHTML = "<i></i> CONNECTED"; }); socket.on("disconnect", () => { $("#connection-state").textContent = "RECONNECTING"; });
}
start();
