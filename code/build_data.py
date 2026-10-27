"""Step 1: resolve every waypoint, draw the routes, measure them, and write the data files.

Inputs (read in place, not copied):
  /home/claude/hist/_data4/wikipedia_journeys_wikitext.json   (English Wikipedia wikitext, CC BY-SA 4.0)
  /home/claude/hist/_data4/wikipedia_journeys_link_coords.json (coordinates of linked articles, via the MediaWiki API)
  /home/claude/hist/_data2/geonames/cities1000.txt            (GeoNames, CC BY 4.0)
Outputs:
  ../data/journeys.csv, ../data/waypoints.csv, ../data/passages.csv, ../data/routes.geojson
  ../work/journeys_full.json (everything, for the next steps)
Run: python3 build_data.py
"""
import os, re, json, math, csv, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
from journeys_spec import J, MIRRORS, PASSAGES, SEA
import searoute

WT = json.load(open("/home/claude/hist/_data4/wikipedia_journeys_wikitext.json"))
LC = json.load(open("/home/claude/hist/_data4/wikipedia_journeys_link_coords.json"))
GN_FILE = "/home/claude/hist/_data2/geonames/cities1000.txt"
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True); os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)

# ---------- GeoNames lookups (only the names we need)
need = set()
for j in J:
    for w in j["wp"]:
        if w[0] != "~" and w[1].startswith("gn:"):
            _, n, cc = w[1].split(":"); need.add((n, cc))
GN = {}
with open(GN_FILE, encoding="utf-8") as f:
    for line in f:
        r = line.rstrip("\n").split("\t")
        alts = set(a.lower() for a in r[3].split(",")) if r[3] else set()
        for (n, cc) in need:
            if r[8] == cc and (r[1].lower() == n.lower() or r[2].lower() == n.lower() or n.lower() in alts):
                pop = int(r[14] or 0); exact = r[1].lower() == n.lower() or r[2].lower() == n.lower()
                key = (n, cc); cand = (exact, pop, r[0], r[1], float(r[4]), float(r[5]))
                if key not in GN or cand[:2] > GN[key][:2]: GN[key] = cand
missing = [k for k in need if k not in GN]
if missing: print("GeoNames missing:", missing); sys.exit(1)


def resolve(key):
    if key.startswith("gn:"):
        _, n, cc = key.split(":"); e = GN[(n, cc)]
        return e[4], e[5], f"GeoNames cities1000 id {e[2]} ({e[3]}, {cc})"
    if key.startswith("txt:"):
        la, lo = map(float, key[4:].split(","))
        return la, lo, "position stated or implied in the article text (see note)"
    if key in LC:
        la, lo = LC[key]; return float(la), float(lo), f"Wikipedia coordinates of the linked article '{key}'"
    raise KeyError(key)


# ---------- article and section checks
def sections(title):
    out = []
    for h in re.findall(r"^=+\s*(.*?)\s*=+\s*$", WT[title]["wt"], re.M):
        h = re.sub(r"\{\{lang\|[^|}]*\|([^}]*)\}\}", r"\1", h).replace("\'\'", "")
        h = re.sub(r"<span[^>]*></span>", "", h)
        out.append(re.sub(r"\s+", " ", h).strip())
    return out


def check_src(src):
    art, _, sec = src.partition("#")
    if art not in WT: return f"article missing: {art}"
    if sec and sec not in sections(art): return f"section missing: {src}"
    return None


# ---------- dates
def parse_date(s):
    """-> (decimal year, precision) where precision in day/month/year/approx"""
    s = s.strip(); approx = s.startswith("c. ")
    if approx: s = s[3:]
    m = re.match(r"^(-?\d+)(?:-(\d\d))?(?:-(\d\d))?$", s)
    y = int(m.group(1)); mo = int(m.group(2)) if m.group(2) else None; d = int(m.group(3)) if m.group(3) else None
    if d: return y + (mo - 1) / 12 + (d - 1) / 365, "day"
    if mo: return y + (mo - 1) / 12 + 0.04, "month"
    return y + 0.5 if not approx else y + 0.5, ("approx" if approx else "year")


def ymd(s):
    y, m, d = map(int, s.split("-")); return y, m, d


def days_between(a, b):
    """Julian-ish day count good enough for spans: proleptic Gregorian via ordinal (years >= 1)."""
    ya, ma, da = ymd(a); yb, mb, db = ymd(b)
    return (date(yb, mb, db) - date(ya, ma, da)).days


# ---------- geometry
R = 6371.0088


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(min(1, math.sqrt(h)))


def gc_points(a, b, step_km=60):
    d = hav(a, b); n = max(1, int(d // step_km))
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    out = []
    if d < 1e-6: return [a, b]
    dd = d / R
    for i in range(n + 1):
        f = i / n
        A = math.sin((1 - f) * dd) / math.sin(dd); B = math.sin(f * dd) / math.sin(dd)
        x = A * math.cos(la1) * math.cos(lo1) + B * math.cos(la2) * math.cos(lo2)
        y = A * math.cos(la1) * math.sin(lo1) + B * math.cos(la2) * math.sin(lo2)
        z = A * math.sin(la1) + B * math.sin(la2)
        out.append((math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))))
    return out


problems = []
full = []
WPROWS, PROWS = [], []
for j in J:
    for src in j["articles"]:
        e = check_src(src)
        if e: problems.append(f"{j['id']}: {e}")
    pts = []  # every point in order: dict
    for w in j["wp"]:
        if w[0] == "~":
            pts.append(dict(name="(drawn routing point)", lat=w[1], lon=w[2], leg=w[3], kind="via", conf="drawn", date=None, src=None, note="", coord_src="drawn by the author to keep the line on a plausible path; not a stop"))
            continue
        name, key, dt, leg, conf, src, note = w
        try:
            la, lo, cs = resolve(key)
        except KeyError:
            problems.append(f"{j['id']}: no coordinates for {key}"); continue
        e = check_src(src)
        if e: problems.append(f"{j['id']} / {name}: {e}")
        pts.append(dict(name=name, lat=la, lon=lo, leg=leg, kind="stop", conf=conf, date=dt, src=src, note=note, coord_src=cs, key=key))
    # which segments are sea paths
    nseg = len(pts) - 1; is_sea = [False] * nseg
    spec = SEA.get(j["id"])

    def find(tok, after=0):
        lab, _, k = tok.partition("~"); lab, _, n = lab.partition("@"); n = int(n or 1)
        hits = [i for i, p in enumerate(pts) if p["name"] == lab and i >= after]
        if len(hits) < n: raise KeyError(f"{j['id']}: sea token {tok}")
        i = hits[n - 1]
        if k:
            vias = [q for q in range(i + 1, len(pts)) if pts[q]["kind"] == "via"]
            if len(vias) < int(k): raise KeyError(f"{j['id']}: sea token {tok} has too few drawn points")
            i = vias[int(k) - 1]
        return i
    if spec == "all": is_sea = [True] * nseg
    elif spec:
        for a_tok, b_tok in spec:
            ia = find(a_tok); ib = find(b_tok, 0 if ("~" in b_tok or "@" in b_tok) else ia + 1)
            if ib <= ia: raise KeyError(f"{j['id']}: empty sea stretch {a_tok} -> {b_tok}")
            for q in range(ia, ib): is_sea[q] = True
    j["_sea"] = is_sea
    # legs: the leg of a segment is the leg of its END point
    legs = {"out": [], "back": []}; seg_km = []; cur = None
    total = {"out": 0.0, "back": 0.0}; known_km = 0.0
    segd = []; segs = []
    for q, (a, b) in enumerate(zip(pts, pts[1:])):
        lg = b["leg"]
        if is_sea[q]:
            nodes = searoute.sea_path((a["lat"], a["lon"]), (b["lat"], b["lon"]))
        else:
            nodes = [(a["lat"], a["lon"]), (b["lat"], b["lon"])]
        line = [nodes[0]]; d = 0.0
        for u, v in zip(nodes, nodes[1:]):
            line.extend(gc_points(u, v)[1:]); d += hav(u, v)
        segd.append(d); segs.append(dict(i=q, sea=is_sea[q], a=a["name"], b=b["name"], line=line))
        total[lg] += d
        if lg != cur:
            legs[lg].append([(a["lat"], a["lon"])]); cur = lg
        legs[lg][-1].extend(line[1:])
        seg_km.append(d)
    # km between known/approximate stops only (no conjectural end, any drawn points in between are fine)
    stops = [p for p in pts if p["kind"] == "stop"]
    # cumulative distance at each point
    cum = [0.0]
    for d in segd: cum.append(cum[-1] + d)
    for i, p in enumerate(pts): p["cum_km"] = cum[i]
    # share of route on segments whose two bounding stops are both known/approximate
    sure = 0.0
    idx = [i for i, p in enumerate(pts) if p["kind"] == "stop"]
    for i1, i2 in zip(idx, idx[1:]):
        if pts[i1]["conf"] != "conjectural" and pts[i2]["conf"] != "conjectural": sure += cum[i2] - cum[i1]
    tot = total["out"] + total["back"]
    y0, p0 = parse_date(j["start"]); y1, p1 = parse_date(j["end"])
    dur = None
    if p0 == "day" and p1 == "day" and not j["start"].startswith("-") and int(j["start"].split("-")[0]) >= 1:
        dur = days_between(j["start"], j["end"])
    elif p0 in ("day", "month") and p1 in ("day", "month"):
        dur = round((y1 - y0) * 365.25)
    end_pt = stops[-1]
    rec = dict({k: v for k, v in j.items() if k != "wp"}, year0=y0, year1=y1, prec0=p0, prec1=p1,
               km_out=round(total["out"]), km_back=round(total["back"]), km_total=round(tot),
               km_sure_share=round(sure / tot, 3) if tot else None, duration_days=dur,
               km_per_day=round(tot / dur, 1) if dur and dur > 0 else None,
               n_stops=len(stops), n_conj=sum(1 for p in stops if p["conf"] == "conjectural"),
               n_known=sum(1 for p in stops if p["conf"] == "known"), n_approx=sum(1 for p in stops if p["conf"] == "approximate"),
               n_via=sum(1 for p in pts if p["kind"] == "via"),
               end_lat=end_pt["lat"], end_lon=end_pt["lon"], end_name=end_pt["name"],
               turn_lat=None, turn_lon=None, points=pts, legs=legs, _segs=segs)
    # turning point = last outward stop
    outs = [p for p in stops if p["leg"] == "out"]
    if outs: rec["turn_lat"], rec["turn_lon"], rec["turn_name"] = outs[-1]["lat"], outs[-1]["lon"], outs[-1]["name"]
    full.append(rec)
    for k, p in enumerate(pts):
        if p["kind"] == "stop":
            WPROWS.append([j["id"], k, p["name"], round(p["lat"], 5), round(p["lon"], 5), p["date"], p["leg"], p["conf"], p["coord_src"], p["src"], p["note"]])
        else:
            WPROWS.append([j["id"], k, p["name"], round(p["lat"], 3), round(p["lon"], 3), "", p["leg"], "drawn", p["coord_src"], "", ""])

byid = {r["id"]: r for r in full}
# passages
for (jid, fa, fb, dep, arr, how, src) in PASSAGES:
    r = byid[jid]; pts = r["points"]
    def occ(lab, after):
        lab, _, n = lab.partition("@"); n = int(n or 1)
        hits = [i for i, p in enumerate(pts) if p["name"] == lab and i > after]
        return hits[n - 1] if len(hits) >= n else None
    ia = occ(fa, -1)
    ib = occ(fb, ia if (ia is not None and "@" not in fb) else -1) if ia is not None else None
    if ia is None or ib is None: problems.append(f"passage {jid}: {fa} -> {fb} not found"); continue
    e = check_src(src)
    if e: problems.append(f"passage {jid}: {e}")
    km = pts[ib]["cum_km"] - pts[ia]["cum_km"]; days = days_between(dep, arr) if int(dep.split("-")[0]) > 0 else None
    PROWS.append(dict(journey=jid, name=r["name"], frm=fa.split("@")[0], to=fb.split("@")[0], depart=dep, arrive=arr, days=days, km=round(km), km_per_day=round(km / days, 1), mode=how, source=src, grade=r["grade"]))

if problems:
    print("PROBLEMS:"); [print(" ", p) for p in problems]; sys.exit(1)

# ---------- write data files
for r in full: r.pop("_sea", None)
SEGS = {r["id"]: r.pop("_segs") for r in full}
cols = ["id", "name", "who", "origin", "region", "mode", "start", "end", "dates_text", "grade", "why", "evidence", "returned", "return_note",
        "km_out", "km_back", "km_total", "km_sure_share", "duration_days", "km_per_day", "stated_km", "stated_km_note", "n_stops", "n_known", "n_approx", "n_conj", "n_via", "articles"]
with open(os.path.join(ROOT, "data", "journeys.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(cols)
    for r in full:
        w.writerow([("; ".join(r[c]) if isinstance(r.get(c), list) else r.get(c, "")) for c in cols])
with open(os.path.join(ROOT, "data", "waypoints.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["journey", "seq", "place", "lat", "lon", "date", "leg", "confidence", "coordinate_source", "wikipedia_source", "note"])
    w.writerows(WPROWS)
with open(os.path.join(ROOT, "data", "passages.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(list(PROWS[0].keys())); [w.writerow(list(p.values())) for p in PROWS]
feats = []
for r in full:
    for lg in ("out", "back"):
        for line in r["legs"][lg]:
            feats.append({"type": "Feature", "properties": {"id": r["id"], "name": r["name"], "leg": lg, "grade": r["grade"], "returned": r["returned"], "note": "great-circle path through the waypoints; drawn, not a recorded track"},
                          "geometry": {"type": "LineString", "coordinates": [[round(lo, 3), round(la, 3)] for la, lo in line]}})
json.dump({"type": "FeatureCollection", "features": feats}, open(os.path.join(ROOT, "data", "routes.geojson"), "w"))
json.dump(dict(journeys=full, passages=PROWS, mirrors=MIRRORS), open(os.path.join(ROOT, "work", "journeys_full.json"), "w"))
json.dump(SEGS, open(os.path.join(ROOT, "work", "segments.json"), "w"))
print(len(full), "journeys,", sum(r["n_stops"] for r in full), "stops,", len(PROWS), "passages")
for r in full: print(f"{r['id']:18s} {r['grade']:9s} {r['returned']:8s} {r['km_total']:7d} km  sure {r['km_sure_share']}  days {r['duration_days']}  kmd {r['km_per_day']}")
