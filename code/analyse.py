"""Step 2: every number used in the page, paper, blog and collage -> ../data/results.json,
plus the compact page data -> ../work/site.json and a simplified land layer -> ../work/land.json.
Run: python3 analyse.py   (after build_data.py)
"""
import os, json, math, statistics as st
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
D = json.load(open(os.path.join(ROOT, "work", "journeys_full.json")))
JS, PS, MIR = D["journeys"], D["passages"], D["mirrors"]
GR = ["Proven", "Probable", "Disputed", "Legend"]
RET = ["returned", "some", "never", "unknown"]
ERAS = [("Antiquity", -1e9, 500, "before AD 500"), ("Middle Ages", 500, 1450, "500 to 1449"),
        ("Age of sail", 1450, 1800, "1450 to 1799"), ("Modern", 1800, 1e9, "1800 onwards")]


def era(y):
    for n, a, b, _ in ERAS:
        if a <= y < b: return n


for j in JS:
    j["era"] = era(j["year0"])

R = {}
R["n_journeys"] = len(JS)
R["year_first"] = min(j["year0"] for j in JS); R["year_last"] = max(j["year1"] for j in JS)
R["span_years"] = round(R["year_last"] - R["year_first"])
R["grade_counts"] = {g: sum(j["grade"] == g for j in JS) for g in GR}
R["return_counts"] = {r: sum(j["returned"] == r for j in JS) for r in RET}
R["eras"] = [dict(name=n, label=l, n=sum(j["era"] == n for j in JS), grades={g: sum(j["era"] == n and j["grade"] == g for j in JS) for g in GR}) for n, a, b, l in ERAS]
for e in R["eras"]:
    e["proven_share"] = round(e["grades"]["Proven"] / e["n"], 3) if e["n"] else None
pre = [j for j in JS if j["year0"] < 1450]; post = [j for j in JS if j["year0"] >= 1450]
R["pre1450"] = dict(n=len(pre), proven=sum(j["grade"] == "Proven" for j in pre), legend=sum(j["grade"] == "Legend" for j in pre))
R["post1450"] = dict(n=len(post), proven=sum(j["grade"] == "Proven" for j in post))
R["grade_by_return"] = {g: {r: sum(j["grade"] == g and j["returned"] == r for j in JS) for r in RET} for g in GR}
R["origin_regions"] = Counter(j["origin"] for j in JS).most_common()

# waypoints
stops = [p for j in JS for p in j["points"] if p["kind"] == "stop"]
R["n_stops"] = len(stops); R["n_drawn_points"] = sum(j["n_via"] for j in JS)
R["stop_conf"] = {c: sum(p["conf"] == c for p in stops) for c in ("known", "approximate", "conjectural")}
R["stop_conf_by_grade"] = {g: {c: sum(p["conf"] == c for j in JS if j["grade"] == g for p in j["points"] if p["kind"] == "stop") for c in ("known", "approximate", "conjectural")} for g in GR}
for g in GR:
    t = sum(R["stop_conf_by_grade"][g].values()); R["stop_conf_by_grade"][g]["share_conjectural"] = round(R["stop_conf_by_grade"][g]["conjectural"] / t, 3)
srcs = Counter()
for p in stops:
    cs = p["coord_src"]
    srcs["wikipedia" if cs.startswith("Wikipedia") else "geonames" if cs.startswith("GeoNames") else "text"] += 1
R["coord_sources"] = dict(srcs)
R["articles_used"] = sorted(set(s.split("#")[0] for j in JS for s in j["articles"]) | set(p["src"].split("#")[0] for j in JS for p in j["points"] if p["kind"] == "stop"))
R["n_articles_used"] = len(R["articles_used"])

# distances
R["km_total_all"] = sum(j["km_total"] for j in JS)
by_km = sorted(JS, key=lambda j: -j["km_total"])
R["longest"] = [dict(id=j["id"], name=j["name"], km=j["km_total"]) for j in by_km[:5]]
R["shortest"] = [dict(id=j["id"], name=j["name"], km=j["km_total"]) for j in by_km[-3:]]
R["km_median"] = round(st.median(j["km_total"] for j in JS))
R["km_by_grade_median"] = {g: round(st.median(j["km_total"] for j in JS if j["grade"] == g)) for g in GR}
R["sure_share_by_grade"] = {g: round(st.mean(j["km_sure_share"] for j in JS if j["grade"] == g), 3) for g in GR}
R["stated_vs_drawn"] = []
for j in JS:
    if not j.get("stated_km"): continue
    drawn, basis, comparable = j["km_total"], "whole drawn route", True
    if j["id"] == "carpine":
        drawn, basis = next(p for p in PS if p["journey"] == "carpine")["km"], "drawn route from Batu's camp to Sira Orda"
    elif j["id"] == "burke_wills":
        drawn, basis = j["km_out"], "drawn outward route only"
    elif j["id"] == "ibn_fadlan":
        basis = "drawn route, Baghdad to Bolghar"
    elif j["id"] == "ibn_battuta":
        comparable, basis = False, "my route covers only the 1325 to 1349 circuit, not his later trips to Spain and Mali"
    R["stated_vs_drawn"].append(dict(id=j["id"], name=j["name"], stated=j["stated_km"], note=j.get("stated_km_note", ""), drawn=drawn, basis=basis, comparable=comparable,
                                     ratio=round(drawn / j["stated_km"], 2)))
cmp_ = [x for x in R["stated_vs_drawn"] if x["comparable"]]
R["stated_vs_drawn_n"] = len(cmp_)
R["stated_vs_drawn_ratio_range"] = [min(x["ratio"] for x in cmp_), max(x["ratio"] for x in cmp_)]
cp = next(p for p in PS if p["journey"] == "carpine")
R["carpine_check"] = dict(stated_km=round(3000 * 1.609344), drawn_km=cp["km"], days=cp["days"])
bw = next(p for p in PS if p["journey"] == "burke_wills" and p["to"] == "Menindee")
R["burke_menindee_check"] = dict(stated_km=750, drawn_km=bw["km"], days=bw["days"])

# whole-trip pace (stops included) where both ends are dated to the day or month
pace = [j for j in JS if j["km_per_day"] and j["id"] != "laperouse"]
R["pace"] = sorted([dict(id=j["id"], name=j["name"], km=j["km_total"], days=j["duration_days"], kmd=j["km_per_day"], mode=j["mode"], grade=j["grade"]) for j in pace], key=lambda x: -x["kmd"])
R["n_pace"] = len(pace)

# dated passages
R["passages"] = PS
R["n_passages"] = len(PS)
modes = defaultdict(list)
for p in PS: modes[p["mode"]].append(p["km_per_day"])
R["passage_modes"] = {m: dict(n=len(v), median=round(st.median(v), 1), min=min(v), max=max(v)) for m, v in modes.items()}
fast = max(PS, key=lambda p: p["km_per_day"]); slow = min(PS, key=lambda p: p["km_per_day"])
R["fastest_passage"] = fast; R["slowest_passage"] = slow
sail = [p for p in PS if p["mode"] == "Sailing ship"]
R["sail_median_kmd"] = round(st.median(p["km_per_day"] for p in sail), 1)
dg = [p for p in PS if p["journey"] == "da_gama"]
R["da_gama_out_back"] = dict(out_days=dg[0]["days"], back_days=dg[1]["days"], out_kmd=dg[0]["km_per_day"], back_kmd=dg[1]["km_per_day"])
am = [p for p in PS if p["journey"] == "amundsen"]; sc = [p for p in PS if p["journey"] == "scott"]
R["pole"] = dict(amundsen_out_kmd=am[0]["km_per_day"], amundsen_back_kmd=am[1]["km_per_day"], amundsen_out_days=am[0]["days"], amundsen_back_days=am[1]["days"],
                 scott_out_kmd=sc[0]["km_per_day"], scott_back_kmd=sc[1]["km_per_day"], scott_out_days=sc[0]["days"], scott_back_days=sc[1]["days"],
                 amundsen_km=next(j for j in JS if j["id"] == "amundsen")["km_total"], scott_km_out=next(j for j in JS if j["id"] == "scott")["km_out"],
                 scott_km_back=next(j for j in JS if j["id"] == "scott")["km_back"])
R["never_returned"] = [dict(id=j["id"], name=j["name"]) for j in JS if j["returned"] == "never"]
R["unknown_return"] = [dict(id=j["id"], name=j["name"]) for j in JS if j["returned"] == "unknown"]
R["mirrors"] = [dict(a=a, b=b, text=t) for a, b, t in MIR]
R["n_mirrors"] = len(MIR)
R["grade_share"] = {g: round(R["grade_counts"][g] / len(JS), 3) for g in GR}
R["proven_or_probable"] = R["grade_counts"]["Proven"] + R["grade_counts"]["Probable"]
R["disputed_or_legend"] = R["grade_counts"]["Disputed"] + R["grade_counts"]["Legend"]
R["legend_never_or_unknown"] = sum(j["grade"] == "Legend" and j["returned"] in ("never", "unknown") for j in JS)
R["polar"] = dict(days_apart=34)
json.dump(R, open(os.path.join(ROOT, "data", "results.json"), "w"), indent=1, ensure_ascii=False)


# ---------- compact page data
def rnd(line, tol=0.12):
    # light Douglas-Peucker in degrees, then round
    if len(line) < 3: return [[round(p[1], 2), round(p[0], 2)] for p in line]
    un = [list(line[0])]
    for p in line[1:]:
        lo = p[1]
        while lo - un[-1][1] > 180: lo -= 360
        while lo - un[-1][1] < -180: lo += 360
        un.append([p[0], lo])
    line = un
    keep = [0, len(line) - 1]; stack = [(0, len(line) - 1)]
    while stack:
        a, b = stack.pop(); A, B = line[a], line[b]; best, bi = 0, None
        for i in range(a + 1, b):
            P = line[i]; dx, dy = B[1] - A[1], B[0] - A[0]
            L2 = dx * dx + dy * dy
            t = 0 if L2 == 0 else max(0, min(1, ((P[1] - A[1]) * dx + (P[0] - A[0]) * dy) / L2))
            d = math.hypot(P[1] - (A[1] + t * dx), P[0] - (A[0] + t * dy))
            if d > best: best, bi = d, i
        if best > tol: keep.append(bi); stack += [(a, bi), (bi, b)]
    keep = sorted(set(keep))
    # keep enough points that long great circles still curve on the projection
    out = []
    for k0, k1 in zip(keep, keep[1:]):
        out.append(line[k0]); step = max(1, (k1 - k0) // 6) if k1 - k0 > 12 else None
        if step:
            for i in range(k0 + step, k1, step): out.append(line[i])
    out.append(line[keep[-1]])
    return [[round((p[1] + 180) % 360 - 180, 2), round(p[0], 2)] for p in out]


site = []
for j in JS:
    site.append(dict(id=j["id"], n=j["name"], who=j["who"], o=j["origin"], rg=j["region"], m=j["mode"], g=j["grade"], why=j["why"], ev=j["evidence"],
                     r=j["returned"], rn=j["return_note"], dt=j["dates_text"], y0=round(j["year0"], 2), y1=round(j["year1"], 2), era=j["era"],
                     km=j["km_total"], ko=j["km_out"], kb=j["km_back"], ss=j["km_sure_share"], d=j["duration_days"], kmd=j["km_per_day"] if j["id"] != "laperouse" else None,
                     sk=j.get("stated_km"), skn=j.get("stated_km_note", ""), art=j["articles"], urls=j.get("extra_urls", []),
                     out=[rnd(l) for l in j["legs"]["out"]], back=[rnd(l) for l in j["legs"]["back"]],
                     wp=[[p["name"], round(p["lat"], 3), round(p["lon"], 3), p["date"], p["leg"][0], p["conf"][0], p["src"], p["note"], p["coord_src"]] for p in j["points"] if p["kind"] == "stop"],
                     end=[round(j["end_lon"], 2), round(j["end_lat"], 2)], nv=j["n_via"]))
json.dump(dict(J=site, P=PS, M=MIR, R=R), open(os.path.join(ROOT, "work", "site.json"), "w"), separators=(",", ":"), ensure_ascii=False)

# simplified land for the page and figures
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
L = json.load(open("/home/claude/hist/_data3/ne/geojson/ne_50m_admin_0_countries.geojson"))
land = unary_union([shape(f["geometry"]).buffer(0) for f in L["features"]]).simplify(0.12, preserve_topology=True)
from shapely.geometry.polygon import orient
geoms = [orient(g, sign=-1.0) for g in getattr(land, "geoms", [land]) if g.area > 0.25]


def rr(c):
    if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)): return [round(c[0], 2), round(c[1], 2)]
    return [rr(x) for x in c]


json.dump({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": rr(mapping(g)["coordinates"])}} for g in geoms]},
          open(os.path.join(ROOT, "work", "land.json"), "w"), separators=(",", ":"))
print("results.json:", len(json.dumps(R)) // 1024, "KB; site.json", os.path.getsize(os.path.join(ROOT, "work", "site.json")) // 1024, "KB; land.json", os.path.getsize(os.path.join(ROOT, "work", "land.json")) // 1024, "KB")
print(json.dumps({k: R[k] for k in ["grade_counts", "return_counts", "pre1450", "post1450", "stop_conf", "km_total_all", "sail_median_kmd", "passage_modes", "da_gama_out_back", "pole", "sure_share_by_grade"]}, indent=0))
