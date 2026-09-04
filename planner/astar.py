import heapq
import math
import numpy as np
from planner.ocean_graph import OceanGrid

grid = OceanGrid()

def h(a,b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def current(lat,lon):
    return np.sin(lat/20)*0.5, np.cos(lon/30)*0.5

def cost(a,b):
    base = h(a,b)
    cx,cy = current(a[0],a[1])
    return base - 0.2*(cx+cy)

def astar(start,end):

    start = (round(start[0]), round(start[1]))
    end = (round(end[0]), round(end[1]))

    pq = [(0,start)]
    came = {}
    g = {start:0}

    visited = set()

    while pq:
        _,cur = heapq.heappop(pq)

        if cur in visited:
            continue
        visited.add(cur)

        if cur == end:
            break

        for n in grid.neighbors(cur):

            ng = g[cur] + cost(cur,n)

            if n not in g or ng < g[n]:
                g[n] = ng
                f = ng + h(n,end)
                heapq.heappush(pq,(f,n))
                came[n] = cur

    path = []
    c = end

    if c not in came:
        return [start,end]

    while c in came:
        path.append(c)
        c = came[c]

    path.append(start)
    return path[::-1]
