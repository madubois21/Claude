#!/usr/bin/env python3
"""Génère index.html et compositions/s1..s6.html.

La géométrie (toit en projection oblique, champ de panneaux, raccords de zoom)
est calculée ici pour que les raccords entre scènes tombent au pixel près.
Relancer ce script ÉCRASE les fichiers HTML : faites vos retouches ici, ou
retouchez les HTML et ne relancez plus le script.

    python3 tools/build.py
"""
import html
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INK = "#111111"
ACC = "#FF5700"
GREY = "#6B6B70"
LIGHT = "#D4D4D8"
PANEL = "#F3F3F4"
CELL = "#D4D4D8"
TH_PANEL = "#FFF1E8"
TH_PANEL_B = "#FFEADF"
TH_CELL = "#FFC9AE"

W, H = 1920, 1080


def n(x):
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def pts(points):
    return " ".join(f"{n(x)},{n(y)}" for x, y in points)


def attr_json(obj):
    return html.escape(json.dumps(obj, ensure_ascii=False), quote=True)


# --------------------------------------------------------------------------
# Shared CSS / JS
# --------------------------------------------------------------------------
BASE_CSS = """
    @font-face { font-family: "Comfortaa"; src: url("assets/fonts/comfortaa-var.woff2") format("woff2"); font-weight: 300 700; font-style: normal; }
    #root { position: absolute; inset: 0; overflow: hidden; font-family: "Comfortaa", sans-serif; color: #111111; }
    #root svg.world { position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; overflow: visible; }
    #root svg.zoom * { vector-effect: non-scaling-stroke; }
    #root .d { stroke-dasharray: 1 1.2; }
    #root .title { position: absolute; font-weight: 700; font-size: 64px; line-height: 1.12; letter-spacing: -0.01em; color: #111111; white-space: nowrap; }
    #root .w { display: inline-block; }
    #root .acc { color: #FF5700; }
    #root .label { position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 32px; line-height: 1.2; color: #6B6B70; white-space: nowrap; }
"""

BASE_JS = """
      const R = document.querySelector('[data-composition-id="__ID__"]') || document;
      const $ = (s) => R.querySelector(s);
      const $$ = (s) => Array.from(R.querySelectorAll(s));
      let V = {};
      try {
        V = (window.__hyperframes && window.__hyperframes.getVariables && window.__hyperframes.getVariables()) || {};
      } catch (e) {}
      const txt = (id, d) => (typeof V[id] === "string" && V[id].trim().length ? V[id] : d);
      // "a b|c *d*." -> word spans; "|" = line break, *x* = accent colour
      function words(el, text) {
        el.textContent = "";
        const out = [];
        let inAcc = false;
        text.split("|").forEach((line, li) => {
          if (li) el.appendChild(document.createElement("br"));
          line.trim().split(/\\s+/).forEach((w, i) => {
            if (i) el.appendChild(document.createTextNode(" "));
            const s = document.createElement("span");
            s.className = "w";
            if (w.startsWith("*")) { inAcc = true; w = w.slice(1); }
            const m = w.match(/^(.*?)\\*([^\\s*]*)$/);
            const core = m ? m[1] : w, tail = m ? m[2] : "";
            if (inAcc) {
              const a = document.createElement("span");
              a.className = "acc";
              a.textContent = core;
              s.appendChild(a);
            } else {
              s.textContent = core;
            }
            if (tail) s.appendChild(document.createTextNode(tail));
            if (m) inAcc = false;
            el.appendChild(s);
            out.push(s);
          });
        });
        return out;
      }
      const tl = gsap.timeline({ paused: true });
      const draw = (t, els, d = 0.8, ease = "power2.inOut", stagger = 0) =>
        tl.fromTo(els, { attr: { "stroke-dashoffset": 1.05 } }, { attr: { "stroke-dashoffset": 0 }, duration: d, ease, stagger }, t);
      const undraw = (t, els, d = 0.5, ease = "power3.in", stagger = 0) =>
        tl.to(els, { attr: { "stroke-dashoffset": -1.15 }, duration: d, ease, stagger }, t);
      const solid = (t, els) => tl.set(els, { strokeDasharray: "none" }, t);
      const blurIn = (t, els, d = 0.15, stagger = 0.067, px = 6) =>
        tl.fromTo(els, { opacity: 0, filter: "blur(" + px + "px)" }, { opacity: 1, filter: "blur(0px)", duration: d, ease: "power2.out", stagger }, t);
      const blurOut = (t, els, d = 0.18, stagger = 0.03, px = 8) =>
        tl.to(els, { opacity: 0, filter: "blur(" + px + "px)", duration: d, ease: "power2.in", stagger }, t);
      const fadeIn = (t, els, d = 0.4, stagger = 0, ease = "power1.out") =>
        tl.fromTo(els, { opacity: 0 }, { opacity: 1, duration: d, ease, stagger }, t);
      const fadeOut = (t, els, d = 0.3, stagger = 0, ease = "power1.in") =>
        tl.to(els, { opacity: 0, duration: d, ease, stagger }, t);
"""


def write_scene(sid, title, variables, css, body, js):
    body = body.replace('class="d', 'stroke-dashoffset="1.05" class="d')
    doc = f"""<template>
  <!-- {title} -->
  <style>{BASE_CSS}{css}
  </style>
  <div
    id="root"
    data-composition-id="{sid}"
    data-width="{W}"
    data-height="{H}"
    data-composition-variables="{attr_json(variables)}"
  >
{body}
  </div>
  <script>
    (function () {{{BASE_JS.replace("__ID__", sid)}{js}
      window.__timelines["{sid}"] = tl;
    }})();
  </script>
</template>
"""
    path = os.path.join(ROOT, "compositions", f"{sid}.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print("wrote", os.path.relpath(path, ROOT))


def svar(vid, label, default):
    return {"id": vid, "type": "string", "label": label, "default": default}


# --------------------------------------------------------------------------
# Solar field geometry (S3 world), shared by S3, S4, S5
# --------------------------------------------------------------------------
PW, PH = 210, 160  # panel
GX, GY = 12, 28  # gaps
COLS, ROWS = 7, 3
FX0, FY0 = 230, 412  # field origin
CC, CR = 6, 4  # cells per panel
HERO = (1, 4)  # (row, col) zoomed panel

# anomalies in panel-local coords at S3 scale
ANOM = {
    (0, 1): [("spot", 87.5, 60)],
    (1, 4): [("spot", 52.5, 60), ("cell", 105, 80), ("conn", 192.5, 120)],
    (2, 5): [("cell", 35, 80), ("cell", 35, 120)],
    (0, 6): [("spot", 157.5, 20)],
}


def panel_xy(r, c):
    return FX0 + c * (PW + GX), FY0 + r * (PH + GY)


HX, HY = panel_xy(*HERO)  # 1118, 600
K = 960 / PW  # S4 scale
S4X, S4Y = 120, 230  # hero panel position in S4 world


def to_s4(x, y):
    return (x - HX) * K + S4X, (y - HY) * K + S4Y


def cell_lines(x, y, w, h):
    d = []
    for i in range(1, CC):
        xx = x + w * i / CC
        d.append(f"M{n(xx)} {n(y)}V{n(y + h)}")
    for j in range(1, CR):
        yy = y + h * j / CR
        d.append(f"M{n(x)} {n(yy)}H{n(x + w)}")
    return "".join(d)


def busbars(x, y, w, h):
    cw = w / CC
    d = []
    for i in range(CC):
        for b in (0.28, 0.5, 0.72):
            xx = x + cw * (i + b)
            d.append(f"M{n(xx)} {n(y + 6)}V{n(y + h - 6)}")
    return "".join(d)


def anomalies_svg(r, c, ox, oy, s, prefix, hero_ids=False):
    """Thermal anomalies of panel (r,c) drawn at origin (ox,oy) and scale s."""
    out = []
    for i, (kind, ax, ay) in enumerate(ANOM.get((r, c), [])):
        x, y = ox + ax * s, oy + ay * s
        idattr = f' id="{prefix}-a{i}"' if hero_ids else ""
        if kind == "spot":
            out.append(
                f'<g{idattr} class="{prefix}-anom" data-x="{n(x)}">'
                f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(22 * s)}" fill="url(#{prefix}-hot)"/>'
                f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(5 * s)}" fill="{ACC}"/></g>'
            )
        elif kind == "cell":
            out.append(
                f'<rect{idattr} class="{prefix}-anom" data-x="{n(x)}" x="{n(x)}" y="{n(y)}" width="{n(35 * s)}" '
                f'height="{n(40 * s)}" fill="url(#{prefix}-warm)"/>'
            )
        elif kind == "conn":
            out.append(
                f'<g{idattr} class="{prefix}-anom" data-x="{n(x)}">'
                f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(13 * s)}" ry="{n(5 * s)}" fill="url(#{prefix}-hot)"/>'
                f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(5 * s)}" ry="{n(2 * s)}" fill="{ACC}"/></g>'
            )
    return "".join(out)


def thermal_defs(prefix):
    return (
        f'<radialGradient id="{prefix}-hot">'
        f'<stop offset="0" stop-color="{ACC}" stop-opacity="1"/>'
        f'<stop offset="0.3" stop-color="{ACC}" stop-opacity="0.9"/>'
        f'<stop offset="0.62" stop-color="#FF7A33" stop-opacity="0.42"/>'
        f'<stop offset="1" stop-color="#FF9A66" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="{prefix}-warm">'
        f'<stop offset="0" stop-color="{ACC}" stop-opacity="0.62"/>'
        f'<stop offset="1" stop-color="{ACC}" stop-opacity="0.26"/></radialGradient>'
    )


def th_fill(r, c):
    return TH_PANEL if (r + c) % 2 == 0 else TH_PANEL_B


# hero panel in S4 world (used by S4 and S5 so the hand-off is exact)
S4PW, S4PH = PW * K, PH * K  # 960 x 731.43
MARKS = [  # detection circles (cx, cy, r) in S4 world + label y
    (S4X + 52.5 * K, S4Y + 60 * K, 110),
    (S4X + 122.5 * K, S4Y + 100 * K, 135),
    (S4X + 192.5 * K, S4Y + 120 * K, 80),
]


def hero_panel_svg(prefix, with_ids=True):
    x, y, w, h = S4X, S4Y, S4PW, S4PH
    pid = (lambda s: f' id="{prefix}-{s}"') if with_ids else (lambda s: "")
    return (
        f'<g{pid("panel")}>'
        f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="{th_fill(*HERO)}"/>'
        f'<path{pid("bus")} d="{busbars(x, y, w, h)}" stroke="#FFDCCB" stroke-width="1" fill="none"/>'
        f'<path d="{cell_lines(x, y, w, h)}" stroke="{TH_CELL}" stroke-width="1" fill="none"/>'
        + anomalies_svg(*HERO, x, y, K, prefix, hero_ids=with_ids)
        + f'<rect{pid("inner")} x="{n(x + 14)}" y="{n(y + 14)}" width="{n(w - 28)}" height="{n(h - 28)}" '
        f'fill="none" stroke="{INK}" stroke-width="1.2"/>'
        f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="none" stroke="{INK}" stroke-width="2"/>'
        "</g>"
    )


def marks_svg(prefix, drawable):
    cls = ' class="d"' if drawable else ""
    out = []
    for i, (cx, cy, r) in enumerate(MARKS):
        out.append(
            f'<circle id="{prefix}-c{i}"{cls} pathLength="1" cx="{n(cx)}" cy="{n(cy)}" r="{r}" '
            f'fill="none" stroke="{ACC}" stroke-width="3" transform="rotate(-90 {n(cx)} {n(cy)})"/>'
        )
    return "".join(out)


# viewBoxes for the zoom hand-offs
S3_END_VB = (HX - 645 / 3, HY - 320 / 3, W / 3, H / 3)  # hero at 645,320 x3
k4 = 630 / S4PW
S4_START_VB = (S4X - 645 / k4, S4Y - 320 / k4, W / k4, H / k4)
THUMB = (260, 200, 520)  # x, y, width of report thumbnail
k5 = THUMB[2] / S4PW
S4_END_VB = (S4X - THUMB[0] / k5, S4Y - THUMB[1] / k5, W / k5, H / k5)


def vb(t):
    return " ".join(n(v) for v in t)


# --------------------------------------------------------------------------
# Logo (vector redraw of the Fly Scan'Air PNG) — logo coords 1270 x 430
# --------------------------------------------------------------------------
LOGO_S = 0.72
LOGO_X = (W - 1270 * LOGO_S) / 2
LOGO_Y = 196
BALL_L = (30, 218)
BALL_R = (1087.5, 170)  # = le point du « ı » (Comfortaa 700, 174 px, mesuré)


def logo_coil_path():
    d = [f"M{BALL_L[0]} {BALL_L[1]}", "H95", "Q125 218 125 248", "V375"]
    xs = [125, 195, 265, 335, 405, 475, 545, 615, 685]
    for i in range(len(xs) - 1):
        a, b = xs[i], xs[i + 1]
        if i % 2 == 0:  # bottom U-turn, then go up
            d.append(f"A35 35 0 0 0 {b} 375")
            d.append("V75")
        else:  # top U-turn, then go down
            d.append(f"A35 35 0 0 1 {b} 75")
            d.append("V375" if i < len(xs) - 2 else "V290")
    d += ["Q685 335 730 335", "H1200", "Q1245 335 1245 290", "V215", "Q1245 170 1200 170", f"H{BALL_R[0]}"]
    return " ".join(d)


def logo_screen(x, y):
    return LOGO_X + x * LOGO_S, LOGO_Y + y * LOGO_S


# --------------------------------------------------------------------------
# S1 — Le problème invisible
# --------------------------------------------------------------------------
def build_s1():
    # building (oblique projection)
    front = (980, 640, 700, 240)
    side = [(1680, 880), (1680, 640), (1790, 400), (1790, 790)]
    roof = [(980, 640), (1680, 640), (1790, 400), (1090, 400)]

    def P(u, v):  # roof plane: u in [0,700], v in [0,1] (back -> front)
        return 1090 + u - 110 * v, 400 + 240 * v

    cols, rows = 6, 3
    u0, u1, gu = 20, 680, 10
    v0, v1, gv = 0.07, 0.93, 0.035
    pw = (u1 - u0 - gu * (cols - 1)) / cols
    ph = (v1 - v0 - gv * (rows - 1)) / rows
    pfills, plines, pcells = [], [], []
    order = sorted(((r, c) for r in range(rows) for c in range(cols)), key=lambda rc: (rc[0] + rc[1], rc[1]))
    for r, c in order:
        ua = u0 + c * (pw + gu)
        va = v0 + r * (ph + gv)
        q = [P(ua, va), P(ua + pw, va), P(ua + pw, va + ph), P(ua, va + ph)]
        pfills.append(f'<polygon class="s1-pfill" points="{pts(q)}" fill="#F1F2F4" stroke="none"/>')
        plines.append(f'<polygon class="d s1-pline" pathLength="1" points="{pts(q)}"/>')
        d = []
        for i in range(1, 4):
            a, b = P(ua + pw * i / 4, va), P(ua + pw * i / 4, va + ph)
            d.append(f"M{n(a[0])} {n(a[1])}L{n(b[0])} {n(b[1])}")
        for j in range(1, 3):
            a, b = P(ua, va + ph * j / 3), P(ua + pw, va + ph * j / 3)
            d.append(f"M{n(a[0])} {n(a[1])}L{n(b[0])} {n(b[1])}")
        pcells.append(f'<path class="s1-cells" d="{"".join(d)}"/>')

    # hotspot: panel row 1, col 3, cell (2,1) -> local coords (u, 240 v)
    hu = u0 + 3 * (pw + gu) + pw * 2.5 / 4
    hv = v0 + 1 * (ph + gv) + ph * 1.5 / 3
    hy = 240 * hv

    sun_c = (1300, 210)
    rays = []
    for i in range(8):
        import math

        a = math.radians(i * 45 - 90)
        x1, y1 = sun_c[0] + 50 * math.cos(a), sun_c[1] + 50 * math.sin(a)
        x2, y2 = sun_c[0] + 72 * math.cos(a), sun_c[1] + 72 * math.sin(a)
        rays.append(f'<line class="d s1-ray" pathLength="1" x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}"/>')

    body = f"""    <svg class="world" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
      <defs>{thermal_defs("s1")}</defs>
      <g fill="none" stroke="{INK}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line id="s1-ground" class="d" pathLength="1" x1="120" y1="880" x2="1800" y2="880"/>
        <g id="s1-walls" stroke="none" fill="#FFFFFF">
          <rect class="s1-wfill" x="{front[0]}" y="{front[1]}" width="{front[2]}" height="{front[3]}"/>
          <polygon class="s1-wfill" points="{pts(side)}"/>
          <polygon class="s1-wfill" points="{pts(roof)}"/>
        </g>
        <rect id="s1-front" class="d s1-line" pathLength="1" x="{front[0]}" y="{front[1]}" width="{front[2]}" height="{front[3]}"/>
        <polyline id="s1-side" class="d s1-line" pathLength="1" points="{pts([(1680, 640), (1790, 400), (1790, 790), (1680, 880)])}"/>
        <polyline id="s1-roof" class="d s1-line" pathLength="1" points="{pts([(980, 640), (1090, 400), (1790, 400)])}"/>
        <g stroke-width="2">
          <rect class="d s1-detail" pathLength="1" x="1080" y="720" width="180" height="160"/>
          <polyline class="d s1-detail" pathLength="1" points="1080,720 1260,880"/>
          <polyline class="d s1-detail" pathLength="1" points="1260,720 1080,880"/>
          <rect class="d s1-detail" pathLength="1" x="1360" y="700" width="240" height="44"/>
          <polyline class="d s1-detail" pathLength="1" points="1440,700 1440,744"/>
          <polyline class="d s1-detail" pathLength="1" points="1520,700 1520,744"/>
        </g>
        <g id="s1-panels">
          {"".join(pfills)}
          <g stroke="#C9CBD1" stroke-width="1">{"".join(pcells)}</g>
          <g stroke-width="2">{"".join(plines)}</g>
        </g>
        <g id="s1-sun" stroke-width="2.5">
          <circle id="s1-sunc" class="d" pathLength="1" cx="{sun_c[0]}" cy="{sun_c[1]}" r="34" transform="rotate(-90 {sun_c[0]} {sun_c[1]})"/>
          {"".join(rays)}
        </g>
      </g>
      <g id="s1-hot" transform="matrix(1 0 -0.45833 1 1090 400)">
        <circle id="s1-hotglow" cx="{n(hu)}" cy="{n(hy)}" r="40" fill="url(#s1-hot)"/>
        <circle id="s1-ring" cx="{n(hu)}" cy="{n(hy)}" r="22" fill="none" stroke="{ACC}" stroke-width="2"/>
        <circle id="s1-ring2" cx="{n(hu)}" cy="{n(hy)}" r="22" fill="none" stroke="{ACC}" stroke-width="2"/>
      </g>
    </svg>
    <div id="s1-title" class="title" style="left: 140px; top: 352px">Certaines anomalies<br />sont invisibles<br />à l’œil nu.</div>"""

    css = """
    #root .s1-pline { stroke: #111111; }
    #root .s1-pfill, #root .s1-cells, #root .s1-wfill { opacity: 0; }
    #root #s1-hotglow, #root #s1-ring, #root #s1-ring2 { opacity: 0; }"""

    js = """
      const title = words($("#s1-title"), txt("s1-title", "Certaines anomalies|sont *invisibles*|à l’œil nu."));
      // 1. dessin progressif du bâtiment
      tl.fromTo($("#s1-ground"), { attr: { "stroke-dashoffset": 0.62 } }, { attr: { "stroke-dashoffset": 0 }, duration: 1.0, ease: "power2.out" }, 0);
      fadeIn(0.3, $$(".s1-wfill"), 0.6);
      draw(0.3, $("#s1-front"), 0.9);
      draw(0.55, $("#s1-side"), 0.8);
      draw(0.8, $("#s1-roof"), 0.9);
      draw(1.25, $$(".s1-detail"), 0.6, "power2.inOut", 0.06);
      draw(1.1, $$(".s1-pline"), 0.5, "power2.inOut", 0.045);
      fadeIn(1.45, $$(".s1-pfill"), 0.4, 0.045);
      fadeIn(1.9, $$(".s1-cells"), 0.5, 0.02);
      draw(1.7, $("#s1-sunc"), 0.7);
      draw(2.05, $$(".s1-ray"), 0.3, "power2.out", 0.04);
      // 2. le point chaud apparaît progressivement
      tl.fromTo($("#s1-hotglow"), { opacity: 0, scale: 0.35, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: 1.2, ease: "power2.inOut" }, 2.6);
      [[4.0, "#s1-ring"], [4.35, "#s1-ring2"], [5.2, "#s1-ring"], [5.55, "#s1-ring2"]].forEach(([t, id]) => {
        tl.fromTo($(id), { opacity: 0.8, scale: 1, transformOrigin: "50% 50%" }, { opacity: 0, scale: 2.6, duration: 1.0, ease: "power2.out", immediateRender: false }, t);
      });
      // 3. titre mot à mot
      blurIn(3.0, title);
      // 4. sortie : tout se dé-trace sauf la ligne de sol
      blurOut(6.35, title, 0.18, 0.025);
      fadeOut(6.4, $("#s1-hotglow"), 0.3);
      undraw(6.4, $$(".s1-pline").reverse(), 0.4, "power3.in", 0.012);
      fadeOut(6.4, [...$$(".s1-pfill"), ...$$(".s1-cells")], 0.35);
      undraw(6.45, [...$$(".s1-ray"), $("#s1-sunc")], 0.4, "power3.in", 0.02);
      undraw(6.4, [...$$(".s1-detail"), $("#s1-roof"), $("#s1-side"), $("#s1-front")], 0.5, "power3.in", 0.025);
      fadeOut(6.6, $$(".s1-wfill"), 0.4);"""
    write_scene(
        "s1",
        "Scène 1 — Le problème invisible",
        [svar("s1-title", "Scène 1 — titre (| = retour ligne, *mot* = orange)", "Certaines anomalies|sont *invisibles*|à l’œil nu.")],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# S2 — Les risques
# --------------------------------------------------------------------------
def smooth_path(points):
    """Catmull-Rom -> Bézier cubiques (courbe passant par chaque point)."""
    d = [f"M{n(points[0][0])} {n(points[0][1])}"]
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{n(c1[0])} {n(c1[1])} {n(c2[0])} {n(c2[1])} {n(p2[0])} {n(p2[1])}")
    return " ".join(d)


# Données du graphique « Rendement (%) » fournies par le client (janvier -> juin)
S2_X0, S2_Y0, S2_DX, S2_DY = 250, 850, 150, 24  # origine (80 %), px par mois, px par point de %
S2_MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun"]
S2_SAINE = [(0, 98.2), (1, 97.9), (2, 97.4), (3, 96.6), (4, 96.3), (5, 96.0), (5.4, 95.2)]
S2_DEFAUT = [(0, 98.2), (1, 96.6), (2, 94.0), (3, 90.0), (4, 86.7), (5, 85.4), (5.4, 85.2)]


def s2_xy(m, v):
    return S2_X0 + m * S2_DX, S2_Y0 - (v - 80) * S2_DY


def build_s2():
    saine = [s2_xy(*p) for p in S2_SAINE]
    defaut = [s2_xy(*p) for p in S2_DEFAUT]
    p_saine, p_defaut = smooth_path(saine), smooth_path(defaut)
    back = smooth_path(defaut[::-1]).replace("M", "L", 1)
    loss = p_saine + " " + back + " Z"
    xend = S2_X0 + 5.4 * S2_DX
    ax_x1, ax_y1 = 1120, 330
    grid, yticks, xticks = [], [], []
    for v in (80, 85, 90, 95, 100):
        y = s2_xy(0, v)[1]
        if v > 80:
            grid.append(f'<line x1="{S2_X0}" y1="{n(y)}" x2="{ax_x1 - 10}" y2="{n(y)}"/>')
        yticks.append(f'<text x="{S2_X0 - 22}" y="{n(y + 10)}" text-anchor="end">{v}</text>')
    for i, m in enumerate(S2_MONTHS):
        x = S2_X0 + i * S2_DX
        xticks.append(f'<line x1="{x}" y1="{S2_Y0}" x2="{x}" y2="{S2_Y0 + 10}" stroke="{INK}" stroke-width="2"/>')
        xticks.append(f'<text x="{x}" y="{S2_Y0 + 46}" text-anchor="middle">{m}</text>')
    gs, gd = saine[-1], defaut[-1]
    flame_o = "M0 -110 C20 -70 75 -45 75 25 C75 75 42 105 0 105 C-42 105 -75 75 -75 25 C-75 -20 -40 -40 -30 -75 C-10 -45 0 -30 5 -10 C20 -40 15 -80 0 -110 Z"
    flame_i = "M0 28 C18 44 30 60 30 76 C30 93 17 104 0 104 C-17 104 -30 93 -30 76 C-30 58 -14 46 0 28 Z"
    shield = "M0 -112 L86 -82 L86 0 C86 60 46 96 0 116 C-46 96 -86 60 -86 0 L-86 -82 Z"
    check = "M-36 2 L-8 30 L40 -24"
    FX, SX, IY = 1430, 1705, 590
    body = f"""    <svg class="world" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
      <defs>
        <clipPath id="s2-clip"><rect id="s2-cliprect" x="{S2_X0}" y="300" width="0" height="560"/></clipPath>
        <linearGradient id="s2-lossg" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stop-color="{ACC}" stop-opacity="0.08"/>
          <stop offset="1" stop-color="{ACC}" stop-opacity="0.22"/>
        </linearGradient>
      </defs>
      <g id="s2-grid" stroke="#E4E4E7" stroke-width="1.5" stroke-dasharray="6 8">{"".join(grid)}</g>
      <g id="s2-yt" class="tick">{"".join(yticks)}</g>
      <g id="s2-xt" class="tick">{"".join(xticks)}</g>
      <path id="s2-loss" clip-path="url(#s2-clip)" d="{loss}" fill="url(#s2-lossg)"/>
      <g fill="none" stroke="{INK}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line id="s2-x" x1="120" y1="880" x2="1800" y2="880"/>
        <polyline id="s2-xa" class="d" pathLength="1" points="{ax_x1 - 12},{S2_Y0 - 9} {ax_x1},{S2_Y0} {ax_x1 - 12},{S2_Y0 + 9}"/>
        <line id="s2-y" class="d" pathLength="1" x1="{S2_X0}" y1="{S2_Y0}" x2="{S2_X0}" y2="{ax_y1}"/>
        <polyline id="s2-ya" class="d" pathLength="1" points="{S2_X0 - 9},{ax_y1 + 12} {S2_X0},{ax_y1} {S2_X0 + 9},{ax_y1 + 12}"/>
        <path id="s2-saine" class="d" pathLength="1" d="{p_saine}" stroke="#A1A1AA" stroke-width="4"/>
        <path id="s2-defaut" class="d" pathLength="1" d="{p_defaut}" stroke="{ACC}" stroke-width="4.5"/>
        <g transform="translate({FX} {IY})">
          <path id="s2-flame" class="d" pathLength="1" d="{flame_o}"/>
          <path id="s2-flamei" d="{flame_i}" fill="{ACC}" stroke="none"/>
        </g>
        <g transform="translate({SX} {IY})">
          <path id="s2-shield" class="d" pathLength="1" d="{shield}"/>
          <path id="s2-check" class="d" pathLength="1" d="{check}" stroke-width="3"/>
        </g>
      </g>
      <circle id="s2-end0" cx="{n(gs[0])}" cy="{n(gs[1])}" r="9" fill="#FFFFFF" stroke="#A1A1AA" stroke-width="3.5"/>
      <circle id="s2-end1" cx="{n(gd[0])}" cy="{n(gd[1])}" r="9" fill="#FFFFFF" stroke="{ACC}" stroke-width="3.5"/>
    </svg>
    <div id="s2-head" class="head">
      <span id="s2-t1" class="term">Perte de rendement</span><i class="sq"></i><span id="s2-t2" class="term">Risque incendie</span><i class="sq"></i><span id="s2-t3" class="term">Défauts invisibles</span>
    </div>
    <div id="s2-lab-y" class="label" style="left: 200px; top: 274px">Rendement (%)</div>
    <div id="s2-lab-x" class="label" style="left: 900px; top: 922px; width: 220px; text-align: right">Temps (mois)</div>
    <div id="s2-lab-s0" class="label" style="left: {n(xend + 22)}px; top: {n(gs[1] - 20)}px">Saine</div>
    <div id="s2-lab-s1" class="label" style="left: {n(xend + 22)}px; top: {n(gd[1] - 20)}px; color: #111111">Avec défauts</div>
    <div id="s2-lab-f" class="label" style="left: {FX - 110}px; top: 735px; width: 220px; text-align: center">Incendie</div>
    <div id="s2-lab-s" class="label" style="left: {SX - 120}px; top: 735px; width: 240px; text-align: center">Assurance</div>"""
    css = """
    #root .head { position: absolute; left: 140px; top: 150px; font-weight: 700; font-size: 46px; letter-spacing: -0.01em; white-space: nowrap; display: flex; align-items: center; }
    #root .term { color: #D4D4D8; }
    #root .sq { display: inline-block; width: 14px; height: 14px; background: #FF5700; margin: 0 28px; }
    #root .tick text { font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 28px; fill: #6B6B70; }
    #root #s2-end0, #root #s2-end1, #root #s2-flamei, #root #s2-grid, #root #s2-yt, #root #s2-xt { opacity: 0; }"""
    js = """
      $("#s2-t1").textContent = txt("s2-t1", "Perte de rendement");
      $("#s2-t2").textContent = txt("s2-t2", "Risque incendie");
      $("#s2-t3").textContent = txt("s2-t3", "Défauts invisibles");
      const head = $("#s2-head");
      // 1. la ligne de sol devient l'axe des temps, l'axe du rendement se dessine
      tl.fromTo($("#s2-x"), { attr: { x1: 120, x2: 1800, y1: 880, y2: 880 } }, { attr: { x1: __X0__, x2: __AX1__, y1: __Y0__, y2: __Y0__ }, duration: 0.7, ease: "power2.inOut" }, 0);
      draw(0.35, $("#s2-y"), 0.55, "power3.out");
      draw(0.7, [$("#s2-xa"), $("#s2-ya")], 0.25, "power2.out", 0.05);
      blurIn(0.3, head, 0.2, 0, 6);
      fadeIn(0.55, [$("#s2-grid"), $("#s2-yt"), $("#s2-xt")], 0.4, 0.08);
      blurIn(0.75, [$("#s2-lab-y"), $("#s2-lab-x")], 0.2, 0.1);
      // 2. installation saine vs installation avec défauts
      draw(0.9, $("#s2-saine"), 1.2, "power1.inOut");
      draw(1.0, $("#s2-defaut"), 1.3, "power1.inOut");
      tl.fromTo($("#s2-cliprect"), { attr: { width: 0 } }, { attr: { width: __CW__ }, duration: 1.3, ease: "power1.inOut" }, 1.0);
      tl.fromTo($("#s2-end0"), { opacity: 0, scale: 0, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.6)" }, 2.1);
      tl.fromTo($("#s2-end1"), { opacity: 0, scale: 0, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.6)" }, 2.25);
      blurIn(2.2, [$("#s2-lab-s0"), $("#s2-lab-s1")], 0.18, 0.12);
      tl.fromTo($("#s2-t1"), { color: "#D4D4D8" }, { color: "#111111", duration: 0.3 }, 1.9);
      // 3. icône incendie
      draw(2.6, $("#s2-flame"), 0.8);
      fadeIn(3.1, $("#s2-flamei"), 0.4);
      blurIn(3.1, $("#s2-lab-f"), 0.2);
      tl.fromTo($("#s2-t2"), { color: "#D4D4D8" }, { color: "#111111", duration: 0.3 }, 3.0);
      // 4. icône assurance
      draw(3.4, $("#s2-shield"), 0.8);
      draw(4.05, $("#s2-check"), 0.3, "power2.out");
      blurIn(3.9, $("#s2-lab-s"), 0.2);
      tl.fromTo($("#s2-t3"), { color: "#D4D4D8" }, { color: "#111111", duration: 0.3 }, 3.85);
      // 5. sortie : flou + fondu
      blurOut(5.45, [head, ...$$(".label")], 0.2, 0.02);
      blurOut(5.5, R.querySelector("svg.world"), 0.25, 0, 8);"""
    js = (js.replace("__X0__", str(S2_X0)).replace("__AX1__", str(ax_x1)).replace("__Y0__", str(S2_Y0))
          .replace("__CW__", n(xend - S2_X0 + 12)))
    write_scene(
        "s2",
        "Scène 2 — Les risques (graphique rendement fourni par le client)",
        [
            svar("s2-t1", "Scène 2 — terme 1", "Perte de rendement"),
            svar("s2-t2", "Scène 2 — terme 2", "Risque incendie"),
            svar("s2-t3", "Scène 2 — terme 3", "Défauts invisibles"),
        ],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# S3 — Inspection drone
# --------------------------------------------------------------------------
HOVER_X, SCAN_END_X, DRONE_Y = 215, 1790, 680


def drone_svg():
    rot = [(-105, -78), (105, -78), (-105, 78), (105, 78)]
    arms = "".join(
        f'<line x1="{n(x * 0.3)}" y1="{n(y * 0.3)}" x2="{x}" y2="{y}" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
        f'<line x1="{n(x * 0.3)}" y1="{n(y * 0.3)}" x2="{x}" y2="{y}" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round"/>'
        for x, y in rot
    )
    rotors = "".join(
        f'<g transform="translate({x} {y})">'
        f'<circle r="56" fill="#111111" fill-opacity="0.035" stroke="{INK}" stroke-width="1.5"/>'
        f'<circle r="9" fill="#FFFFFF" stroke="{INK}" stroke-width="2"/>'
        f'<g class="s3-blade"><line x1="-48" y1="0" x2="48" y2="0" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/></g>'
        "</g>"
        for x, y in rot
    )
    return f"""<g id="s3-drone">
          <ellipse cx="34" cy="46" rx="150" ry="112" fill="#111111" fill-opacity="0.06"/>
          {arms}
          {rotors}
          <rect x="-52" y="-36" width="104" height="72" rx="18" fill="#FFFFFF" stroke="{INK}" stroke-width="2.5"/>
          <line x1="-30" y1="-36" x2="-30" y2="36" stroke="{INK}" stroke-width="1.2"/>
          <circle cx="58" cy="0" r="14" fill="#FFFFFF" stroke="{INK}" stroke-width="2.5"/>
          <circle cx="58" cy="0" r="6" fill="{ACC}"/>
        </g>"""


def build_s3():
    normal, thermal = [], []
    anom_xs = []
    for c in range(COLS):
        for r in range(ROWS):
            x, y = panel_xy(r, c)
            normal.append(
                f'<rect class="s3-pfill" x="{x}" y="{y}" width="{PW}" height="{PH}" fill="{PANEL}"/>'
                f'<path class="s3-cells" d="{cell_lines(x, y, PW, PH)}" stroke="{CELL}" stroke-width="1" fill="none"/>'
                f'<rect class="d s3-pline" pathLength="1" x="{x}" y="{y}" width="{PW}" height="{PH}" fill="none" stroke="{INK}" stroke-width="2"/>'
            )
            thermal.append(
                f'<rect x="{x}" y="{y}" width="{PW}" height="{PH}" fill="{th_fill(r, c)}"/>'
                f'<path d="{cell_lines(x, y, PW, PH)}" stroke="{TH_CELL}" stroke-width="1" fill="none"/>'
                + anomalies_svg(r, c, x, y, 1, "s3")
                + f'<rect x="{x}" y="{y}" width="{PW}" height="{PH}" fill="none" stroke="{INK}" stroke-width="2"/>'
            )
            for kind, ax, ay in ANOM.get((r, c), []):
                if kind == "spot":
                    anom_xs.append((x + ax, y + ay))
    rings = "".join(
        f'<circle class="s3-ring" data-x="{n(x)}" cx="{n(x)}" cy="{n(y)}" r="16" fill="none" stroke="{ACC}" stroke-width="2"/>'
        for x, y in anom_xs
    )
    fy0, fy1 = FY0 - 20, FY0 + ROWS * PH + (ROWS - 1) * GY + 20
    body = f"""    <svg id="s3-svg" class="world zoom" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
      <defs>
        {thermal_defs("s3")}
        <linearGradient id="s3-trail" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stop-color="{ACC}" stop-opacity="0"/>
          <stop offset="1" stop-color="{ACC}" stop-opacity="0.16"/>
        </linearGradient>
        <clipPath id="s3-clip"><rect id="s3-cliprect" x="{HOVER_X}" y="{fy0}" width="0" height="{fy1 - fy0}"/></clipPath>
      </defs>
      <g id="s3-normal">{"".join(normal)}</g>
      <g id="s3-thermal" clip-path="url(#s3-clip)">{"".join(thermal)}{rings}</g>
      <g id="s3-scan">
        <rect x="-120" y="{fy0}" width="120" height="{fy1 - fy0}" fill="url(#s3-trail)"/>
        <line x1="0" y1="{fy0}" x2="0" y2="{fy1}" stroke="{ACC}" stroke-width="3"/>
        <line x1="-12" y1="{fy0}" x2="12" y2="{fy0}" stroke="{ACC}" stroke-width="3"/>
        <line x1="-12" y1="{fy1}" x2="12" y2="{fy1}" stroke="{ACC}" stroke-width="3"/>
      </g>
      {drone_svg()}
      <polyline id="s3-leader" class="d" pathLength="1" points="{HOVER_X},{DRONE_Y - 40} {HOVER_X},331 470,331" fill="none" stroke="{INK}" stroke-width="1.5"/>
      <circle id="s3-leaddot" cx="{HOVER_X}" cy="{DRONE_Y - 40}" r="5" fill="{INK}"/>
    </svg>
    <div id="s3-hud">
      <div id="s3-tag" class="tag">Caméra infrarouge</div>
      <div id="s3-scale" class="scale"><span>Froid</span><i></i><span>Chaud</span></div>
    </div>
    <div id="s3-title" class="title" style="left: 140px; top: 120px">Le scan infrarouge révèle<br />chaque échauffement.</div>"""
    css = """
    #root #s3-hud { position: absolute; left: 480px; top: 306px; display: flex; align-items: center; gap: 36px; }
    #root .tag { font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 30px; line-height: 1; padding: 10px 16px; background: #FFFFFF; border: 1.5px solid #111111; color: #111111; white-space: nowrap; }
    #root .scale { display: flex; align-items: center; gap: 14px; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 30px; color: #6B6B70; }
    #root .scale i { display: block; width: 200px; height: 12px; background: linear-gradient(90deg, #E4E4E7 0%, #FFD2BC 55%, #FF5700 100%); }
    #root #s3-tag, #root #s3-scale, #root #s3-leaddot, #root #s3-scan, #root .s3-ring { opacity: 0; }
    #root .s3-pfill, #root .s3-cells { opacity: 0; }"""
    js = f"""
      const title = words($("#s3-title"), txt("s3-title", "Le scan infrarouge révèle|chaque *échauffement*."));
      const HOVER = {HOVER_X}, END = {SCAN_END_X}, Y = {DRONE_Y};
      const T0 = 3.9, TD = 2.7; // balayage
      // 1. le champ de panneaux se dessine (vue de dessus)
      draw(0.1, $$(".s3-pline"), 0.5, "power2.inOut", 0.035);
      fadeIn(0.35, $$(".s3-pfill"), 0.4, 0.035);
      fadeIn(0.7, $$(".s3-cells"), 0.5, 0.025);
      solid(1.9, $$(".s3-pline"));
      // 2. le drone entre ; les rotors tournent en continu
      tl.fromTo($("#s3-drone"), {{ x: -260, y: Y }}, {{ x: HOVER, y: Y, duration: 1.2, ease: "expo.out" }}, 0.9);
      tl.fromTo($$(".s3-blade"), {{ rotation: 0, transformOrigin: "50% 50%" }}, {{ rotation: 360 * 15, duration: 7.2, ease: "none" }}, 0);
      // 3. HUD technique : ligne de rappel + données
      fadeIn(1.95, $("#s3-leaddot"), 0.15);
      draw(2.0, $("#s3-leader"), 0.4, "power2.out");
      blurIn(2.3, [$("#s3-tag"), $("#s3-scale")], 0.18, 0.12);
      blurOut(3.65, [$("#s3-tag"), $("#s3-scale")], 0.16, 0.05);
      undraw(3.65, $("#s3-leader"), 0.22, "power3.in");
      fadeOut(3.7, $("#s3-leaddot"), 0.15);
      tl.set($("#s3-leader"), {{ opacity: 0 }}, 3.9);
      // 4. balayage thermique : la ligne orange révèle la vue thermique
      fadeIn(T0 - 0.15, $("#s3-scan"), 0.15);
      tl.fromTo($("#s3-scan"), {{ x: HOVER }}, {{ x: END, duration: TD, ease: "power1.inOut" }}, T0);
      tl.to($("#s3-drone"), {{ x: END, duration: TD, ease: "power1.inOut" }}, T0);
      tl.fromTo($("#s3-cliprect"), {{ attr: {{ width: 0 }} }}, {{ attr: {{ width: END - HOVER }}, duration: TD, ease: "power1.inOut" }}, T0);
      // chaque point chaud pulse quand la ligne le croise
      const inv = (y) => (y < 0.5 ? Math.sqrt(y / 2) : 1 - Math.sqrt((1 - y) / 2)); // inverse de power1.inOut
      $$(".s3-ring").forEach((el) => {{
        const p = (parseFloat(el.getAttribute("data-x")) - HOVER) / (END - HOVER);
        const t = T0 + TD * inv(Math.min(Math.max(p, 0), 1));
        tl.fromTo(el, {{ opacity: 0.9, scale: 1, transformOrigin: "50% 50%" }}, {{ opacity: 0, scale: 2.6, duration: 0.8, ease: "power2.out", immediateRender: false }}, t + 0.05);
      }});
      blurIn(4.0, title, 0.15, 0.067);
      // 5. sortie : le drone quitte le cadre, puis zoom traversant
      fadeOut(T0 + TD - 0.05, $("#s3-scan"), 0.25);
      tl.to($("#s3-drone"), {{ x: 2250, duration: 0.5, ease: "power3.in" }}, 6.6);
      blurOut(6.95, title, 0.16, 0.02);
      tl.to($("#s3-svg"), {{ attr: {{ viewBox: "{vb(S3_END_VB)}" }}, duration: 0.62, ease: "power3.in" }}, 7.18);"""
    write_scene(
        "s3",
        "Scène 3 — Inspection drone",
        [svar("s3-title", "Scène 3 — titre", "Le scan infrarouge révèle|chaque *échauffement*.")],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# S4 — Détection des anomalies
# --------------------------------------------------------------------------
def build_s4():
    neigh = []
    hr, hc = HERO
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            r, c = hr + dr, hc + dc
            x3, y3 = panel_xy(r, c)
            x, y = to_s4(x3, y3)
            neigh.append(
                f'<rect x="{n(x)}" y="{n(y)}" width="{n(S4PW)}" height="{n(S4PH)}" fill="{th_fill(r, c)}"/>'
                f'<path d="{cell_lines(x, y, S4PW, S4PH)}" stroke="{TH_CELL}" stroke-width="1" fill="none"/>'
                + anomalies_svg(r, c, x, y, K, "s4")
                + f'<rect x="{n(x)}" y="{n(y)}" width="{n(S4PW)}" height="{n(S4PH)}" fill="none" stroke="{INK}" stroke-width="2"/>'
            )
    labels_y = [504, 652, 800]
    leaders, dots, labels = [], [], []
    names = [("s4-l1", "Point chaud"), ("s4-l2", "Cellule défectueuse"), ("s4-l3", "Défaut de connexion")]
    import math

    for i, ((cx, cy, r), ly) in enumerate(zip(MARKS, labels_y)):
        dy = ly - cy
        sx = cx + math.sqrt(max(r * r - dy * dy, 0))
        leaders.append(f'<polyline id="s4-ld{i}" class="d" pathLength="1" points="{n(sx)},{n(ly)} 1160,{n(ly)}" fill="none" stroke="{INK}" stroke-width="1.5"/>')
        dots.append(f'<circle id="s4-dot{i}" cx="1160" cy="{n(ly)}" r="5" fill="{INK}"/>')
        labels.append(f'<div id="{names[i][0]}" class="lab4" style="left: 1182px; top: {n(ly - 21)}px">{names[i][1]}</div>')
    hx, hy = MARKS[0][0], MARKS[0][1]
    body = f"""    <svg id="s4-svg" class="world zoom" viewBox="{vb(S4_START_VB)}" width="{W}" height="{H}">
      <defs>{thermal_defs("s4")}</defs>
      <g id="s4-neigh">{"".join(neigh)}</g>
      {hero_panel_svg("s4")}
      <circle id="s4-ring" cx="{n(hx)}" cy="{n(hy)}" r="34" fill="none" stroke="{ACC}" stroke-width="2.5"/>
      <g id="s4-marks">{marks_svg("s4", True)}</g>
      <g id="s4-leaders">{"".join(leaders)}{"".join(dots)}</g>
    </svg>
    {"".join(labels)}
    <div id="s4-title" class="title" style="left: 120px; top: 86px; font-size: 56px">Chaque anomalie est détectée et localisée.</div>"""
    css = """
    #root .lab4 { position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 36px; line-height: 42px; color: #111111; white-space: nowrap; }
    #root #s4-bus, #root #s4-inner, #root #s4-ring { opacity: 0; }
    #root #s4-leaders circle { opacity: 0; }"""
    js = f"""
      const title = words($("#s4-title"), txt("s4-title", "Chaque anomalie est détectée et localisée."));
      txt("s4-l1", "") && ($("#s4-l1").textContent = txt("s4-l1", ""));
      txt("s4-l2", "") && ($("#s4-l2").textContent = txt("s4-l2", ""));
      txt("s4-l3", "") && ($("#s4-l3").textContent = txt("s4-l3", ""));
      const svg = $("#s4-svg");
      // 1. le zoom se pose sur le panneau défectueux
      tl.fromTo(svg, {{ attr: {{ viewBox: "{vb(S4_START_VB)}" }} }}, {{ attr: {{ viewBox: "0 0 {W} {H}" }}, duration: 0.95, ease: "power3.out" }}, 0);
      fadeOut(0.2, $("#s4-neigh"), 0.6, 0, "power1.inOut");
      fadeIn(0.55, [$("#s4-inner"), $("#s4-bus")], 0.6);
      // 2. titre : du gris à l'encre, mot à mot
      tl.fromTo(title, {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2 }}, 0.75);
      tl.fromTo(title, {{ color: "#D4D4D8" }}, {{ color: "#111111", duration: 0.25, stagger: 0.08 }}, 0.95);
      // 3. points chauds pulsants
      [1.0, 2.0, 3.0, 4.0, 5.0].forEach((t) => {{
        tl.fromTo($("#s4-ring"), {{ opacity: 0.85, scale: 1, transformOrigin: "50% 50%" }}, {{ opacity: 0, scale: 3.2, duration: 1.0, ease: "power2.out", immediateRender: false }}, t);
      }});
      // 4. les défauts sont entourés automatiquement
      [[1.4, 0], [2.3, 1], [3.2, 2]].forEach(([t, i]) => {{
        draw(t, $("#s4-c" + i), 0.6, "power2.inOut");
        draw(t + 0.4, $("#s4-ld" + i), 0.3, "power2.out");
        fadeIn(t + 0.65, $("#s4-dot" + i), 0.1);
        blurIn(t + 0.62, $("#s4-l" + (i + 1)), 0.18);
      }});
      solid(4.0, $$("#s4-marks circle"));
      // 5. sortie : la vignette part dans le rapport
      blurOut(5.55, [...title, $("#s4-l1"), $("#s4-l2"), $("#s4-l3")], 0.18, 0.02);
      undraw(5.55, $$("#s4-leaders polyline"), 0.2, "power3.in");
      fadeOut(5.55, $$("#s4-leaders circle"), 0.15);
      fadeOut(5.8, [$("#s4-bus"), $("#s4-inner")], 0.4);
      tl.to(svg, {{ attr: {{ viewBox: "{vb(S4_END_VB)}" }}, duration: 0.72, ease: "power2.inOut" }}, 5.83);"""
    write_scene(
        "s4",
        "Scène 4 — Détection des anomalies",
        [
            svar("s4-title", "Scène 4 — titre", "Chaque anomalie est détectée et localisée."),
            svar("s4-l1", "Scène 4 — étiquette 1", "Point chaud"),
            svar("s4-l2", "Scène 4 — étiquette 2", "Cellule défectueuse"),
            svar("s4-l3", "Scène 4 — étiquette 3", "Défaut de connexion"),
        ],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# S5 — Rapport et bénéfices
# --------------------------------------------------------------------------
# Données du graphique « Production (kWh/an) » fournies par le client
S5_AX, S5_AY, S5_TOP = 1060, 850, 410  # axe Y en x, axe X en y, haut de l'échelle (25 000)
S5_K = (S5_AY - S5_TOP) / 25000
S5_BARS = [("Installation|saine", 20000, 1250, "#CDCDD2"), ("Installation|avec défauts", 16400, 1580, ACC)]
S5_BW = 210


def build_s5():
    dx, dy, dw, dh = 220, 96, 600, 848
    doc_path = f"M{dx} {dy} H{dx + dw} V{dy + dh} H{dx} Z"
    rows = [650, 730, 810]
    items = ["Anomalies localisées", "Priorités d’intervention", "Recommandations"]
    boxes, checks, texts = [], [], []
    for i, (y, t) in enumerate(zip(rows, items)):
        boxes.append(f'<rect class="d s5-box" pathLength="1" x="260" y="{y - 17}" width="34" height="34" rx="4"/>')
        checks.append(f'<polyline id="s5-k{i}" class="d" pathLength="1" points="266,{y + 1} 275,{y + 10} 290,{y - 9}" stroke="{ACC}" stroke-width="4"/>')
        texts.append(f'<div id="s5-i{i}" class="item" style="left: 318px; top: {y - 21}px">{t}</div>')
    ball_x, ball_y = logo_screen(*BALL_L)
    grid, yticks, bars, cats = [], [], [], []
    for v in range(0, 25001, 5000):
        y = S5_AY - v * S5_K
        if v:
            grid.append(f'<line x1="{S5_AX}" y1="{n(y)}" x2="1770" y2="{n(y)}"/>')
        label = f"{v:,}".replace(",", " ")
        yticks.append(f'<text x="{S5_AX - 20}" y="{n(y + 10)}" text-anchor="end">{label}</text>')
    for i, (name, v, cx, col) in enumerate(S5_BARS):
        h = v * S5_K
        bars.append(
            f'<rect id="s5-bar{i}" x="{cx - S5_BW / 2}" y="{n(S5_AY - h)}" width="{S5_BW}" height="{n(h + 12)}" rx="10" '
            f'fill="{col}" data-top="{n(S5_AY - h)}" data-h="{n(h + 12)}"/>'
        )
        cats.append(f'<div id="s5-cat{i}" class="cat" style="left: {cx - 170}px; top: {S5_AY + 18}px">{name.replace("|", "<br />")}</div>')
    body = f"""    <div id="s5-paper" style="left: {dx}px; top: {dy}px; width: {dw}px; height: {dh}px"></div>
    <svg class="world" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
      <g fill="none" stroke="{INK}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path id="s5-doc" class="d" pathLength="1" d="{doc_path}"/>
        <line id="s5-rule" class="d" pathLength="1" x1="260" y1="178" x2="780" y2="178" stroke-width="1.5"/>
        {"".join(boxes)}
        {"".join(checks)}
        <line class="d s5-foot" pathLength="1" x1="260" y1="884" x2="660" y2="884" stroke="#E4E4E7" stroke-width="8"/>
        <line class="d s5-foot" pathLength="1" x1="260" y1="910" x2="560" y2="910" stroke="#E4E4E7" stroke-width="8"/>
      </g>
    </svg>
    <svg id="s5-thumb" class="world zoom" viewBox="{vb(S4_END_VB)}" width="{W}" height="{H}">
      <defs>{thermal_defs("s5")}</defs>
      {hero_panel_svg("s5", with_ids=False)}
      <g id="s5-marks">{marks_svg("s5", False)}</g>
    </svg>
    <svg id="s5-chart" class="world" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
      <defs><clipPath id="s5-clip"><rect x="0" y="0" width="{W}" height="{S5_AY}"/></clipPath></defs>
      <g id="s5-axes">
        <g id="s5-grid" stroke="#E4E4E7" stroke-width="1.5" stroke-dasharray="6 8">{"".join(grid)}</g>
        <g id="s5-yt" class="tick">{"".join(yticks)}</g>
        <g fill="none" stroke="{INK}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line id="s5-ax" class="d" pathLength="1" x1="{S5_AX}" y1="{S5_AY}" x2="1790" y2="{S5_AY}"/>
          <polyline id="s5-axa" class="d" pathLength="1" points="1778,{S5_AY - 9} 1790,{S5_AY} 1778,{S5_AY + 9}"/>
          <line id="s5-ay" class="d" pathLength="1" x1="{S5_AX}" y1="{S5_AY}" x2="{S5_AX}" y2="375"/>
          <polyline id="s5-aya" class="d" pathLength="1" points="{S5_AX - 9},387 {S5_AX},375 {S5_AX + 9},387"/>
        </g>
      </g>
      <g clip-path="url(#s5-clip)">{"".join(bars)}</g>
    </svg>
    <div id="s5-h" class="dochead" style="left: 260px; top: 128px">Rapport d’inspection</div>
    {"".join(texts)}
    <div id="s5-lab-y" class="label" style="left: 1010px; top: 318px">Production (kWh/an)</div>
    {"".join(cats)}
    <div id="s5-title" class="title" style="left: 960px; top: 150px">Un rapport clair<br />pour agir vite.</div>"""
    css = """
    #root #s5-paper { position: absolute; background: #FFFFFF; box-shadow: 0 18px 40px rgba(17, 17, 17, 0.08); opacity: 0; }
    #root .dochead { position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 700; font-size: 30px; line-height: 40px; color: #111111; white-space: nowrap; }
    #root .item { position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 30px; line-height: 42px; color: #111111; white-space: nowrap; }
    #root .tick text { font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 28px; fill: #6B6B70; }
    #root .cat { position: absolute; width: 340px; text-align: center; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 28px; line-height: 36px; color: #111111; }
    #root #s5-grid, #root #s5-yt { opacity: 0; }"""
    js = """
      const title = words($("#s5-title"), txt("s5-title", "Un rapport clair|pour *agir vite*."));
      ["s5-i0", "s5-i1", "s5-i2"].forEach((id, i) => { const v = txt(id, ""); if (v) $("#" + id).textContent = v; });
      // 1. la feuille se dessine autour de la vignette
      draw(0, $("#s5-doc"), 1.1, "power2.inOut");
      fadeIn(0.2, $("#s5-paper"), 0.7);
      blurIn(0.55, $("#s5-h"), 0.2);
      draw(0.65, $("#s5-rule"), 0.45, "power2.out");
      // 2. titre
      blurIn(0.9, title, 0.15, 0.067);
      // 3. checklist cochée
      draw(1.15, $$(".s5-box"), 0.35, "power2.out", 0.12);
      blurIn(1.3, [$("#s5-i0"), $("#s5-i1"), $("#s5-i2")], 0.18, 0.2);
      draw(1.8, $("#s5-k0"), 0.25, "power2.out");
      draw(2.2, $("#s5-k1"), 0.25, "power2.out");
      draw(2.6, $("#s5-k2"), 0.25, "power2.out");
      draw(1.7, $$(".s5-foot"), 0.4, "power2.out", 0.1);
      // 4. graphique production : installation saine vs avec défauts
      draw(2.2, [$("#s5-ay"), $("#s5-ax")], 0.55, "power3.out", 0.08);
      draw(2.6, [$("#s5-aya"), $("#s5-axa")], 0.22, "power2.out", 0.05);
      fadeIn(2.45, [$("#s5-grid"), $("#s5-yt")], 0.4, 0.08);
      blurIn(2.55, $("#s5-lab-y"), 0.18);
      [0, 1].forEach((i) => {
        const b = $("#s5-bar" + i);
        const top = parseFloat(b.getAttribute("data-top")), h = parseFloat(b.getAttribute("data-h"));
        tl.fromTo(b, { attr: { y: __AY__, height: 0 } }, { attr: { y: top, height: h }, duration: 0.75, ease: "power3.out" }, 2.85 + i * 0.35);
        blurIn(3.15 + i * 0.35, $("#s5-cat" + i), 0.18);
      });
      // 5. sortie : tout se floute ; la barre orange se replie en point et file vers le logo
      const keep = $("#s5-bar1");
      const kx = __BX__, ky = parseFloat(keep.getAttribute("data-top"));
      blurOut(5.85, [...title, $("#s5-h"), $("#s5-i0"), $("#s5-i1"), $("#s5-i2"), $("#s5-lab-y"), $("#s5-cat0"), $("#s5-cat1")], 0.2, 0.015);
      blurOut(5.9, [R.querySelector("svg.world"), $("#s5-thumb"), $("#s5-paper"), $("#s5-axes"), $("#s5-bar0")], 0.22, 0.02);
      tl.to(keep, { attr: { x: kx - 10, y: ky - 10, width: 20, height: 20, rx: 10 }, duration: 0.32, ease: "power2.inOut" }, 5.85);
      tl.to(keep, { attr: { x: __TX__, y: __TY__ }, duration: 0.5, ease: "power2.inOut" }, 6.08);"""
    js = (js.replace("__AY__", str(S5_AY)).replace("__BX__", str(S5_BARS[1][2]))
          .replace("__TX__", n(ball_x - 10)).replace("__TY__", n(ball_y - 10)))
    write_scene(
        "s5",
        "Scène 5 — Rapport et bénéfices",
        [
            svar("s5-title", "Scène 5 — titre", "Un rapport clair|pour *agir vite*."),
            svar("s5-i0", "Scène 5 — ligne 1", "Anomalies localisées"),
            svar("s5-i1", "Scène 5 — ligne 2", "Priorités d’intervention"),
            svar("s5-i2", "Scène 5 — ligne 3", "Recommandations"),
        ],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# S6 — Call to action (logo Fly Scan'Air)
# --------------------------------------------------------------------------
def build_s6():
    bx, by = logo_screen(*BALL_L)
    body = f"""    <svg class="world" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
      <defs>
        <radialGradient id="s6-ball" cx="0.36" cy="0.34" r="0.7">
          <stop offset="0" stop-color="#FF9C84"/>
          <stop offset="0.35" stop-color="#E0402F"/>
          <stop offset="1" stop-color="#A51F17"/>
        </radialGradient>
        <linearGradient id="s6-word" gradientUnits="userSpaceOnUse" x1="140" y1="0" x2="1198" y2="0">
          <stop offset="0" stop-color="#E2392D"/>
          <stop offset="0.47" stop-color="#E9862A"/>
          <stop offset="0.6" stop-color="#E8842A"/>
          <stop offset="1" stop-color="#DC382D"/>
        </linearGradient>
        <clipPath id="s6-clip"><rect id="s6-cliprect" x="120" y="100" width="0" height="260"/></clipPath>
      </defs>
      <g id="s6-logo" transform="translate({n(LOGO_X)} {LOGO_Y}) scale({LOGO_S})">
        <path id="s6-coil" class="d" pathLength="1" d="{logo_coil_path()}" fill="none" stroke="#6D6C74" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
        <g clip-path="url(#s6-clip)">
          <text id="s6-word" x="140" y="292" font-family="Comfortaa" font-weight="700" font-size="174" fill="url(#s6-word)" stroke="url(#s6-word)" stroke-width="10" stroke-linejoin="round" paint-order="stroke">Fly Scan’Aır</text>
        </g>
        <line id="s6-scan" x1="0" y1="118" x2="0" y2="336" stroke="{ACC}" stroke-width="4"/>
        <circle id="s6-ballr" cx="{BALL_R[0]}" cy="{BALL_R[1]}" r="12" fill="url(#s6-ball)"/>
        <circle id="s6-balll" cx="{BALL_L[0]}" cy="{BALL_L[1]}" r="12" fill="url(#s6-ball)"/>
      </g>
      <circle id="s6-dot" cx="{n(bx)}" cy="{n(by)}" r="10" fill="{ACC}"/>
    </svg>
    <div id="s6-slogan" class="title cta1">Inspections techniques aériennes,<br />révélez l’invisible.</div>
    <div id="s6-msg" class="cta2">Faites contrôler votre installation.</div>
    <div id="s6-contact" class="cta3">www.flyscanair.com · 06 22 80 57 69 · contact@flyscanair.com</div>"""
    css = """
    #root .cta1 { left: 0; width: 1920px; top: 552px; text-align: center; font-size: 56px; line-height: 1.18; }
    #root .cta2 { position: absolute; left: 0; width: 1920px; top: 722px; text-align: center; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 38px; color: #111111; }
    #root .cta3 { position: absolute; left: 0; width: 1920px; top: 808px; text-align: center; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 32px; color: #6B6B70; display: flex; justify-content: center; align-items: center; }
    #root .cta3 .sq { display: inline-block; width: 10px; height: 10px; background: #FF5700; margin: 0 24px; }
    #root #s6-scan, #root #s6-ballr, #root #s6-balll { opacity: 0; }"""
    js = f"""
      const slogan = words($("#s6-slogan"), txt("s6-slogan", "Inspections techniques aériennes,|révélez *l’invisible*."));
      const msg = words($("#s6-msg"), txt("s6-msg", "Faites contrôler votre installation."));
      const contact = txt("s6-contact", "www.flyscanair.com|06 22 80 57 69|contact@flyscanair.com");
      const cEl = $("#s6-contact");
      cEl.textContent = "";
      contact.split("|").forEach((part, i) => {{
        if (i) {{ const q = document.createElement("i"); q.className = "sq"; cEl.appendChild(q); }}
        const sp = document.createElement("span"); sp.textContent = part.trim(); cEl.appendChild(sp);
      }});
      // 1. le point orange devient la bille rouge du logo
      tl.fromTo($("#s6-balll"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.35, ease: "power1.inOut" }}, 0.0);
      tl.to($("#s6-dot"), {{ opacity: 0, duration: 0.35, ease: "power1.inOut" }}, 0.0);
      // 2. le serpentin se trace, la ligne de scan révèle le nom
      draw(0.2, $("#s6-coil"), 1.7, "power1.inOut");
      tl.fromTo($("#s6-scan"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.12 }}, 0.5);
      tl.fromTo($("#s6-scan"), {{ x: 120 }}, {{ x: 1230, duration: 1.3, ease: "power1.inOut" }}, 0.5);
      tl.fromTo($("#s6-cliprect"), {{ attr: {{ width: 0 }} }}, {{ attr: {{ width: 1110 }}, duration: 1.3, ease: "power1.inOut" }}, 0.5);
      tl.to($("#s6-scan"), {{ opacity: 0, duration: 0.2 }}, 1.75);
      tl.fromTo($("#s6-ballr"), {{ opacity: 0, scale: 0, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.4, ease: "back.out(1.6)" }}, 1.85);
      // 3. slogan, message, contact
      blurIn(2.1, slogan, 0.15, 0.067);
      tl.fromTo(msg, {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2 }}, 2.6);
      tl.fromTo(msg, {{ color: "#D4D4D8" }}, {{ color: "#111111", duration: 0.25, stagger: 0.08 }}, 2.7);
      if (contact) blurIn(3.1, $("#s6-contact"), 0.2);"""
    write_scene(
        "s6",
        "Scène 6 — Call to action",
        [
            svar("s6-slogan", "Scène 6 — slogan", "Inspections techniques aériennes,|révélez *l’invisible*."),
            svar("s6-msg", "Scène 6 — message", "Faites contrôler votre installation."),
            svar("s6-contact", "Scène 6 — contact (| sépare les éléments)", "www.flyscanair.com|06 22 80 57 69|contact@flyscanair.com"),
        ],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# index.html
# --------------------------------------------------------------------------
SCENES = [("s1", 0, 7.2), ("s2", 7.2, 6.0), ("s3", 13.2, 7.8), ("s4", 21.0, 6.6), ("s5", 27.6, 6.6), ("s6", 34.2, 6.6)]
TOTAL = 40.8

# (id, file, hit time in the film, volume): the file's measured peak lands one frame after its picture
SFX = [
    ("sfx-drone", "whoosh-short.mp3", 13.2 + 0.98, 0.5),
    ("sfx-scan", "whoosh-cinematic.mp3", 13.2 + 5.25, 0.3),
    ("sfx-zoom", "whoosh-high.mp3", 13.2 + 7.78, 0.45),
    ("sfx-tick1", "key-press.mp3", 21.0 + 2.03, 0.5),
    ("sfx-tick2", "key-press.mp3", 21.0 + 2.93, 0.45),
    ("sfx-tick3", "key-press.mp3", 21.0 + 3.83, 0.5),
    ("sfx-carry", "whoosh-low.mp3", 21.0 + 6.2, 0.35),
    ("sfx-check1", "click-soft.mp3", 27.6 + 1.92, 0.6),
    ("sfx-check2", "click-soft.mp3", 27.6 + 2.32, 0.55),
    ("sfx-check3", "click-soft.mp3", 27.6 + 2.72, 0.6),
    ("sfx-logo", "impact-bass-1.mp3", 34.2 + 1.92, 0.22),
]


def build_index(sfx_offsets):
    hosts = "\n".join(
        f"""      <div
        id="{sid}"
        class="clip"
        data-composition-id="{sid}"
        data-composition-src="compositions/{sid}.html"
        data-start="{n(start)}"
        data-duration="{n(dur)}"
        data-track-index="1"
        data-track-kind="graphics"
        data-width="{W}"
        data-height="{H}"
      ></div>"""
        for sid, start, dur in SCENES
    )
    audio = [
        f'      <audio id="music" class="clip" src="assets/audio/music.wav" data-start="0" data-duration="{n(TOTAL)}" data-track-index="2" data-volume="1"></audio>'
    ]
    for i, (aid, fname, t, vol) in enumerate(SFX):
        t = max(0.0, t + 1 / 30 - sfx_offsets.get(fname, 0.0))
        dur = float(
            subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", os.path.join(ROOT, "assets", "audio", "sfx", fname)],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
        )
        audio.append(
            f'      <audio id="{aid}" class="clip" src="assets/audio/sfx/{fname}" data-start="{n(t)}" data-duration="{n(dur - 0.005)}" data-track-index="{3 + i % 3}" data-volume="{vol}"></audio>'
        )
    variables = [
        {"id": "color-ground", "type": "color", "label": "Fond", "default": "#FFFFFF"},
        {"id": "color-ink", "type": "color", "label": "Encre", "default": INK},
        {"id": "color-accent", "type": "color", "label": "Accent", "default": ACC},
        {"id": "color-grid", "type": "color", "label": "Trame de points", "default": "#E4E4E7"},
    ]
    doc = f"""<!doctype html>
<html lang="fr" data-composition-variables="{attr_json(variables)}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>Fly Scan’Air — Inspection thermographique par drone</title>
    <script src="assets/vendor/gsap-3.15.0.min.js"></script>
    <style>
      :root {{
        --color-ground: #ffffff;
        --color-ink: #111111;
        --color-accent: #ff5700;
        --color-grid: #e4e4e7;
      }}
      * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }}
      html,
      body {{
        margin: 0;
        width: 1920px;
        height: 1080px;
        overflow: hidden;
        background: var(--color-ground);
      }}
      #root {{
        position: relative;
        width: 100%;
        height: 100%;
        background: var(--color-ground);
      }}
      #bg {{
        position: absolute;
        inset: 0;
        background-color: var(--color-ground);
        background-image: radial-gradient(circle, var(--color-grid) 1.6px, transparent 2px);
        background-size: 48px 48px;
        background-position: 24px 24px;
      }}
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="{n(TOTAL)}"
      data-width="{W}"
      data-height="{H}"
    >
      <div id="bg"></div>
{hosts}
{chr(10).join(audio)}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(doc)
    print("wrote index.html")


if __name__ == "__main__":
    offsets = {}
    p = os.path.join(ROOT, "assets", "audio", "sfx", "peaks.json")
    if os.path.exists(p):
        offsets = json.load(open(p))
    build_s1()
    build_s2()
    build_s3()
    build_s4()
    build_s5()
    build_s6()
    build_index(offsets)
