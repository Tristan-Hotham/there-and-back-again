"""Step 4: ../header.png, the 1200 x 630 social card (matplotlib).
Fonts: Fraunces, Source Serif 4 and IBM Plex Mono TTFs from github.com/google/fonts in FONT_DIR
(falls back to system serif and monospace). Run: python3 make_header.py
"""
import os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mapkit as M

S, L = M.load(); F = M.fonts(); R = S["R"]
BG, FG, MUT, HOT = "#F3ECDC", "#231C14", "#6E6352", "#9A3B1E"
fig = plt.figure(figsize=(12, 6.3), dpi=100); fig.patch.set_facecolor(BG)
ax = fig.add_axes([0.40, 0.08, 0.59, 0.84])
M.draw_land(ax, L, grat="#DDD3BB")
M.draw_routes(ax, S["J"], lw=1.25, alpha=0.88)
fig.text(0.04, 0.86, "DATA STUDY  ·  2,500 YEARS OF GREAT JOURNEYS", fontproperties=F["monob"], fontsize=11.5, color=MUT)
fig.text(0.035, 0.80, "There\nand back\nagain", fontproperties=F["disp"], fontsize=56, color=FG, va="top", linespacing=0.95, weight="bold")
fig.text(0.04, 0.37, f"{R['n_journeys']} journeys, each graded\nby the evidence that it happened.", fontproperties=F["serif"], fontsize=17, color=FG, va="top", linespacing=1.3)
y = 0.16
for i, g in enumerate(M.GRADES):
    x = 0.04 + [0, 0.085, 0.18, 0.275][i]
    fig.lines.append(plt.Line2D([x, x + 0.022], [y + 0.012, y + 0.012], color=M.GCOL[g], lw=3.5, transform=fig.transFigure))
    fig.text(x + 0.026, y, f"{g}", fontproperties=F["mono"], fontsize=9.5, color=FG)
fig.text(0.04, 0.045, "Dr Tristan Hotham · Independent researcher", fontproperties=F["mono"], fontsize=10.5, color=MUT)
out = os.path.join(M.ROOT, "header.png"); fig.savefig(out, dpi=100, facecolor=BG); print("header.png written")
