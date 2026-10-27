"""Step 3: build ../index.html from page_template.html (and README.md from README_template.md).

Placeholders like {{grade_counts.Proven}} or {{km_total_all|int}} are filled from
../data/results.json. Formats: int, f0, f1, pct0, pct1, words, Words, raw.
The compact page data (../work/site.json) and land (../work/land.json) are embedded.
Run: python3 build_site.py
"""
import os, re, json

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
site = open(os.path.join(ROOT, "work", "site.json")).read()
land = open(os.path.join(ROOT, "work", "land.json")).read()
W = "zero one two three four five six seven eight nine ten eleven twelve".split()


def get(path):
    v = R
    for k in path.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def fmt(v, f):
    if f == "int": return f"{int(round(v)):,}"
    if f == "f0": return f"{v:.0f}"
    if f == "f1": return f"{v:.1f}"
    if f == "pct0": return f"{v * 100:.0f}%"
    if f == "pct1": return f"{v * 100:.1f}%"
    if f in ("words", "Words"):
        s = W[int(v)] if int(v) < len(W) else f"{int(v):,}"
        return s.capitalize() if f == "Words" else s
    return str(v)


def sub(m):
    path, _, f = m.group(1).partition("|")
    return fmt(get(path.strip()), f.strip() or "raw")


t = open(os.path.join(HERE, "page_template.html")).read()
t = re.sub(r"\{\{(.+?)\}\}", sub, t)
t = t.replace("/*DATA*/", "const D = " + site + ";\nconst LAND = " + land + ";")
open(os.path.join(ROOT, "index.html"), "w").write(t)
print("index.html", len(t.encode()) // 1024, "KB")
rt = os.path.join(HERE, "README_template.md")
if os.path.exists(rt):
    open(os.path.join(ROOT, "README.md"), "w").write(re.sub(r"\{\{(.+?)\}\}", sub, open(rt).read()))
    print("README.md written")
