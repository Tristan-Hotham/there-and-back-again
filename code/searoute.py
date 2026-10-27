"""Drawn sea paths: a shortest path over a 0.5-degree ocean grid between two points,
then smoothed by straight great-circle shortcuts that stay at sea.

This only makes the drawn lines plausible (they go round continents rather than over
them). It is not a reconstruction of anyone's track, and every sea path is marked
"drawn" in the data. Land mask: Natural Earth 1:50m countries (public domain).
"""
import os, json, math, heapq
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
NE = "/home/claude/hist/_data3/ne/geojson/ne_50m_admin_0_countries.geojson"
CACHE = os.path.join(ROOT, "work", "seamask_05.npy")
RES = 0.5
NY, NX = int(180 / RES), int(360 / RES)
R = 6371.0088

# narrow straits opened by hand on the grid (pairs of points; every cell on the line is made sea)
STRAITS = [
    ((36.0, -6.2), (35.9, -4.8)),        # Gibraltar
    ((41.25, 29.1), (40.95, 28.95)), ((40.95, 28.95), (40.4, 26.7)), ((40.4, 26.7), (40.0, 26.1)),  # Bosporus, Marmara, Dardanelles
    ((45.4, 36.6), (45.0, 36.5)),        # Kerch
    ((38.25, 15.6), (38.0, 15.65)),      # Messina
    ((12.7, 43.3), (12.4, 43.5)),        # Bab-el-Mandeb
    ((26.6, 56.0), (26.2, 56.8)),        # Hormuz
    ((1.2, 103.6), (1.25, 104.3)), ((2.5, 101.2), (1.2, 103.6)),   # Singapore and Malacca
    ((-5.9, 105.8), (-6.1, 105.6)),      # Sunda
    ((-10.3, 141.5), (-10.6, 142.6)),    # Torres
    ((-52.4, -68.4), (-52.9, -70.5)), ((-52.9, -70.5), (-53.5, -71.0)), ((-53.5, -71.0), (-53.9, -71.5)), ((-53.9, -71.5), (-52.7, -74.2)),  # Magellan
    ((-41.1, 174.3), (-41.3, 174.8)),    # Cook Strait
    ((51.0, 1.4), (51.1, 1.7)),          # Dover
    ((57.9, 10.6), (56.0, 12.7)), ((56.0, 12.7), (55.4, 12.8)),   # Skagerrak and Oresund
    ((10.7, 79.9), (9.3, 79.5)),         # Palk Strait
    ((24.5, 118.5), (25.5, 119.8)),      # Taiwan Strait side
    ((-34.4, 18.5), (-34.9, 19.0)),      # Cape
    ((54.0, -9.0), (55.3, -7.0)),        # north-west Ireland coast
    ((-8.0, 115.6), (-8.6, 115.8)),      # Lombok
]


def _gc(a, b, step_km):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    d = 2 * math.asin(min(1, math.sqrt(h)))
    n = max(1, int(d * R // step_km))
    out = []
    for i in range(n + 1):
        f = i / n
        if d < 1e-9: out.append(a); continue
        A = math.sin((1 - f) * d) / math.sin(d); B = math.sin(f * d) / math.sin(d)
        x = A * math.cos(la1) * math.cos(lo1) + B * math.cos(la2) * math.cos(lo2)
        y = A * math.cos(la1) * math.sin(lo1) + B * math.cos(la2) * math.sin(lo2)
        z = A * math.sin(la1) + B * math.sin(la2)
        out.append((math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))))
    return out


def _cell(la, lo):
    i = min(NY - 1, max(0, int((90 - la) / RES))); j = int(((lo + 180) % 360) / RES) % NX
    return i, j


def _center(i, j):
    return 90 - (i + 0.5) * RES, -180 + (j + 0.5) * RES


def load_mask():
    if os.path.exists(CACHE):
        return np.load(CACHE)
    from shapely.geometry import shape
    from shapely.ops import unary_union
    from shapely.prepared import prep
    import shapely
    land = unary_union([shape(f["geometry"]).buffer(0) for f in json.load(open(NE))["features"]])
    lats = np.array([_center(i, 0)[0] for i in range(NY)]); lons = np.array([_center(0, j)[1] for j in range(NX)])
    LO, LA = np.meshgrid(lons, lats)
    sea = ~shapely.contains_xy(land, LO.ravel(), LA.ravel()).reshape(NY, NX)
    for a, b in STRAITS:
        for p in _gc(a, b, 5):
            sea[_cell(*p)] = True
    np.save(CACHE, sea)
    return sea


SEA = None


def _is_sea(p):
    return SEA[_cell(*p)]


def _snap(p):
    i0, j0 = _cell(*p)
    if SEA[i0, j0]: return (i0, j0)
    for r in range(1, 12):
        best = None
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                if max(abs(di), abs(dj)) != r: continue
                i, j = i0 + di, (j0 + dj) % NX
                if 0 <= i < NY and SEA[i, j]:
                    c = _center(i, j); d = (c[0] - p[0]) ** 2 + ((c[1] - p[1] + 540) % 360 - 180) ** 2
                    if best is None or d < best[0]: best = (d, (i, j))
        if best: return best[1]
    return (i0, j0)


def _astar(s, t):
    def h(c):
        a, b = _center(*c), _center(*t)
        return _hav(a, b)
    openq = [(h(s), 0.0, s)]; g = {s: 0.0}; came = {}
    while openq:
        f, gc, c = heapq.heappop(openq)
        if c == t: break
        if gc > g.get(c, 1e18): continue
        ci, cj = c; cc = _center(ci, cj)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if not di and not dj: continue
                ni, nj = ci + di, (cj + dj) % NX
                if not (0 <= ni < NY) or not SEA[ni, nj]: continue
                ng = gc + _hav(cc, _center(ni, nj))
                if ng < g.get((ni, nj), 1e18):
                    g[(ni, nj)] = ng; came[(ni, nj)] = c; heapq.heappush(openq, (ng + h((ni, nj)), ng, (ni, nj)))
    if t not in g: return None
    path = [t]
    while path[-1] != s: path.append(came[path[-1]])
    return [_center(*c) for c in reversed(path)]


def _hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(min(1, math.sqrt(h)))


def _clear(a, b):
    pts = _gc(a, b, 15)
    return all(_is_sea(p) for p in pts[1:-1] if _hav(p, a) > 40 and _hav(p, b) > 40)


def sea_path(a, b):
    """List of (lat, lon) from a to b at sea, smoothed. Falls back to a great circle."""
    global SEA
    if SEA is None: SEA = load_mask()
    if _clear(a, b): return [a, b]
    s, t = _snap(a), _snap(b)
    path = _astar(s, t)
    if not path: return [a, b]
    nodes = [a] + path + [b]
    out = [nodes[0]]; i = 0
    while i < len(nodes) - 1:
        j = len(nodes) - 1
        while j > i + 1 and not _clear(nodes[i], nodes[j]): j -= 1
        out.append(nodes[j]); i = j
    return out
