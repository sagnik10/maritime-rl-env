def build_route(start, end):
    lat1, lon1 = start
    lat2, lon2 = end

    steps = 40
    route = []

    for i in range(steps + 1):
        t = i / steps
        lat = lat1 + (lat2 - lat1) * t
        lon = lon1 + (lon2 - lon1) * t
        route.append([lat, lon])

    return route
