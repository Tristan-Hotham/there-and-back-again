"""Shared drawing helpers for the static figures (header, paper, blog, collage):
Equal Earth projection, land polygons and route lines from ../work/site.json.
"""
import os, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
LON0 = 15.0
GRADES = ["Proven", "Probable", "Disputed", "Legend"]
GCOL = {"Proven": "#2A5DA8", "Probable": "#00896A", "Disputed": "#BC6C00", "Legend": "#B3407F"}
FONT_DIR = os.environ.get("FONT_DIR", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts/")


def wrap(lon):
    return (lon - LON0 + 180) % 360 - 180


def ee(lon, lat):
    lam = np.radians(wrap(np.asarray(lon, float))); phi = np.radians(np.asarray(lat, float))
    th = np.arcsin(np.sqrt(3) / 2 * np.sin(phi))
    x = 2 * np.sqrt(3) * lam * np.cos(th) / (3 * (9 * A4 * th ** 8 + 7 * A3 * th ** 6 + 3 * A2 * th ** 2 + A1))
    y = A4 * th ** 9 + A3 * th ** 7 + A2 * th ** 3 + A1 * th
    return x, y


def split_line(coords):
    """coords [[lon,lat],...] -> list of segments that do not jump across the map edge"""
    segs, cur = [], [coords[0]]
    for a, b in zip(coords, coords[1:]):
        if abs(wrap(b[0]) - wrap(a[0])) > 180:
            segs.append(cur); cur = [b]
        else:
            cur.append(b)
    segs.append(cur)
    return [s for s in segs if len(s) > 1]


def load():
    S = json.load(open(os.path.join(ROOT, "work", "site.json")))
    L = json.load(open(os.path.join(ROOT, "work", "land.json")))
    return S, L


def land_rings(L):
    """land polygons as lists of projected rings (split at the map edge)"""
    out = []
    for f in L["features"]:
        for ring in f["geometry"]["coordinates"][:1]:
            for seg in split_line(ring):
                x, y = ee([p[0] for p in seg], [p[1] for p in seg]); out.append(np.column_stack([x, y]))
    return out


def outline():
    lat = np.linspace(-90, 90, 181)
    xl, yl = ee(np.full_like(lat, LON0 - 179.999), lat); xr, yr = ee(np.full_like(lat, LON0 + 179.999), lat[::-1])
    return np.concatenate([xl, xr]), np.concatenate([yl, yr])


def draw_land(ax, L, land="#E9DCBC", coast="#8C7A58", sea="#E6E3D2", lw=0.4, grat="#D6CDB4", zorder=0):
    from matplotlib.patches import Polygon
    ox, oy = outline()
    ax.fill(ox, oy, color=sea, zorder=zorder, lw=0)
    if grat:
        for lo in range(-180, 181, 30):
            lat = np.linspace(-90, 90, 91); x, y = ee(np.full_like(lat, lo + 1e-6), lat); ax.plot(x, y, color=grat, lw=0.4, zorder=zorder + 0.1)
        for la in range(-60, 61, 30):
            lon = np.linspace(LON0 - 179.9, LON0 + 179.9, 361); x, y = ee(lon, np.full_like(lon, la)); ax.plot(x, y, color=grat, lw=0.4, zorder=zorder + 0.1)
    for f in L["features"]:
        ring = f["geometry"]["coordinates"][0]
        lons = np.array([p[0] for p in ring]); lats = np.array([p[1] for p in ring])
        w = wrap(lons)
        if np.ptp(w) > 300:  # polygon straddles the map edge: split into two halves
            for side in (-1, 1):
                ww = np.where(np.sign(w) == side, w, side * 179.999)
                x, y = ee(ww + LON0, lats)
                ax.add_patch(Polygon(np.column_stack([x, y]), closed=True, fc=land, ec=coast, lw=lw, zorder=zorder + 0.2))
        else:
            x, y = ee(lons, lats); ax.add_patch(Polygon(np.column_stack([x, y]), closed=True, fc=land, ec=coast, lw=lw, zorder=zorder + 0.2))
    ax.plot(ox, oy, color=coast, lw=lw * 2, zorder=zorder + 0.3)
    ax.set_aspect("equal"); ax.axis("off")


def draw_routes(ax, J, ids=None, lw=1.1, alpha=0.9, skip_polar=True, zorder=3, back_dash=(0, (3.2, 2.2)), colors=GCOL, markers=True):
    for j in J:
        if ids and j["id"] not in ids: continue
        if skip_polar and j["id"] in ("amundsen", "scott"): continue
        c = colors[j["g"]]
        for leg, ls in (("out", "-"), ("back", back_dash)):
            for line in j[leg]:
                for seg in split_line(line):
                    x, y = ee([p[0] for p in seg], [p[1] for p in seg])
                    ax.plot(x, y, color=c, lw=lw, alpha=alpha, ls=ls, zorder=zorder, solid_capstyle="round")
        if markers:
            ex, ey = ee(j["end"][0], j["end"][1])
            if j["r"] == "never": ax.plot(ex, ey, marker="x", color=c, ms=lw * 4.5, mew=lw * 1.4, zorder=zorder + 1)
            elif j["r"] == "unknown": ax.plot(ex, ey, marker="o", mfc="none", mec=c, ms=lw * 4.5, mew=lw, zorder=zorder + 1)


def fonts():
    from matplotlib import font_manager as fm
    names = {}
    for f, n in [("FrauncesVar.ttf", "disp"), ("IBMPlexMono-Regular.ttf", "mono"), ("IBMPlexMono-Medium.ttf", "monob"), ("SourceSerif4-Regular.ttf", "serif"), ("SourceSerif4-Semibold.ttf", "serifb"), ("SourceSerif4-It.ttf", "serifi")]:
        p = os.path.join(FONT_DIR, f)
        if os.path.exists(p):
            fm.fontManager.addfont(p); names[n] = fm.FontProperties(fname=p)
        else:
            names[n] = fm.FontProperties(family="serif" if "serif" in n or n == "disp" else "monospace")
    return names
