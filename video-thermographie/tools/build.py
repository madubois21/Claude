#!/usr/bin/env python3
"""Génère index.html et compositions/s0..s8.html.

La géométrie (toit en projection oblique, champ de panneaux, raccords de zoom)
est calculée ici pour que les raccords entre scènes tombent au pixel près.
Relancer ce script ÉCRASE les fichiers HTML : faites vos retouches ici, ou
retouchez les HTML et ne relancez plus le script.

    python3 tools/build.py          # 16:9 (version principale, à la racine du projet)
    python3 tools/build.py 9x16     # déclinaison verticale  -> formats/9x16/
    python3 tools/build.py 1x1      # déclinaison carrée     -> formats/1x1/
"""
import html
import json
import os
import shutil
import subprocess
import sys

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

FMT = (sys.argv[1] if len(sys.argv) > 1 else "16x9").lower()
assert FMT in ("16x9", "9x16", "1x1"), FMT
WIDE = FMT == "16x9"
SW, SH = 1920, 1080  # scène de référence (monde 16:9) dans laquelle tout est dessiné
W, H = {"16x9": (1920, 1080), "9x16": (1080, 1920), "1x1": (1080, 1080)}[FMT]
OUT = ROOT if WIDE else os.path.join(ROOT, "formats", FMT)
CANVAS = "" if WIDE else f' style="width: {W}px; height: {H}px"'

# Mise en page des déclinaisons. Mêmes dessins, textes, minutage et transitions :
# seuls l'échelle et la position des blocs changent. Une boîte = (échelle, tx, ty)
# appliquée à la scène de référence 1920 x 1080.
LAYOUTS = {
    "9x16": dict(
        s1_box=(1.15, -1047, 500), s1_title=(108, 330, 74), s1_sun=(1300, 210),
        s3_cam=(-35, 832, -245.9, 1000), s3_hud=(556, 597), s3_title=(108, 330, 58),
        handoff=(220, 641, 640),
        s4_settle=(60, 560, 960), s4_title=(108, 330, 56), s4_title_text="Chaque anomalie est|détectée et localisée.",
        s4_rows=(1380, 1490, 1600), s4_order=(2, 0, 1), s4_fs=(34, 28), s4_band_col=0.8,
        s4_lab=(("r", 1020, 480), ("l", 332, 520), ("l", 108, 560)),
        s5_title=(108, 300, 64), s5_doc=(0.8, 124, 423.2), s5_chart=(0.8, -556, 975.6), s5_stamp=36, s5_pfs=35,
        s5_fs=dict(item=35, head=36, tick=36, label=38, cat=36, catlh=44),
    ),
    "1x1": dict(
        s1_box=(0.98, -817.3, 87.6), s1_title=(108, 120, 56), s1_sun=(1640, 230),
        s3_cam=(-35, 832, 87.4, 1000), s3_hud=(556, 236), s3_title=(108, 108, 52),
        handoff=(270, 380, 540),
        s4_settle=(204, 170, 672), s4_title=(108, 90, 40), s4_title_text="Chaque anomalie est détectée et localisée.",
        s4_rows=(750, 825, 900), s4_order=(2, 0, 1), s4_fs=(30, 28), s4_band_col=0.8,
        s4_lab=(("r", 1000, 420), ("l", 385, 480), ("l", 108, 560)),
        s5_title=(108, 150, 52), s5_doc=(0.7, -90, 232.8), s5_chart=(0.58, -10, 175.6), s5_stamp=40, s5_pfs=40,
        s5_fs=dict(item=49, head=40, tick=49, label=49, cat=49, catlh=58),
    ),
}
L = LAYOUTS.get(FMT)


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
      // SVG de zoom (non-scaling-stroke) : les tirets sont posés à l'échelle de l'écran, le motif suit donc
      // l'échelle de l'SVG au moment du tracé (data-dash), sinon la fin du trait n'apparaît qu'au passage en plein.
      const dk = (el) => { const z = el.closest ? el.closest("svg[data-dash]") : null; return z ? parseFloat(z.getAttribute("data-dash")) : 1; };
      $$("svg[data-dash] .d").forEach((el) => {
        const k = dk(el);
        el.style.strokeDasharray = k + " " + 1.2 * k;
        el.setAttribute("stroke-dashoffset", 1.05 * k);
      });
      const draw = (t, els, d = 0.8, ease = "power2.inOut", stagger = 0) =>
        tl.fromTo(els, { attr: { "stroke-dashoffset": (i, el) => 1.05 * dk(el) } }, { attr: { "stroke-dashoffset": 0 }, duration: d, ease, stagger }, t);
      const undraw = (t, els, d = 0.5, ease = "power3.in", stagger = 0) =>
        tl.to(els, { attr: { "stroke-dashoffset": (i, el) => -1.15 * dk(el) }, duration: d, ease, stagger }, t);
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


def dash_k(view_box):
    """Échelle écran / monde d'un SVG plein cadre pour une viewBox donnée (preserveAspectRatio « meet »)."""
    return round(min(W / view_box[2], H / view_box[3]), 5)


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
    path = os.path.join(OUT, "compositions", f"{sid}.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print("wrote", os.path.relpath(path, ROOT))


def box(content, b):
    """Place un bloc de la scène de référence dans le cadre de la déclinaison."""
    if b is None:
        return content
    sc, tx, ty = b
    return (
        f'    <div class="box" data-layout-allow-overflow style="position: absolute; left: 0; top: 0; width: {SW}px; height: {SH}px; '
        f'transform-origin: 0 0; transform: translate({n(tx)}px, {n(ty)}px) scale({sc})">\n{content}\n    </div>'
    )


def tstyle(spec, default):
    """Style inline d'un titre : celui du 16:9, ou (left, top, taille) de la déclinaison."""
    if L is None:
        return default
    left, top, size = spec
    return f"left: {left}px; top: {top}px; font-size: {size}px"


def svar(vid, label, default):
    return {"id": vid, "type": "string", "label": label, "default": default}


# --------------------------------------------------------------------------
# Solar field geometry (S3 world), shared by S3, S4, S5
# --------------------------------------------------------------------------
PW, PH = 210, 160  # panel
GX, GY = 12, 28  # gaps
COLS, ROWS = 7, 3
FX0, FY0 = 230, 412  # field origin
CC, CR = 8, 6  # cellules par module (cellules presque carrées, 26 x 27)
HERO = (1, 4)  # (row, col) zoomed panel

# anomalies par module, en cellules (colonne, ligne) — signatures thermiques de la note technique (IEC TS 62446-3)
ANOM = {
    (0, 1): [("spot", 3, 2)],  # point chaud ponctuel
    (1, 4): [("crack", 2, 4), ("band", 0), ("jbox",)],  # module zoomé en S4 : cellule fissurée, sous-chaîne, boîte de jonction
    (2, 2): [("module",)],  # module fonctionnant à vide : échauffement uniforme
    (2, 5): [("cell", 1, 2), ("cell", 1, 3)],  # cellules isolées plus chaudes
    (0, 6): [("spot", 6, 0)],
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


CWU, CHU = PW / CC, PH / CR  # taille d'une cellule (échelle S3)


def anom_center(kind, *a):
    """Point d'ancrage d'une anomalie dans le repère du module (échelle S3)."""
    if kind in ("spot", "cell"):
        return (a[0] + 0.5) * CWU, (a[1] + 0.5) * CHU
    if kind == "crack":
        return (a[0] + 0.5) * CWU, (a[1] + 0.52) * CHU
    if kind == "band":  # sur la sous-chaîne, à l'abscisse choisie par format
        return (L["s4_band_col"] if L else 5.5) * CWU, (a[0] + 1) * CHU
    if kind == "jbox":
        return PW - 0.62 * CWU, PH / 2
    return PW / 2, PH / 2


def anom_anchor(kind, *a):
    """Départ de la ligne de rappel : bord droit (16:9, lignes horizontales) ou bas (déclinaisons, lignes verticales)."""
    if kind == "crack":
        i, j = a
        return ((i + 0.5) * CWU, (j + 1) * CHU) if L else ((i + 1) * CWU, (j + 0.52) * CHU)
    if kind == "jbox":
        return (PW - 0.62 * CWU, PH / 2 + 0.48 * CHU) if L else (PW - 0.36 * CWU, PH / 2)
    return anom_center(kind, *a)


def hval(*k):
    """Valeur pseudo-aléatoire déterministe dans [0, 1[ (variation d'une cellule à l'autre)."""
    h = 2166136261
    for v in k:
        h = ((h ^ (v & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return (h % 10007) / 10007


def cell_tint(r, c, ox, oy, s):
    """Thermogramme : chaque cellule a sa propre température, à peine différente de ses voisines.
    Cellules regroupées par nuance (6 niveaux) : un seul tracé par nuance, pour alléger la page."""
    cw, ch = CWU * s, CHU * s
    levels = {}
    for j in range(CR):
        for i in range(CC):
            lv = min(5, int(hval(r, c, i, j) * 6))
            levels.setdefault(lv, []).append(f"M{n(ox + i * cw)} {n(oy + j * ch)}h{n(cw)}v{n(ch)}h{n(-cw)}Z")
    return "".join(f'<path d="{"".join(d)}" fill="{ACC}" fill-opacity="{0.015 + 0.055 * (lv + 0.5) / 6:.3f}"/>'
                   for lv, d in sorted(levels.items()))


def anomalies_svg(r, c, ox, oy, s, prefix, hero_ids=False):
    """Anomalies thermiques du module (r, c), dessinées à l'origine (ox, oy) et à l'échelle s."""
    cw, ch = CWU * s, CHU * s

    def cellrect(i, j, op):
        return (f'<rect x="{n(ox + i * cw)}" y="{n(oy + j * ch)}" width="{n(cw)}" height="{n(ch)}" '
                f'fill="{ACC}" fill-opacity="{op:.3f}"/>')

    out = []
    for k, (kind, *a) in enumerate(ANOM.get((r, c), [])):
        ax, ay = anom_center(kind, *a)
        x, y = ox + ax * s, oy + ay * s
        idattr = f' id="{prefix}-a{k}"' if hero_ids else ""
        g = f'<g{idattr} class="{prefix}-anom" data-x="{n(x)}">'
        if kind == "spot":  # point chaud : la cellule chauffe, cœur carré très chaud, diffusion autour
            i, j = a
            out.append(g + cellrect(i, j, 0.3)
                       + f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(0.8 * cw)}" fill="url(#{prefix}-hot)" fill-opacity="0.7"/>'
                       + f'<rect x="{n(x - 0.17 * cw)}" y="{n(y - 0.17 * cw)}" width="{n(0.34 * cw)}" height="{n(0.34 * cw)}" '
                       f'rx="{n(0.07 * cw)}" fill="{ACC}"/></g>')
        elif kind == "crack":  # cellule fissurée : points chauds alignés sur la fissure
            i, j = a
            x0, y0 = ox + i * cw, oy + j * ch
            spots = [(0.3, 0.28, 0.26), (0.53, 0.55, 0.36), (0.72, 0.8, 0.22)]
            out.append(
                g + cellrect(i, j, 0.34)
                + "".join(f'<circle cx="{n(x0 + u * cw)}" cy="{n(y0 + v * ch)}" r="{n(rr * cw)}" fill="url(#{prefix}-hot)"/>'
                          for u, v, rr in spots)
                + "".join(f'<circle cx="{n(x0 + u * cw)}" cy="{n(y0 + v * ch)}" r="{n(rr * 0.22 * cw)}" fill="{ACC}"/>'
                          for u, v, rr in spots)
                + "</g>")
        elif kind == "band":  # sous-chaîne court-circuitée par sa diode by-pass : un tiers du module plus chaud
            j0 = a[0]
            out.append(g + "".join(cellrect(i, j, 0.22 + 0.08 * hval(r, c, i, j, 7)) for j in (j0, j0 + 1) for i in range(CC))
                       + "</g>")
        elif kind == "jbox":  # boîte de jonction en surchauffe, au dos, vue à travers le module
            out.append(g + f'<ellipse cx="{n(x)}" cy="{n(y)}" rx="{n(0.6 * cw)}" ry="{n(1.0 * ch)}" fill="url(#{prefix}-hot)" fill-opacity="0.8"/>'
                       + f'<rect x="{n(x - 0.18 * cw)}" y="{n(y - 0.38 * ch)}" width="{n(0.36 * cw)}" height="{n(0.76 * ch)}" '
                       f'rx="{n(0.12 * cw)}" fill="{ACC}" fill-opacity="0.85"/></g>')
        elif kind == "cell":  # cellule isolée plus chaude
            i, j = a
            out.append(g + cellrect(i, j, 0.42) + "</g>")
        elif kind == "module":  # module à vide : tout le module chauffe
            out.append(g + "".join(cellrect(i, j, 0.13 + 0.06 * hval(r, c, i, j, 3)) for j in range(CR) for i in range(CC))
                       + "</g>")
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
        f'<linearGradient id="{prefix}-band" x1="0" x2="1" y1="0" y2="0">'
        f'<stop offset="0" stop-color="{ACC}" stop-opacity="0.28"/>'
        f'<stop offset="0.5" stop-color="{ACC}" stop-opacity="0.72"/>'
        f'<stop offset="1" stop-color="{ACC}" stop-opacity="0.28"/></linearGradient>'
    )


def th_fill(r, c):
    return TH_PANEL if (r + c) % 2 == 0 else TH_PANEL_B


# hero panel in S4 world (used by S4 and S5 so the hand-off is exact)
S4PW, S4PH = PW * K, PH * K  # 960 x 731.43
HERO_ANCH = [(S4X + ax * K, S4Y + ay * K) for kind, *a in ANOM[HERO] for ax, ay in [anom_anchor(kind, *a)]]  # monde S4
S4_LABELS = [  # texte principal | précision technique (note technique, § 3.2 et 3.7)
    "Point chaud (hot-spot)|cellule fissurée",
    "Diode by-pass défectueuse|échauffement linéaire",
    "Boîte de jonction|connexion en surchauffe",
]


def hero_panel_svg(prefix, with_ids=True):
    x, y, w, h = S4X, S4Y, S4PW, S4PH
    pid = (lambda s: f' id="{prefix}-{s}"') if with_ids else (lambda s: "")
    return (
        f'<g{pid("panel")}>'
        f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="{th_fill(*HERO)}"/>'
        + cell_tint(*HERO, x, y, K)
        + f'<path{pid("bus")} d="{busbars(x, y, w, h)}" stroke="#FFDCCB" stroke-width="1" fill="none"/>'
        + anomalies_svg(*HERO, x, y, K, prefix, hero_ids=with_ids)
        + f'<path d="{cell_lines(x, y, w, h)}" stroke="{TH_CELL}" stroke-width="1" fill="none"/>'
        + f'<rect{pid("inner")} x="{n(x + 14)}" y="{n(y + 14)}" width="{n(w - 28)}" height="{n(h - 28)}" '
        f'fill="none" stroke="{INK}" stroke-width="1.2"/>'
        f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="none" stroke="{INK}" stroke-width="2"/>'
        "</g>"
    )


def cell_box(i0, j0, i1, j1, m):
    """Cadre de détection (monde S4) autour des cellules i0..i1 x j0..j1, marge m en cellules."""
    cw, ch = CWU * K, CHU * K
    return (S4X + (i0 - m) * cw, S4Y + (j0 - m) * ch, (i1 - i0 + 1 + 2 * m) * cw, (j1 - j0 + 1 + 2 * m) * ch)


BOX1 = cell_box(2, 4, 2, 4, 0.3)  # défaut n°1 : la cellule fissurée
BOX2 = cell_box(0, 0, CC - 1, 1, -0.14)  # défaut n°2 : la sous-chaîne (deux rangées)


# viewBoxes for the zoom hand-offs (rectangles à l'écran du panneau défectueux)
HAND = L["handoff"] if L else (645, 320, 630)  # raccord S3 -> S4
k3 = HAND[2] / PW
S3_END_VB = (HX - HAND[0] / k3, HY - HAND[1] / k3, W / k3, H / k3)
k4 = HAND[2] / S4PW
S4_START_VB = (S4X - HAND[0] / k4, S4Y - HAND[1] / k4, W / k4, H / k4)
SETTLE = L["s4_settle"] if L else (S4X, S4Y, S4PW)  # panneau posé en S4
ks = SETTLE[2] / S4PW
S4_SETTLE_VB = (S4X - SETTLE[0] / ks, S4Y - SETTLE[1] / ks, W / ks, H / ks)
THUMB = (260, 200, 520)  # x, y, largeur de la vignette du rapport (scène de référence)
k5 = THUMB[2] / S4PW
THUMB_LOCAL_VB = (S4X - THUMB[0] / k5, S4Y - THUMB[1] / k5, SW / k5, SH / k5)
if L:  # vignette vue à l'écran à travers la boîte du rapport
    _ds, _dx, _dy = L["s5_doc"]
    THUMB_SCREEN = (_ds * THUMB[0] + _dx, _ds * THUMB[1] + _dy, _ds * THUMB[2])
else:
    THUMB_SCREEN = THUMB
k5s = THUMB_SCREEN[2] / S4PW
S4_END_VB = (S4X - THUMB_SCREEN[0] / k5s, S4Y - THUMB_SCREEN[1] / k5s, W / k5s, H / k5s)


def vb(t):
    return " ".join(n(v) for v in t)


# --------------------------------------------------------------------------
# Logo (vector redraw of the Fly Scan'Air PNG) — logo coords 1270 x 430
# --------------------------------------------------------------------------
P0 = {  # titre d'ouverture (taille du corps, texte : | = retour ligne, *mot* = orange)
    "16x9": dict(size=76, text="Le contrôle *thermographique*|appliqué aux installations|photovoltaïques"),
    "9x16": dict(size=74, text="Le contrôle|*thermographique*|appliqué aux|installations|photovoltaïques"),
    "1x1": dict(size=60, text="Le contrôle|*thermographique* appliqué|aux installations|photovoltaïques"),
}[FMT]
P2 = {  # installation au centre : échelle du champ, ellipse de l'orbite (rayons), rayon d'une pastille, corps des légendes,
    #   angles de départ (degrés, sens horaire depuis la droite), angle parcouru pendant la scène, angle d'arrivée en spirale,
    #   angle de sortie, excentricité apparente (accélération au passage devant), profondeur (pastille plus grande devant).
    # Les ellipses et les arcs sont choisis pour qu'aucune légende ne passe sur l'installation ni ne sorte du cadre :
    # tour complet en 16:9 ; en 9:16 et 1:1, trois pictogrammes sur l'arc du haut et trois sur l'arc du bas.
    "16x9": dict(s=0.52, rx=760, ry=405, r=56, lf=31, a0=(-90, -30, 30, 90, 150, 210), sweep=80, ain=-100, aout=45, ecc=0.15, dep=0.08),
    "9x16": dict(s=0.42, rx=350, ry=660, r=54, lf=32, a0=(-158, -104, -50, 22, 76, 130), sweep=36, ain=-40, aout=12, ecc=0.0, dep=0.06),
    "1x1": dict(s=0.38, rx=380, ry=360, r=46, lf=30, a0=(-146, -103, -60, 32, 75, 118), sweep=28, ain=-40, aout=12, ecc=0.0, dep=0.06),
}[FMT]
P6 = {  # plateforme en ligne : titre (gauche, haut, corps), fenêtre à l'écran (x, y, l, h), volets en coordonnées fenêtre
    "16x9": dict(title=(120, 50, 48), text="Suivez votre installation|sur notre *plateforme en ligne*.",
                 win=(120, 196, 1680, 836), bar=60, ui=22, rh=38,
                 map=(20, 76, 824, 740), list=(860, 76, 800, 362), detail=(860, 454, 800, 362)),
    "9x16": dict(title=(108, 130, 58), text="Suivez votre|installation sur notre|*plateforme en ligne*.",
                 win=(40, 410, 1000, 1460), bar=64, ui=26, rh=50,
                 map=(16, 80, 968, 500), list=(16, 596, 968, 466), detail=(16, 1078, 968, 366)),
    "1x1": dict(title=(60, 40, 40), text="Suivez votre installation|sur notre *plateforme en ligne*.",
                win=(40, 170, 1000, 880), bar=52, ui=20, rh=33,
                map=(14, 64, 480, 802), list=(506, 64, 480, 321), detail=(506, 399, 480, 467)),
}[FMT]
P7 = {  # « Retrouvez-nous sur… » : titre (haut, corps), barre (largeur, hauteur, centre y au départ, centre y après la recherche),
    #   résultats (haut, largeur max, hauteur max de l'image), barre du navigateur, corps du texte tapé
    "16x9": dict(head=(392, 56), bar=(1100, 92, 540, 154), res=(248, 1500, 680), chrome=44, fs=38),
    "9x16": dict(head=(770, 62), bar=(960, 110, 960, 590), res=(705, 1000, 640), chrome=50, fs=42),
    "1x1": dict(head=(400, 50), bar=(900, 84, 540, 205), res=(277, 1000, 600), chrome=40, fs=34),
}[FMT]
P8 = {  # carton final : échelle et haut du logo (position finale), slogan (haut, corps) — ensemble centré dans le cadre
    "16x9": dict(s=0.72, y=289, slogan=(659, 56), text="Inspections techniques aériennes,|*révélez l’invisible*."),
    "9x16": dict(s=0.7, y=668, slogan=(1039, 60), text="Inspections techniques|aériennes,|*révélez l’invisible*."),
    "1x1": dict(s=0.6, y=297, slogan=(605, 50), text="Inspections techniques|aériennes,|*révélez l’invisible*."),
}[FMT]
LOGO_S = P8["s"]
LOGO_X = (W - 1270 * LOGO_S) / 2
LOGO_Y = P8["y"]
LOGO_Y0 = (H - 430 * LOGO_S) / 2  # logo centré dans le cadre, avant sa remontée
ICONS = json.load(open(os.path.join(ROOT, "assets", "icons-phosphor.json"), encoding="utf-8"))["icons"]
# Mesures prises sur le logo fourni (assets/images/logo-flyscanair.png, même repère) :
# billes, axes des 9 verticales du serpentin, haut et bas des boucles, cadre de droite.
BALL_L = (29, 225.5)
BALL_R = (1102.5, 165.5)  # = le point du « i » : la bille est centrée sur la tige (x 1089–1117)
BALL_RAD = 13
COIL_XS = [126.5, 194.5, 263.5, 332, 401, 469, 537.5, 606, 675]
COIL_TOP, COIL_BOT = 39.5, 410.5  # axe du trait au sommet / au creux des boucles
LOGO_LETTERS = json.load(open(os.path.join(ROOT, "assets", "logo-letters.json"), encoding="utf-8"))["d"]  # tools/logo_trace.py


def logo_coil_path():
    xs = COIL_XS
    d = [f"M{BALL_L[0]} {BALL_L[1]}", "H86", f"Q{xs[0]} {BALL_L[1]} {xs[0]} 266"]
    for i in range(len(xs) - 1):
        a, b = xs[i], xs[i + 1]
        r = (b - a) / 2
        if i % 2 == 0:  # creux de boucle, puis remontée
            d.append(f"V{n(COIL_BOT - r)}")
            d.append(f"A{n(r)} {n(r)} 0 0 0 {n(b)} {n(COIL_BOT - r)}")
        else:  # sommet de boucle, puis descente
            d.append(f"V{n(COIL_TOP + r)}")
            d.append(f"A{n(r)} {n(r)} 0 0 1 {n(b)} {n(COIL_TOP + r)}")
    d += ["V290", f"Q{xs[-1]} 340 725 340", "H1200", "Q1248 340 1248 292", "V214",
          f"Q1248 {BALL_R[1]} 1200 {BALL_R[1]}", f"H{BALL_R[0]}"]
    return " ".join(d)


def logo_screen(x, y):
    return LOGO_X + x * LOGO_S, LOGO_Y + y * LOGO_S


# --------------------------------------------------------------------------
# S0 — Titre d'ouverture (sans voix)
# --------------------------------------------------------------------------
def build_s0():
    size, text = P0["size"], P0["text"]
    nl = text.count("|") + 1
    top = (H - nl * size * 1.14) / 2 - size * 0.25
    ly = top + nl * size * 1.14 + size * 0.55  # filet orange sous le titre
    body = f"""    <div id="s0-title" class="title s0t" style="top: {n(top)}px; font-size: {size}px"></div>
    <svg class="world" viewBox="0 0 {W} {H}" width="{W}" height="{H}"{CANVAS}>
      <line id="s0-rule" class="d" pathLength="1" x1="{n(W / 2 - 90)}" y1="{n(ly)}" x2="{n(W / 2 + 90)}" y2="{n(ly)}" stroke="{ACC}" stroke-width="6" stroke-linecap="round"/>
    </svg>"""
    css = f"""
    #root .s0t {{ left: 0; width: {W}px; text-align: center; line-height: 1.14; }}"""
    js = f"""
      const title = words($("#s0-title"), txt("s0-title", "{text}"));
      blurIn(0.15, title, 0.22, 0.06, 8);
      draw(0.75, $("#s0-rule"), 0.6, "power2.out");
      // sortie : le titre se floute, le filet se dé-trace vers la droite
      blurOut(3.05, title, 0.2, 0.015);
      undraw(3.05, $("#s0-rule"), 0.35, "power3.in");"""
    write_scene("s0", "Scène 0 — Titre d'ouverture", [svar("s0-title", "Scène 0 — titre (| = retour ligne, *mot* = orange)", text)],
                css, body, js)


# --------------------------------------------------------------------------
# S1 — Le problème invisible
# --------------------------------------------------------------------------
def s1_ground():
    """Ligne de sol : en déclinaison, elle couvre le cadre (40 -> W-40 px à l'écran)."""
    if L is None:
        return 120, 1800
    sc, tx, _ = L["s1_box"]
    return (40 - tx) / sc, (W - 40 - tx) / sc


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

    sun_c = L["s1_sun"] if L else (1300, 210)
    rays = []
    for i in range(8):
        import math

        a = math.radians(i * 45 - 90)
        x1, y1 = sun_c[0] + 50 * math.cos(a), sun_c[1] + 50 * math.sin(a)
        x2, y2 = sun_c[0] + 72 * math.cos(a), sun_c[1] + 72 * math.sin(a)
        rays.append(f'<line class="d s1-ray" pathLength="1" x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}"/>')

    gx1, gx2 = s1_ground()
    svg = f"""    <svg class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">
      <defs>{thermal_defs("s1")}</defs>
      <g fill="none" stroke="{INK}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line id="s1-ground" class="d" pathLength="1" x1="{n(gx1)}" y1="880" x2="{n(gx2)}" y2="880"/>
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
    </svg>"""
    body = box(svg, L["s1_box"] if L else None) + f"""
    <div id="s1-title" class="title" style="{tstyle(L and L["s1_title"], "left: 140px; top: 352px")}">Certaines anomalies<br />sont invisibles<br />à l’œil nu.</div>"""

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
      fadeOut(6.6, $$(".s1-wfill"), 0.4);
      undraw(6.5, $("#s1-ground"), 0.5, "power3.in");"""
    write_scene(
        "s1",
        "Scène 1 — Le problème invisible",
        [svar("s1-title", "Scène 1 — titre (| = retour ligne, *mot* = orange)", "Certaines anomalies|sont *invisibles*|à l’œil nu.")],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# S2 — Les enjeux : l'installation (pas encore inspectée) au centre, six pictogrammes en orbite
# --------------------------------------------------------------------------
FIELD_C = (FX0 + (COLS * PW + (COLS - 1) * GX) / 2, FY0 + (ROWS * PH + (ROWS - 1) * GY) / 2)  # centre du champ (monde S3)
S2_VB = (FIELD_C[0] - W / 2 / P2["s"], FIELD_C[1] - H / 2 / P2["s"], W / P2["s"], H / P2["s"])
if L:  # caméra de la scène 3 : cadre vertical / carré qui suit le drone
    _cx0, _cx1, _cy, _cvw = L["s3_cam"]
    S3_VB0 = (_cx0, _cy, _cvw, _cvw * H / W)
    S3_VB1 = (_cx1, _cy, _cvw, _cvw * H / W)
else:
    S3_VB0 = S3_VB1 = (0, 0, W, H)
S2_PICTOS = [  # légende, icône Phosphor (assets/icons-phosphor.json), dans l'ordre d'apparition (sens horaire)
    ("Perte de rendement", "trend-down"),
    ("Échauffement", "thermometer-hot"),
    ("Défaut électrique", "lightning"),
    ("Risque incendie", "fire"),
    ("Garantie", "seal-check"),
    ("Assurance", "shield-check"),
]
QUESTION = "Comment détecter|ces *anomalies* ?"  # raccord S2 -> S3 : même place, même texte


def field_normal(prefix, drawn):
    """Champ de 7 x 3 modules, aspect « visible » (avant le scan). drawn : contours déjà tracés (pas d'animation)."""
    out = []
    for c in range(COLS):
        for r in range(ROWS):
            x, y = panel_xy(r, c)
            line = "" if drawn else f'class="d {prefix}-pline" pathLength="1" '
            out.append(
                f'<rect class="{prefix}-pfill" x="{x}" y="{y}" width="{PW}" height="{PH}" fill="{PANEL}"/>'
                f'<path class="{prefix}-cells" d="{cell_lines(x, y, PW, PH)}" stroke="{CELL}" stroke-width="1" fill="none"/>'
                f'<rect {line}x="{x}" y="{y}" width="{PW}" height="{PH}" fill="none" stroke="{INK}" stroke-width="2"/>'
            )
    return "".join(out)


def question_html(sid):
    ign = " data-layout-ignore" if sid == "s2" else ""  # en S2 la question ne fait qu'apparaître : elle reste affichée en S3
    return (f'<div id="{sid}-q" class="title"{ign} style="{tstyle(L and L["s3_title"], "left: 140px; top: 120px")}">'
            f'Comment détecter<br />ces anomalies ?</div>')


def build_s2():
    r, lf = P2["r"], P2["lf"]
    pictos = []
    for i, (label, icon) in enumerate(S2_PICTOS):
        lab = f"top: {n(r + 12)}px"  # légende sous la pastille
        pictos.append(
            f'<div id="s2-k{i}" class="pk" data-layout-allow-overflow><div class="pk-in">'
            f'<div class="pk-c" style="left: {-r}px; top: {-r}px; width: {2 * r}px; height: {2 * r}px">'
            f'<svg viewBox="0 0 256 256" width="{n(r * 1.06)}" height="{n(r * 1.06)}"><path d="{ICONS[icon]}" fill="{ACC}"/></svg></div>'
            f'<div class="pk-l" style="{lab}; font-size: {lf}px">{label}</div></div></div>')
    body = f"""    <svg id="s2-svg" class="world zoom" data-dash="{dash_k(S2_VB)}" viewBox="{vb(S2_VB)}" width="{W}" height="{H}"{CANVAS}>
      <g id="s2-field">{field_normal("s2", drawn=False)}</g>
    </svg>
    <svg class="world" viewBox="0 0 {W} {H}" width="{W}" height="{H}"{CANVAS}>
      <ellipse id="s2-orbit" cx="{n(W / 2)}" cy="{n(H / 2)}" rx="{P2["rx"]}" ry="{P2["ry"]}" fill="none" stroke="#C9CBD1" stroke-width="2.5" stroke-dasharray="2 16" stroke-linecap="round"/>
    </svg>
    {"".join(pictos)}
    {question_html("s2")}"""
    css = f"""
    #root .pk {{ position: absolute; left: 0; top: 0; width: 0; height: 0; }}
    #root .pk-in {{ position: absolute; left: 0; top: 0; width: 0; height: 0; transform-origin: 0 0; opacity: 0; }}
    #root .pk-l {{ opacity: 0; }}
    #root .pk-c {{ position: absolute; box-sizing: border-box; border-radius: 50%; background: #FFFFFF; border: 2.5px solid #111111; display: flex; align-items: center; justify-content: center; }}
    #root .pk-l {{ position: absolute; left: -260px; width: 520px; text-align: center; font-family: "Comfortaa", sans-serif; font-weight: 700; line-height: 1.2; color: #111111; white-space: nowrap; }}
    #root .s2-pfill, #root .s2-cells, #root #s2-orbit {{ opacity: 0; }}"""
    js = f"""
      const q = words($("#s2-q"), txt("s3-q", "{QUESTION}"));
      // 1. l'installation se dessine au centre de l'écran (le même champ que le survol, pas encore inspecté)
      draw(0.05, $$(".s2-pline"), 0.5, "power2.inOut", 0.03);
      fadeIn(0.25, $$(".s2-pfill"), 0.4, 0.03);
      fadeIn(0.55, $$(".s2-cells"), 0.5, 0.02);
      solid(1.5, $$(".s2-pline"));
      // 2. six pictogrammes viennent graviter autour (orbite elliptique, sens horaire)
      const orbit = $("#s2-orbit");
      fadeIn(0.55, orbit, 0.6);
      tl.fromTo(orbit, {{ attr: {{ "stroke-dashoffset": 0 }} }}, {{ attr: {{ "stroke-dashoffset": -160 }}, duration: 6.6, ease: "none" }}, 0);
      // orbite : angle = départ + rotation lente + arrivée en spirale + sortie ; un peu plus vite quand le pictogramme
      // passe devant (bas de l'ellipse), un peu plus grand aussi (profondeur)
      const CX = {n(W / 2)}, CY = {n(H / 2)}, RX = {P2["rx"]}, RY = {P2["ry"]};
      const A0 = {list(P2["a0"])}, SWEEP = {P2["sweep"]}, AIN = {P2["ain"]}, AOUT = {P2["aout"]}, ECC = {P2["ecc"]}, DEP = {P2["dep"]};
      const K = $$(".pk");
      K.forEach((el, i) => {{ const v = txt("s2-k" + i, ""); if (v) el.querySelector(".pk-l").textContent = v; }});
      const G = {{ p: 0 }};
      const st = K.map(() => ({{ ea: 0, er: 0, xa: 0, xr: 0 }}));
      const D = Math.PI / 180;
      const place = (i) => {{
        const s_ = st[i];
        const lin = A0[i] + SWEEP * G.p + AIN * (1 - s_.ea) + AOUT * s_.xa;
        const th = (lin + (ECC / D) * Math.sin(lin * D - Math.PI / 2)) * D;
        const rf = 1 + 1.3 * (1 - s_.er) + 1.1 * s_.xr;
        const k = 1 + DEP * Math.sin(th);
        K[i].style.transform = "translate(" + (CX + RX * rf * Math.cos(th)).toFixed(2) + "px, " + (CY + RY * rf * Math.sin(th)).toFixed(2) + "px) scale(" + k.toFixed(4) + ")";
      }};
      const placeAll = () => K.forEach((el, i) => place(i));
      placeAll();
      tl.fromTo(G, {{ p: 0 }}, {{ p: 1, duration: 6.6, ease: "none", onUpdate: placeAll }}, 0);
      K.forEach((el, i) => {{
        const pin = el.querySelector(".pk-in"), lab = el.querySelector(".pk-l");
        const t = 0.7 + i * 0.32, tx = 5.05 + i * 0.05;
        // 2a. capture : le pictogramme arrive de loin en spirale et se place sur l'orbite
        tl.fromTo(st[i], {{ ea: 0 }}, {{ ea: 1, duration: 1.2, ease: "power2.out", onUpdate: () => place(i), immediateRender: false }}, t);
        tl.fromTo(st[i], {{ er: 0 }}, {{ er: 1, duration: 1.2, ease: "power3.out", onUpdate: () => place(i), immediateRender: false }}, t);
        tl.fromTo(pin, {{ opacity: 0, scale: 0.55 }}, {{ opacity: 1, scale: 1, duration: 0.7, ease: "power2.out" }}, t);
        fadeIn(t + 0.75, lab, 0.3);
        // 3. échappement : la légende s'efface, le pictogramme repart en s'éloignant de plus en plus vite
        fadeOut(tx, lab, 0.15);
        tl.fromTo(st[i], {{ xa: 0 }}, {{ xa: 1, duration: 0.6, ease: "power2.in", onUpdate: () => place(i), immediateRender: false }}, tx);
        tl.fromTo(st[i], {{ xr: 0 }}, {{ xr: 1, duration: 0.6, ease: "power2.in", onUpdate: () => place(i), immediateRender: false }}, tx);
        tl.to(pin, {{ opacity: 0, scale: 0.8, duration: 0.45, ease: "power2.in" }}, tx + 0.12);
      }});
      fadeOut(5.2, orbit, 0.4);
      // 4. la caméra se rapproche : l'installation prend la place du survol (scène 3), la question s'affiche
      tl.fromTo($("#s2-svg"), {{ attr: {{ viewBox: "{vb(S2_VB)}" }} }}, {{ attr: {{ viewBox: "{vb(S3_VB0)}" }}, duration: 1.2, ease: "power2.inOut" }}, 5.35);
      blurIn(5.85, q, 0.15, 0.067);"""
    write_scene(
        "s2",
        "Scène 2 — Les enjeux : installation au centre, pictogrammes en orbite",
        [svar("s3-q", "Scènes 2-3 — question (| = retour ligne, *mot* = orange)", QUESTION)]
        + [svar(f"s2-k{i}", f"Scène 2 — pictogramme {i + 1}", lab) for i, (lab, _) in enumerate(S2_PICTOS)],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# S3 — Inspection drone
# --------------------------------------------------------------------------
HOVER_X, SCAN_END_X, DRONE_Y = 215, 1790, 680


def drone_svg():
    """Drone vu de dessus, réduit à l'essentiel : corps, deux bras, quatre rotors, objectif."""
    rot = [(-100, -76), (100, -76), (-100, 76), (100, 76)]
    rotors = "".join(
        f'<g transform="translate({x} {y})">'
        f'<circle r="50" fill="#FFFFFF" fill-opacity="0.75" stroke="{INK}" stroke-width="2"/>'
        f'<g class="s3-blade"><line x1="-40" y1="0" x2="40" y2="0" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/></g>'
        "</g>"
        for x, y in rot
    )
    return f"""<g id="s3-drone">
          <line x1="-100" y1="-76" x2="100" y2="76" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>
          <line x1="100" y1="-76" x2="-100" y2="76" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>
          {rotors}
          <rect x="-44" y="-30" width="88" height="60" rx="16" fill="#FFFFFF" stroke="{INK}" stroke-width="2.5"/>
          <circle cx="30" cy="0" r="7" fill="{ACC}"/>
        </g>"""


def build_s3():
    thermal = []
    anom_xs = []
    for c in range(COLS):
        for r in range(ROWS):
            x, y = panel_xy(r, c)
            thermal.append(
                f'<rect x="{x}" y="{y}" width="{PW}" height="{PH}" fill="{th_fill(r, c)}"/>'
                + cell_tint(r, c, x, y, 1)
                + anomalies_svg(r, c, x, y, 1, "s3")
                + f'<path d="{cell_lines(x, y, PW, PH)}" stroke="{TH_CELL}" stroke-width="1" fill="none"/>'
                + f'<rect x="{x}" y="{y}" width="{PW}" height="{PH}" fill="none" stroke="{INK}" stroke-width="2"/>'
            )
            for kind, *a in ANOM.get((r, c), []):
                if kind in ("spot", "crack"):
                    ax, ay = anom_center(kind, *a)
                    anom_xs.append((x + ax, y + ay))
    rings = "".join(
        f'<circle class="s3-ring" data-x="{n(x)}" cx="{n(x)}" cy="{n(y)}" r="16" fill="none" stroke="{ACC}" stroke-width="2"/>'
        for x, y in anom_xs
    )
    fy0, fy1 = FY0 - 20, FY0 + ROWS * PH + (ROWS - 1) * GY + 20
    body = f"""    <svg id="s3-svg" class="world zoom" data-dash="{dash_k(S3_VB0)}" viewBox="{vb(S3_VB0)}" width="{W}" height="{H}"{CANVAS}>
      <defs>
        {thermal_defs("s3")}
        <linearGradient id="s3-trail" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stop-color="{ACC}" stop-opacity="0"/>
          <stop offset="1" stop-color="{ACC}" stop-opacity="0.16"/>
        </linearGradient>
        <clipPath id="s3-clip"><rect id="s3-cliprect" x="{HOVER_X}" y="{fy0}" width="0" height="{fy1 - fy0}"/></clipPath>
      </defs>
      <g id="s3-normal">{field_normal("s3", drawn=True)}</g>
      <g id="s3-thermal" clip-path="url(#s3-clip)">{"".join(thermal)}{rings}</g>
      <g id="s3-scan">
        <rect x="-120" y="{fy0}" width="120" height="{fy1 - fy0}" fill="url(#s3-trail)"/>
        <line x1="0" y1="{fy0}" x2="0" y2="{fy1}" stroke="{ACC}" stroke-width="3"/>
        <line x1="-12" y1="{fy0}" x2="12" y2="{fy0}" stroke="{ACC}" stroke-width="3"/>
        <line x1="-12" y1="{fy1}" x2="12" y2="{fy1}" stroke="{ACC}" stroke-width="3"/>
      </g>
      {drone_svg()}
      <polyline id="s3-leader" class="d" pathLength="1" points="{HOVER_X},{DRONE_Y - 34} {HOVER_X},331 470,331" fill="none" stroke="{INK}" stroke-width="1.5"/>
      <circle id="s3-leaddot" cx="{HOVER_X}" cy="{DRONE_Y - 34}" r="5" fill="{INK}"/>
    </svg>
    <div id="s3-hud">
      <div id="s3-tag" class="tag">Caméra infrarouge</div>
      <div id="s3-scale" class="scale"><span>Froid</span><i></i><span>Chaud</span></div>
    </div>
    <div id="s3-title" class="title" style="{tstyle(L and L["s3_title"], "left: 140px; top: 120px")}">Le scan infrarouge révèle<br />chaque échauffement.</div>
    {question_html("s3")}"""
    css = """
    #root #s3-hud { position: absolute; left: 480px; top: 306px; display: flex; align-items: center; gap: 36px; }
    #root .tag { font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 30px; line-height: 1; padding: 10px 16px; background: #FFFFFF; border: 1.5px solid #111111; color: #111111; white-space: nowrap; }
    #root .scale { display: flex; align-items: center; gap: 14px; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 30px; color: #6B6B70; }
    #root .scale i { display: block; width: 200px; height: 12px; background: linear-gradient(90deg, #E4E4E7 0%, #FFD2BC 55%, #FF5700 100%); }
    #root #s3-tag, #root #s3-scale, #root #s3-leaddot, #root #s3-scan, #root .s3-ring { opacity: 0; }"""
    if L:
        css += f"""
    #root #s3-hud {{ left: {L["s3_hud"][0]}px; top: {L["s3_hud"][1]}px; flex-direction: column; align-items: flex-start; gap: 12px; }}"""
    js = f"""
      const title = words($("#s3-title"), txt("s3-title", "Le scan infrarouge révèle|chaque *échauffement*."));
      const HOVER = {HOVER_X}, END = {SCAN_END_X}, Y = {DRONE_Y};
      const T0 = 3.2, TD = 1.5; // balayage rapide
      // 1. raccord de la scène 2 : le champ est déjà là, la question reste affichée puis laisse place au titre
      const q = words($("#s3-q"), txt("s3-q", "{QUESTION}"));
      blurOut(2.85, q, 0.18, 0.025);
      // 2. le drone entre ; les rotors tournent en continu
      tl.fromTo($("#s3-drone"), {{ x: -260, y: Y }}, {{ x: HOVER, y: Y, duration: 0.85, ease: "expo.out" }}, 0.7);
      tl.fromTo($$(".s3-blade"), {{ rotation: 0, transformOrigin: "50% 50%" }}, {{ rotation: 360 * 13, duration: 6.6, ease: "none" }}, 0);
      // 3. HUD technique : ligne de rappel + données
      fadeIn(1.6, $("#s3-leaddot"), 0.15);
      draw(1.65, $("#s3-leader"), 0.35, "power2.out");
      blurIn(1.95, [$("#s3-tag"), $("#s3-scale")], 0.18, 0.12);
      blurOut(3.0, [$("#s3-tag"), $("#s3-scale")], 0.16, 0.05);
      undraw(3.0, $("#s3-leader"), 0.2, "power3.in");
      fadeOut(3.05, $("#s3-leaddot"), 0.15);
      tl.set($("#s3-leader"), {{ opacity: 0 }}, 3.25);
      // 4. balayage thermique : la ligne orange révèle la vue thermique
      fadeIn(T0 - 0.12, $("#s3-scan"), 0.12);
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
      blurIn(3.25, title, 0.15, 0.067);
      // 5. sortie : le drone quitte le cadre, puis zoom traversant
      fadeOut(T0 + TD - 0.05, $("#s3-scan"), 0.2);
      tl.to($("#s3-drone"), {{ x: 2250, duration: 0.45, ease: "power3.in" }}, T0 + TD);
      blurOut(5.6, title, 0.16, 0.02);
      tl.to($("#s3-svg"), {{ attr: {{ viewBox: "{vb(S3_END_VB)}" }}, duration: 0.62, ease: "power3.in" }}, 5.98);"""
    if L:
        marker = '      tl.fromTo($("#s3-cliprect"),'
        cam = (f'      tl.fromTo($("#s3-svg"), {{ attr: {{ viewBox: "{vb(S3_VB0)}" }} }}, '
               f'{{ attr: {{ viewBox: "{vb(S3_VB1)}" }}, duration: TD, ease: "power1.inOut" }}, T0);\n')
        js = js.replace(marker, cam + marker, 1)
    write_scene(
        "s3",
        "Scène 3 — Inspection drone",
        [svar("s3-title", "Scène 3 — titre", "Le scan infrarouge révèle|chaque *échauffement*."),
         svar("s3-q", "Scènes 2-3 — question (| = retour ligne, *mot* = orange)", QUESTION)],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# S4 — Détection des anomalies
# --------------------------------------------------------------------------
def lab4(i, left, top, extra=""):
    main, detail = S4_LABELS[i].split("|")
    return (f'<div id="s4-l{i + 1}" class="lab4" style="left: {n(left)}px; top: {n(top)}px{extra}">'
            f'<span class="m">{main}</span><span class="dt">{detail}</span></div>')


def s4_callouts():
    """Déclinaisons : étiquettes sous le panneau, reliées par des traits verticaux."""
    vx, vy, vw, _ = S4_SETTLE_VB
    k = W / vw
    mlh = round(L["s4_fs"][0] * 1.22)
    leaders, dots, labels = [None] * 3, [None] * 3, [None] * 3
    for row, i, (align, xr, wbox) in zip(L["s4_rows"], L["s4_order"], L["s4_lab"]):
        cx, cy = HERO_ANCH[i]
        scx = (cx - vx) * k
        wy1 = (row - mlh / 2 - 8) / k + vy
        leaders[i] = f'<polyline id="s4-ld{i}" class="d" pathLength="1" points="{n(cx)},{n(cy)} {n(cx)},{n(wy1)}" fill="none" stroke="{INK}" stroke-width="1.5"/>'
        dots[i] = f'<circle id="s4-dot{i}" cx="{n(cx)}" cy="{n(wy1)}" r="{n(5 / k)}" fill="{INK}"/>'
        left, ta = {"c": (scx - wbox / 2, "center"), "r": (xr - wbox, "right"), "l": (xr, "left")}[align]
        labels[i] = lab4(i, left, row - mlh / 2, f"; width: {wbox}px; text-align: {ta}")
    return leaders, dots, labels


def build_s4():
    import math

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
                + cell_tint(r, c, x, y, K)
                + anomalies_svg(r, c, x, y, K, "s4")
                + f'<path d="{cell_lines(x, y, S4PW, S4PH)}" stroke="{TH_CELL}" stroke-width="1" fill="none"/>'
                + f'<rect x="{n(x)}" y="{n(y)}" width="{n(S4PW)}" height="{n(S4PH)}" fill="none" stroke="{INK}" stroke-width="2"/>'
            )
    # 16:9 : lignes de rappel horizontales, du défaut jusqu'à l'étiquette à droite
    leaders, dots, labels = [], [], []
    for i, (ax, ay) in enumerate(HERO_ANCH):
        leaders.append(f'<polyline id="s4-ld{i}" class="d" pathLength="1" points="{n(ax)},{n(ay)} 1160,{n(ay)}" fill="none" stroke="{INK}" stroke-width="1.5"/>')
        dots.append(f'<circle id="s4-dot{i}" cx="1160" cy="{n(ay)}" r="5" fill="{INK}"/>')
        labels.append(lab4(i, 1182, ay - 22))
    if L:
        leaders, dots, labels = s4_callouts()
    kz = W / S4_SETTLE_VB[2]  # échelle écran du monde S4, panneau posé
    pins = [f'<circle id="s4-pin{i}" cx="{n(ax)}" cy="{n(ay)}" r="{n(8 / kz)}" fill="{INK}" stroke="#FFFFFF" stroke-width="3"/>'
            for i, (ax, ay) in enumerate(HERO_ANCH)]
    s4t = L["s4_title_text"] if L else "Chaque anomalie est détectée et localisée."
    fm, fd = L["s4_fs"] if L else (36, 28)
    body = f"""    <svg id="s4-svg" class="world zoom" data-dash="{dash_k(S4_SETTLE_VB)}" viewBox="{vb(S4_START_VB)}" width="{W}" height="{H}"{CANVAS}>
      <defs>{thermal_defs("s4")}</defs>
      <g id="s4-neigh">{"".join(neigh)}</g>
      {hero_panel_svg("s4")}
      <g id="s4-leaders">{"".join(leaders)}{"".join(dots)}{"".join(pins)}</g>
    </svg>
    {"".join(labels)}
    <div id="s4-title" class="title" style="{tstyle(L and L["s4_title"], "left: 120px; top: 86px; font-size: 56px")}">Chaque anomalie est détectée et localisée.</div>"""
    css = f"""
    #root .lab4 {{ position: absolute; font-family: "Comfortaa", sans-serif; white-space: nowrap; }}
    #root .lab4 .m {{ display: block; font-weight: 700; font-size: {fm}px; line-height: {round(fm * 1.22)}px; color: #111111; }}
    #root .lab4 .dt {{ display: block; font-weight: 600; font-size: {fd}px; line-height: {round(fd * 1.3)}px; color: #6B6B70; }}
    #root #s4-bus, #root #s4-inner {{ opacity: 0; }}
    #root #s4-leaders circle {{ opacity: 0; }}"""
    js = f"""
      const title = words($("#s4-title"), txt("s4-title", "{s4t}"));
      [1, 2, 3].forEach((i) => {{
        const v = txt("s4-l" + i, "");
        if (v && v.indexOf("|") > 0) {{
          const el = $("#s4-l" + i);
          el.querySelector(".m").textContent = v.split("|")[0];
          el.querySelector(".dt").textContent = v.split("|")[1];
        }}
      }});
      const svg = $("#s4-svg");
      // 1. le zoom se pose sur le panneau défectueux
      tl.fromTo(svg, {{ attr: {{ viewBox: "{vb(S4_START_VB)}" }} }}, {{ attr: {{ viewBox: "{vb(S4_SETTLE_VB)}" }}, duration: 0.95, ease: "power3.out" }}, 0);
      fadeOut(0.2, $("#s4-neigh"), 0.6, 0, "power1.inOut");
      fadeIn(0.55, [$("#s4-inner"), $("#s4-bus")], 0.6);
      // 2. titre : du gris à l'encre, mot à mot
      tl.fromTo(title, {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2 }}, 0.75);
      tl.fromTo(title, {{ color: "#D4D4D8" }}, {{ color: "#111111", duration: 0.25, stagger: 0.08 }}, 0.95);
      // 3. chaque défaut est désigné : point sur l'anomalie, ligne de rappel, étiquette (calé sur la voix off)
      [[0.8, 0], [1.55, 1], [3.3, 2]].forEach(([t, i]) => {{
        tl.fromTo($("#s4-pin" + i), {{ opacity: 0, scale: 0, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)" }}, t + 0.1);
        draw(t + 0.25, $("#s4-ld" + i), 0.35, "power2.out");
        fadeIn(t + 0.58, $("#s4-dot" + i), 0.1);
        blurIn(t + 0.62, $("#s4-l" + (i + 1)), 0.18);
      }});
      // 5. sortie : la vignette part dans le rapport
      blurOut(6.15, [...title, $("#s4-l1"), $("#s4-l2"), $("#s4-l3")], 0.18, 0.02);
      undraw(6.15, $$("#s4-leaders polyline"), 0.2, "power3.in");
      fadeOut(6.15, $$("#s4-leaders circle"), 0.15);
      fadeOut(6.4, [$("#s4-bus"), $("#s4-inner")], 0.4);
      tl.to(svg, {{ attr: {{ viewBox: "{vb(S4_END_VB)}" }}, duration: 0.72, ease: "power2.inOut" }}, 6.43);"""
    write_scene(
        "s4",
        "Scène 4 — Détection des anomalies (vocabulaire de la note technique)",
        [
            svar("s4-title", "Scène 4 — titre", s4t),
            svar("s4-l1", "Scène 4 — étiquette 1 (principal|précision)", S4_LABELS[0]),
            svar("s4-l2", "Scène 4 — étiquette 2 (principal|précision)", S4_LABELS[1]),
            svar("s4-l3", "Scène 4 — étiquette 3 (principal|précision)", S4_LABELS[2]),
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


# lien « Accéder à votre installation » sur la couverture du rapport (coordonnées de la page, scène de référence)
S5_LINK, S5_LINK_FS, S5_LINK_2L = {  # x, y, largeur, hauteur ; corps (≥ 28 px à l'écran) ; texte sur deux lignes
    "16x9": ((260, 676, 520, 58), 28, False),
    "9x16": ((260, 664, 520, 104), 36, True),
    "1x1": ((260, 660, 520, 112), 40, True),
}[FMT]
S5_CHECKS = [round(13.3 + i * 0.36, 2) for i in range(4)]  # cases de la checklist (page 3), une toutes les 0,36 s
S5_LOGO_Y = S5_LINK[1] + S5_LINK[3] + (38 if S5_LINK_2L else 38)  # petit logo de la couverture, sous le lien
CUR_K = {"16x9": 1.3, "9x16": 1.5, "1x1": 1.25}[FMT]  # taille du curseur


def doc_to_screen(x, y):
    """Coordonnées de la page du rapport -> écran (boîte s5_doc des déclinaisons)."""
    ds, ddx, ddy = L["s5_doc"] if L else (1, 0, 0)
    return ds * x + ddx, ds * y + ddy


def cursor_html(cid):
    """Pointeur de souris (pointe en 0, 0), blanc cerné d'encre."""
    k = CUR_K
    return (f'<div id="{cid}" class="cur"><svg style="position: absolute; left: {n(-2 * k)}px; top: {n(-2 * k)}px" '
            f'width="{n(30 * k)}" height="{n(44 * k)}" viewBox="-2 -2 30 44">'
            f'<path d="M0 0L0 34L8.5 26L14 39L19.5 36.6L14 24L25 24Z" fill="#FFFFFF" stroke="{INK}" stroke-width="2.2" stroke-linejoin="round"/></svg></div>')


CUR_CSS = """
    #root .cur { position: absolute; left: 0; top: 0; width: 0; height: 0; transform-origin: 0 0; }
    #root .win { position: absolute; box-sizing: border-box; background: #FFFFFF; border: 2.5px solid #111111; border-radius: 18px; }"""


S5_CATS = [  # gravité (inspirée de la catégorisation IEC du rapport type), couleurs Fly Scan'Air
    (5, "Critique", "#FF5700", 1),
    (4, "Important", "#FF8A4C", 2),
    (3, "Impact physique", "#FFBE9A", 1),
    (2, "Usure anormale", "#A1A1AA", 2),
    (1, "Esthétique", "#D4D4D8", 1),
]


def mini_logo(x, y, sc, prefix):
    """Logo Fly Scan'Air statique, petit format (couverture du rapport)."""
    return (
        f'<defs><linearGradient id="{prefix}-word" gradientUnits="userSpaceOnUse" x1="140" y1="0" x2="1198" y2="0">'
        '<stop offset="0" stop-color="#E2392D"/><stop offset="0.47" stop-color="#E9862A"/>'
        '<stop offset="0.6" stop-color="#E8842A"/><stop offset="1" stop-color="#DC382D"/></linearGradient></defs>'
        f'<g transform="translate({n(x)} {n(y)}) scale({sc})">'
        f'<path d="{logo_coil_path()}" fill="none" stroke="#6D6C74" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<path d="{LOGO_LETTERS}" fill="url(#{prefix}-word)"/>'
        f'<circle cx="{BALL_L[0]}" cy="{BALL_L[1]}" r="{BALL_RAD}" fill="#D8352A"/><circle cx="{BALL_R[0]}" cy="{BALL_R[1]}" r="{BALL_RAD}" fill="#D8352A"/>'
        "</g>"
    )


S5_CARD = {  # fiche défaut, en coordonnées écran : x, y, largeur, corps du texte, champs empilés (format étroit)
    "16x9": (980, 352, 820, 30, False),
    "9x16": (108, 1212, 864, 32, False),
    "1x1": (510, 292, 545, 28, True),
}[FMT]
S5_DEFAUTS = [  # valeurs illustratives (aucune donnée du rapport type)
    dict(num="Défaut #1", cat=4, cat_fill="#FF8A4C", cat_ink="#111111", statut="À traiter", type="Point chaud",
         dt="11,2 °C", mx="58 °C", origine="Cellule fissurée", action="Contrôle électrique", note="Échauffement localisé"),
    dict(num="Défaut #2", cat=5, cat_fill=ACC, cat_ink="#FFFFFF", statut="À traiter", type="Diode by-pass",
         dt="7,8 °C", mx="54 °C", origine="Diode défectueuse", action="Remplacer la diode", note="Échauffement linéaire"),
]


def s5_plan(pfs):
    """Plan de localisation (page « Analyse détaillée », sous la vignette) : 7 x 3 modules, module concerné en orange."""
    lab_y = 612
    tick_y = lab_y + pfs * 1.25 + pfs * 0.95
    px0 = 260 + pfs * 1.1
    gx_, gy_ = 8, 8
    mw = (780 - px0 - 6 * gx_) / 7
    mh = mw * 0.62
    py0 = tick_y + pfs * 0.4
    mods, ticks = [], []
    for r_ in range(ROWS):
        for c_ in range(COLS):
            if (r_, c_) == HERO:
                continue
            fill = "#FFD2BC" if (r_, c_) in ANOM else PANEL
            mods.append(f'<rect class="s5-pm" x="{n(px0 + c_ * (mw + gx_))}" y="{n(py0 + r_ * (mh + gy_))}" width="{n(mw)}" height="{n(mh)}" rx="4" fill="{fill}" stroke="{INK}" stroke-width="1.5"/>')
    hx_, hy_ = px0 + HERO[1] * (mw + gx_), py0 + HERO[0] * (mh + gy_)
    hero = f'<g id="s5-ph"><rect x="{n(hx_)}" y="{n(hy_)}" width="{n(mw)}" height="{n(mh)}" rx="4" fill="{ACC}" stroke="{INK}" stroke-width="1.5"/></g>'
    for r_ in range(ROWS):
        ticks.append(f'<text class="pg" x="262" y="{n(py0 + r_ * (mh + gy_) + mh / 2 + pfs * 0.36)}" font-size="{pfs}" fill="#6B6B70">{"ABC"[r_]}</text>')
    for c_ in range(COLS):
        ticks.append(f'<text class="pg" x="{n(px0 + c_ * (mw + gx_) + mw / 2)}" y="{n(tick_y)}" text-anchor="middle" font-size="{pfs}" fill="#6B6B70">{c_ + 1}</text>')
    cap_y = py0 + 3 * mh + 2 * gy_ + pfs * 0.35
    return (f'<div id="s5-plan-lab" class="pgt grey" style="left: 260px; top: {n(lab_y)}px">Localisation</div>\n'
            f'      <svg id="s5-plan" class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}"><g id="s5-pticks">{"".join(ticks)}</g>{"".join(mods)}{hero}</svg>\n'
            f'      <div id="s5-plan-cap" class="pgt" style="left: {n(px0)}px; top: {n(cap_y)}px">Rangée B · module 5</div>')


def s5_card(k, d):
    """Fiche d'un défaut, mise en page des rapports Fly Scan'Air : titre en couleur, filet vertical à gauche,
    libellés en gras (Catégorie, Statut, Type, ΔT, MaxT), séparateur, puis Origine / Action / Note en italique."""
    x0, y0, w, f, stacked = S5_CARD
    rh = f * 1.9  # hauteur d'une ligne
    lx = x0 + 30  # libellés
    vx = lx + f * 6.4  # valeurs (après « Catégorie : »)
    x2 = x0 + w * 0.53  # deuxième colonne (Statut, MaxT)
    vx2 = x2 + f * 4.6
    yb = y0 + f * 1.45 * 1.2 + f * 0.55
    rows = []  # (y, [(x, kind, texte)])
    y = yb
    badge = ("badge", str(d["cat"]))
    pill = ("pill", d["statut"])
    if stacked:
        lines = [[("Catégorie :", badge)], [("Statut :", pill)], [("Type :", ("v", d["type"]))],
                 [("ΔT :", ("v", d["dt"]))], [("MaxT :", ("v", d["mx"]))], "rule",
                 [("Origine :", ("it", d["origine"]))], [("Action :", ("it", d["action"]))], [("Note :", ("it", d["note"]))]]
    else:
        lines = [[("Catégorie :", badge), ("Statut :", pill)], [("Type :", ("v", d["type"]))],
                 [("ΔT :", ("v", d["dt"])), ("MaxT :", ("v", d["mx"]))], "rule",
                 [("Origine :", ("it", d["origine"]))], [("Action :", ("it", d["action"]))], [("Note :", ("it", d["note"]))]]
    html, shapes = [], []
    cls = f"s5-c{k}"
    html.append(f'<div class="rct {cls}" style="left: {n(x0)}px; top: {n(y0)}px; font-size: {n(f * 1.45)}px">{d["num"]}</div>')
    for line in lines:
        if line == "rule":
            shapes.append(f'<line x1="{n(lx)}" y1="{n(y + rh * 0.3)}" x2="{n(x0 + w)}" y2="{n(y + rh * 0.3)}" stroke="#D4D4D8" stroke-width="2"/>')
            y += rh * 0.6
            continue
        ty = y + (rh - f * 1.25) / 2
        for col, (lab, (kind, val)) in enumerate(line):
            lxx, vxx = (lx, vx) if col == 0 else (x2, vx2)
            html.append(f'<div class="rcl {cls}" style="left: {n(lxx)}px; top: {n(ty)}px; font-size: {f}px">{lab}</div>')
            if kind == "badge":
                b = f * 1.5
                shapes.append(f'<g id="s5-badge{k}"><rect x="{n(vxx)}" y="{n(y + (rh - b) / 2)}" width="{n(b)}" height="{n(b)}" rx="7" fill="{d["cat_fill"]}"/>'
                              f'<text class="pg b" x="{n(vxx + b / 2)}" y="{n(y + rh / 2 + f * 0.36)}" text-anchor="middle" font-size="{f}" fill="{d["cat_ink"]}">{val}</text></g>')
            elif kind == "pill":
                ph, pw = f * 1.45, len(val) * f * 0.6 + f * 1.1
                shapes.append(f'<rect x="{n(vxx)}" y="{n(y + (rh - ph) / 2)}" width="{n(pw)}" height="{n(ph)}" rx="{n(ph / 2)}" fill="#FFD2BC"/>'
                              f'<text class="pg" x="{n(vxx + pw / 2)}" y="{n(y + rh / 2 + f * 0.36)}" text-anchor="middle" font-size="{f}" fill="#111111" font-weight="600">{val}</text>')
            else:
                it = " it" if kind == "it" else ""
                html.append(f'<div class="rcv{it} {cls}" style="left: {n(vxx)}px; top: {n(ty)}px; font-size: {f}px">{val}</div>')
        if len(line) == 2 and line[1][1][0] == "v":  # séparateur vertical entre ΔT et MaxT
            shapes.append(f'<line x1="{n(x2 - f * 0.9)}" y1="{n(y + rh * 0.22)}" x2="{n(x2 - f * 0.9)}" y2="{n(y + rh * 0.78)}" stroke="#A1A1AA" stroke-width="2"/>')
        y += rh
    shapes.insert(0, f'<line x1="{n(x0 + 4)}" y1="{n(yb)}" x2="{n(x0 + 4)}" y2="{n(y)}" stroke="#D4D4D8" stroke-width="3"/>')
    svg = f'<svg class="world {cls}" viewBox="0 0 {W} {H}" width="{W}" height="{H}"{CANVAS}>{"".join(shapes)}</svg>'
    return "\n    ".join([html[0], svg] + html[1:])


def build_s5():
    dx, dy, dw, dh = 220, 96, 600, 848
    doc_path = f"M{dx} {dy} H{dx + dw} V{dy + dh} H{dx} Z"
    pfs = L["s5_pfs"] if L else 30  # corps de texte des pages
    foot = (f'<line class="s5-foot" x1="260" y1="890" x2="660" y2="890" stroke="#E4E4E7" stroke-width="8" stroke-linecap="round"/>'
            f'<line class="s5-foot" x1="260" y1="914" x2="560" y2="914" stroke="#E4E4E7" stroke-width="8" stroke-linecap="round"/>')
    rule = '<line class="d s5-rule" pathLength="1" x1="260" y1="178" x2="780" y2="178" stroke="#111111" stroke-width="1.5"/>'
    # ---- page 1 : analyse détaillée (la vignette du panneau arrive de la scène 4)
    p1 = f"""      <div id="s5-p1" class="s5-page">
      <svg class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">{rule}</svg>
      <svg id="s5-thumb" class="world zoom" viewBox="{vb(THUMB_LOCAL_VB)}" width="{SW}" height="{SH}">
        <defs>{thermal_defs("s5")}</defs>
        {hero_panel_svg("s5", with_ids=False)}
        <rect id="s5-bbox" x="{n(BOX1[0])}" y="{n(BOX1[1])}" width="{n(BOX1[2])}" height="{n(BOX1[3])}" rx="6" fill="none" stroke="{ACC}" stroke-width="3"/>
      </svg>
      <div class="dochead" style="left: 260px; top: 128px">Analyse détaillée</div>
      {s5_plan(pfs)}
      </div>"""
    # ---- page 2 : résultats + gravité
    cards, swatches, bars = [], [], []
    for i in range(3):  # trois lignes de statistiques, séparées par un filet
        cards.append(f'<line class="d s5-card" pathLength="1" x1="260" y1="{254 + i * 54}" x2="780" y2="{254 + i * 54}" stroke="#E4E4E7" stroke-width="2"/>')
    rows_html = []
    for i, (k, lab, col, cnt) in enumerate(S5_CATS):
        y = 452 + i * 72
        ink = "#FFFFFF" if k >= 5 else "#111111"  # blanc seulement sur l'orange vif (contraste)
        swatches.append(f'<g class="s5-sw"><rect x="260" y="{y - 22}" width="44" height="44" rx="8" fill="{col}"/>'
                        f'<text class="pg b" x="282" y="{y + pfs * 0.36:.1f}" text-anchor="middle" font-size="{pfs}" fill="{ink}">{k}</text></g>')
        bars.append(f'<rect class="s5-gbar" x="680" y="{y - 9}" width="{cnt * 46}" height="18" rx="9" fill="{col}" data-w="{cnt * 46}"/>')
        rows_html.append(f'<div class="pgt s5-cl" style="left: 322px; top: {y - pfs * 0.62:.0f}px">{lab}</div>')
    p2 = f"""      <div id="s5-p2" class="s5-page">
      <svg class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">{rule}{foot}{"".join(cards)}{"".join(swatches)}{"".join(bars)}</svg>
      <div class="dochead" style="left: 260px; top: 128px">Résultats</div>
      <div id="s5-n0" class="num" style="left: 260px; top: 202px">0</div>
      <div id="s5-n1" class="num" style="left: 260px; top: 256px">0</div>
      <div id="s5-n2" class="num" style="left: 260px; top: 310px">0 / 7</div>
      <div class="pgt s5-cardl" style="left: 410px; top: {230 - pfs * 0.62:.0f}px">défauts détectés</div>
      <div class="pgt s5-cardl" style="left: 410px; top: {284 - pfs * 0.62:.0f}px">modules impactés</div>
      <div class="pgt s5-cardl" style="left: 410px; top: {338 - pfs * 0.62:.0f}px">défauts résolus</div>
      <div id="s5-sub" class="pgt b" style="left: 260px; top: {400 - pfs:.0f}px">Gravité des défauts</div>
      {"".join(rows_html)}
      </div>"""
    # ---- page 3 : couverture + tampon de conformité
    sf = L["s5_stamp"] if L else 30
    sw_, sh_ = sf * 10.4, sf * 3.6
    stamp = (
        f'<g transform="translate(520 548) rotate(-7)"><g id="s5-stamp">'
        f'<rect x="{n(-sw_ / 2)}" y="{n(-sh_ / 2)}" width="{n(sw_)}" height="{n(sh_)}" rx="10" fill="#FFFFFF" stroke="{ACC}" stroke-width="3"/>'
        f'<rect x="{n(-sw_ / 2 + 7)}" y="{n(-sh_ / 2 + 7)}" width="{n(sw_ - 14)}" height="{n(sh_ - 14)}" rx="6" fill="none" stroke="{ACC}" stroke-width="1.5"/>'
        f'<text class="stamp" x="0" y="{n(-sf * 0.25)}" text-anchor="middle" font-size="{sf}" letter-spacing="3">CONFORME</text>'
        f'<text class="stamp" x="0" y="{n(sf * 1.05)}" text-anchor="middle" font-size="{sf}">IEC TS 62446-3</text>'
        f'</g></g>'
    )
    illus = []
    for r in range(2):
        for c in range(4):
            x, y = 300 + c * 113, 440 + r * 112
            illus.append(f'<rect class="d s5-ill" pathLength="1" x="{x}" y="{y}" width="100" height="98" fill="#F3F3F4" stroke="#111111" stroke-width="1.5"/>')
    p3 = f"""      <div id="s5-p3" class="s5-page">
      <svg class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">
        <line id="s5-acc" class="d" pathLength="1" x1="260" y1="150" x2="420" y2="150" stroke="{ACC}" stroke-width="5" stroke-linecap="round"/>
        {"".join(illus)}
        <rect id="s5-hotc" x="526" y="552" width="100" height="98" fill="url(#s5-hot)"/>
        <g id="s5-mlogo">{mini_logo(520 - 1270 * 0.26 / 2, S5_LOGO_Y, 0.26, "s5m")}</g>
      </svg>
      <svg class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">{stamp}</svg>
      <div id="s5-ct" class="covt" style="left: 260px; top: 200px">Rapport d’inspection<br />thermique</div>
      <div id="s5-cs" class="pgt grey" style="left: 260px; top: 340px">Centrale photovoltaïque</div>
      <div id="s5-link" class="lnk" style="left: {S5_LINK[0]}px; top: {S5_LINK[1]}px; width: {S5_LINK[2]}px; height: {S5_LINK[3]}px; font-size: {S5_LINK_FS}px"><svg viewBox="0 0 256 256" width="{n(S5_LINK_FS * 1.05)}" height="{n(S5_LINK_FS * 1.05)}"><path d="{ICONS["arrow-square-out"]}" fill="{ACC}"/></svg><span id="s5-linkt">Accéder à votre{"<br />" if S5_LINK_2L else " "}installation</span></div>
      </div>"""
    doc_part = f"""    <div id="s5-docw" style="position: absolute; left: 0; top: 0; width: {SW}px; height: {SH}px">
    <div class="s5-sheet" style="left: {dx + 22}px; top: {dy + 22}px; width: {dw}px; height: {dh}px"></div>
    <div class="s5-sheet" style="left: {dx + 11}px; top: {dy + 11}px; width: {dw}px; height: {dh}px"></div>
    <div id="s5-paper" style="left: {dx}px; top: {dy}px; width: {dw}px; height: {dh}px"></div>
    <svg class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">
      <path id="s5-doc" class="d" pathLength="1" d="{doc_path}" fill="none" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>
    </svg>
{p1}
{p2}
{p3}
    </div>"""
    # ---- colonne de droite : graphique de production (page 2), checklist (page 3)
    grid, yticks, gbars, cats = [], [], [], []
    for v in range(0, 25001, 5000):
        y = S5_AY - v * S5_K
        if v:
            grid.append(f'<line x1="{S5_AX}" y1="{n(y)}" x2="1770" y2="{n(y)}"/>')
        label = f"{v:,}".replace(",", " ")
        yticks.append(f'<text x="{S5_AX - 20}" y="{n(y + 10)}" text-anchor="end">{label}</text>')
    for i, (name, v, cx, col) in enumerate(S5_BARS):
        h = v * S5_K
        gbars.append(
            f'<rect id="s5-bar{i}" x="{cx - S5_BW / 2}" y="{n(S5_AY - h)}" width="{S5_BW}" height="{n(h + 12)}" rx="10" '
            f'fill="{col}" data-top="{n(S5_AY - h)}" data-h="{n(h + 12)}"/>'
        )
        cats.append(f'<div id="s5-cat{i}" class="cat" style="left: {cx - 170}px; top: {S5_AY + 18}px">{name.replace("|", "<br />")}</div>')
    items = ["Anomalies localisées", "Priorités d’intervention", "Recommandations", "Justificatif assurance"]
    crow = [440, 520, 600, 680]
    cboxes = "".join(f'<rect class="d s5-box" pathLength="1" x="1010" y="{y - 17}" width="34" height="34" rx="4" fill="none" stroke="{INK}" stroke-width="2"/>' for y in crow)
    cchecks = "".join(f'<polyline id="s5-k{i}" class="d" pathLength="1" points="1016,{y + 1} 1025,{y + 10} 1040,{y - 9}" fill="none" stroke="{ACC}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>' for i, y in enumerate(crow))
    ctexts = "".join(f'<div id="s5-i{i}" class="item" style="left: 1068px; top: {y - 21}px">{t}</div>' for i, (y, t) in enumerate(zip(crow, items)))
    chart_part = f"""    <svg id="s5-chart" class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">
      <defs><clipPath id="s5-clip"><rect x="-4000" y="-4000" width="{SW + 8000}" height="{S5_AY + 4000}"/></clipPath></defs>
      <g id="s5-axes">
        <g id="s5-grid" stroke="#E4E4E7" stroke-width="1.5" stroke-dasharray="6 8">{"".join(grid)}</g>
        <g id="s5-yt" class="tick">{"".join(yticks)}</g>
      </g>
      <g clip-path="url(#s5-clip)">{"".join(gbars)}</g>
      <g id="s5-axlines">
        <g fill="none" stroke="{INK}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line id="s5-ax" class="d" pathLength="1" x1="{S5_AX}" y1="{S5_AY}" x2="1790" y2="{S5_AY}"/>
          <polyline id="s5-axa" class="d" pathLength="1" points="1778,{S5_AY - 9} 1790,{S5_AY} 1778,{S5_AY + 9}"/>
          <line id="s5-ay" class="d" pathLength="1" x1="{S5_AX}" y1="{S5_AY}" x2="{S5_AX}" y2="375"/>
          <polyline id="s5-aya" class="d" pathLength="1" points="{S5_AX - 9},387 {S5_AX},375 {S5_AX + 9},387"/>
        </g>
      </g>
    </svg>
    <div id="s5-lab-y" class="label" style="left: 1010px; top: 318px">Production (kWh/an)</div>
    {"".join(cats)}
    <svg id="s5-check" class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">{cboxes}{cchecks}</svg>
    {ctexts}"""
    tst = tstyle(L and L["s5_title"], "left: 960px; top: 150px")
    titles = "\n".join(f'    <div id="s5-t{i}" class="title" style="{tst}">{t}</div>' for i, t in (
        (1, "Chaque défaut est<br />localisé et qualifié."),
        (2, "Classés par gravité,<br />avec l’action à mener."),
        (3, "Un rapport aux normes,<br />pour agir rapidement."),
    ))
    cards_html = "\n    ".join(s5_card(k + 1, d) for k, d in enumerate(S5_DEFAUTS))
    lx0, ly0 = doc_to_screen(S5_LINK[0], S5_LINK[1])
    lx1, ly1 = doc_to_screen(S5_LINK[0] + S5_LINK[2], S5_LINK[1] + S5_LINK[3])
    wx, wy, ww, wh = P6["win"]
    body = (box(doc_part, L["s5_doc"] if L else None) + "\n" + box(chart_part, L["s5_chart"] if L else None) + "\n" + titles
            + "\n    " + cards_html
            + f'''
    <svg class="world" viewBox="0 0 {W} {H}" width="{W}" height="{H}"{CANVAS}>
      <rect id="s5-open" x="{n(lx0)}" y="{n(ly0)}" width="{n(lx1 - lx0)}" height="{n(ly1 - ly0)}" rx="{n((ly1 - ly0) / 2)}" fill="#FFF1E8" stroke="{ACC}" stroke-width="2"/>
    </svg>
    {cursor_html("s5-cur")}''')
    css = f"""
    #root #s5-paper, #root .s5-sheet {{ position: absolute; background: #FFFFFF; opacity: 0; }}
    #root #s5-paper {{ box-shadow: 0 18px 40px rgba(17, 17, 17, 0.08); }}
    #root .s5-sheet {{ border: 1.5px solid #D4D4D8; }}
    #root .s5-page {{ position: absolute; left: 0; top: 0; width: {SW}px; height: {SH}px; }}
    #root #s5-p2, #root #s5-p3 {{ opacity: 0; }}
    #root .dochead {{ position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 700; font-size: {pfs}px; line-height: 40px; color: #111111; white-space: nowrap; }}
    #root .pgt {{ position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: {pfs}px; line-height: 1.25; color: #111111; white-space: nowrap; }}
    #root .pgt.b, #root .pg.b {{ font-weight: 700; }}
    #root .pgt.grey {{ color: #6B6B70; }}
    #root .pg {{ font-family: "Comfortaa", sans-serif; }}
    #root .num {{ position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 700; font-size: 44px; line-height: 54px; color: #111111; white-space: nowrap; }}
    #root #s5-n0 {{ color: #FF5700; }}
    #root .covt {{ position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 700; font-size: 44px; line-height: 54px; color: #111111; white-space: nowrap; }}
    #root .item {{ position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 30px; line-height: 42px; color: #111111; white-space: nowrap; }}
    #root .tick text {{ font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 28px; fill: #6B6B70; }}
    #root .stamp {{ font-family: "Comfortaa", sans-serif; font-weight: 700; fill: #FF5700; }}
    #root .rct {{ position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 700; line-height: 1.2; color: #FF5700; white-space: nowrap; }}
    #root .rcl {{ position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 700; line-height: 1.25; color: #111111; white-space: nowrap; }}
    #root .rcv {{ position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 600; line-height: 1.25; color: #111111; white-space: nowrap; }}
    #root .rcv.it {{ font-style: italic; color: #3F3F46; }}
    #root .cat {{ position: absolute; width: 340px; text-align: center; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 28px; line-height: 36px; color: #111111; }}
    #root .lnk {{ position: absolute; box-sizing: border-box; display: flex; align-items: center; justify-content: center; gap: 14px; border-radius: 30px; background: #FFF1E8; border: 2px solid #FF5700; font-family: "Comfortaa", sans-serif; font-weight: 700; color: #111111; white-space: nowrap; }}
    #root .lnk span {{ text-align: center; line-height: 1.25; text-decoration: underline; text-decoration-color: #FF5700; text-decoration-thickness: 2px; text-underline-offset: 6px; }}
    #root #s5-open, #root #s5-link {{ opacity: 0; }}{CUR_CSS}
    #root #s5-grid, #root #s5-yt, #root #s5-stamp, #root .s5-foot, #root #s5-hotc, #root #s5-mlogo, #root .s5-sw, #root #s5-badge1, #root #s5-badge2, #root #s5-bbox, #root #s5-plan-lab, #root #s5-plan-cap, #root #s5-pticks, #root .s5-pm, #root #s5-ph {{ opacity: 0; }}"""
    if L:
        fs = L["s5_fs"]
        css += f"""
    #root .item {{ font-size: {fs["item"]}px; }}
    #root .tick text {{ font-size: {fs["tick"]}px; }}
    #root .label {{ font-size: {fs["label"]}px; }}
    #root .cat {{ font-size: {fs["cat"]}px; line-height: {fs["catlh"]}px; }}"""
    js = """
      const t1 = words($("#s5-t1"), txt("s5-t1", "Chaque défaut est|localisé et *qualifié*."));
      const t2 = words($("#s5-t2"), txt("s5-t2", "Classés par *gravité*,|avec l’action à mener."));
      const t3 = words($("#s5-t3"), txt("s5-t3", "Un rapport *aux normes*,|pour agir rapidement."));
      ["s5-i0", "s5-i1", "s5-i2", "s5-i3"].forEach((id) => { const v = txt(id, ""); if (v) $("#" + id).textContent = v; });
      const P1 = $("#s5-p1"), P2 = $("#s5-p2"), P3 = $("#s5-p3");
      const pageOut = (t, el) => tl.to(el, { opacity: 0, x: -30, filter: "blur(6px)", duration: 0.22, ease: "power2.in" }, t);
      const pageIn = (t, el) => tl.fromTo(el, { opacity: 0, x: 30, filter: "blur(6px)" }, { opacity: 1, x: 0, filter: "blur(0px)", duration: 0.32, ease: "power3.out" }, t);
      // 1. la feuille se dessine autour de la vignette ; les autres pages du rapport se devinent derrière
      draw(0, $("#s5-doc"), 1.1, "power2.inOut");
      fadeIn(0.2, $("#s5-paper"), 0.7);
      fadeIn(0.6, $$(".s5-sheet"), 0.5, 0.12);
      // PAGE 1 — analyse détaillée du défaut
      blurIn(0.55, P1.querySelector(".dochead"), 0.2);
      draw(0.65, P1.querySelector(".s5-rule"), 0.45, "power2.out");
      blurIn(0.9, t1, 0.15, 0.067);
      //   défaut n°1 : le cadre de détection se pose sur la cellule fissurée, la fiche se remplit
      const bbox = $("#s5-bbox");
      tl.fromTo(bbox, { opacity: 0, scale: 1.35, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.6)" }, 1.45);
      blurIn(1.7, $$(".s5-c1"), 0.18, 0.06);
      tl.fromTo($("#s5-badge1"), { opacity: 0, scale: 0.6, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(1.8)" }, 2.0);
      //   plan de localisation : le champ se dessine, le module concerné s'allume
      blurIn(2.6, $("#s5-plan-lab"), 0.18);
      fadeIn(2.7, $("#s5-pticks"), 0.3);
      fadeIn(2.75, $$(".s5-pm"), 0.25, 0.02);
      tl.fromTo($("#s5-ph"), { opacity: 0, scale: 0.5, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)" }, 3.45);
      blurIn(3.7, $("#s5-plan-cap"), 0.18);
      //   défaut n°2 (voix : « chaque défaut y est décrit… ») : le cadre glisse sur la sous-chaîne
      blurOut(5.15, $$(".s5-c1"), 0.16, 0.006);
      fadeOut(5.15, $("#s5-badge1"), 0.15);
      tl.to(bbox, { attr: { x: __B2X__, y: __B2Y__, width: __B2W__, height: __B2H__ }, duration: 0.55, ease: "power2.inOut" }, 5.2);
      blurIn(5.5, $$(".s5-c2"), 0.18, 0.05);
      tl.fromTo($("#s5-ph"), { scale: 1 }, { scale: 1.12, duration: 0.22, ease: "power2.out", yoyo: true, repeat: 1, immediateRender: false }, 5.3);
      tl.fromTo($("#s5-badge2"), { opacity: 0, scale: 0.6, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(1.8)" }, 6.85); // « …et qualifié »
      // PAGE 2 — résultats et gravité
      blurOut(8.05, t1, 0.16, 0.02);
      blurOut(8.0, [$("#s5-plan-lab"), $("#s5-plan"), $("#s5-plan-cap")], 0.2, 0.02);
      blurOut(7.95, $$(".s5-c2"), 0.16, 0.006);
      pageOut(8.05, P1);
      pageIn(8.25, P2);
      draw(8.3, P2.querySelector(".s5-rule"), 0.4, "power2.out");
      blurIn(8.35, t2, 0.15, 0.067);
      draw(8.45, $$(".s5-card"), 0.4, "power2.out", 0.1);
      [["#s5-n0", 7], ["#s5-n1", 5]].forEach(([id, v], i) => {
        const el = $(id), o = { v: 0 };
        tl.fromTo(o, { v: 0 }, { v, duration: 0.6, ease: "power2.out", onUpdate: () => { el.textContent = Math.round(o.v); } }, 8.6 + i * 0.12);
      });
      blurIn(8.55, [$("#s5-n0"), $("#s5-n1"), $("#s5-n2"), ...$$(".s5-cardl")], 0.2, 0.06);
      blurIn(9.05, $("#s5-sub"), 0.18);
      fadeIn(9.15, $$(".s5-sw"), 0.25, 0.1);
      blurIn(9.2, $$(".s5-cl"), 0.18, 0.1);
      $$(".s5-gbar").forEach((b, i) => {
        tl.fromTo(b, { attr: { width: 0 } }, { attr: { width: parseFloat(b.getAttribute("data-w")) }, duration: 0.5, ease: "power3.out" }, 9.35 + i * 0.1);
      });
      fadeIn(9.65, $$("#s5-p2 .s5-foot"), 0.3, 0.1);
      //   graphique de production (fourni par le client)
      draw(8.75, [$("#s5-ay"), $("#s5-ax")], 0.55, "power3.out", 0.08);
      draw(9.15, [$("#s5-aya"), $("#s5-axa")], 0.22, "power2.out", 0.05);
      fadeIn(9.0, [$("#s5-grid"), $("#s5-yt")], 0.4, 0.08);
      blurIn(9.05, $("#s5-lab-y"), 0.18);
      [0, 1].forEach((i) => {
        const b = $("#s5-bar" + i);
        const top = parseFloat(b.getAttribute("data-top")), h = parseFloat(b.getAttribute("data-h"));
        tl.fromTo(b, { attr: { y: __AY__, height: 0 } }, { attr: { y: top, height: h }, duration: 0.75, ease: "power3.out" }, 9.4 + i * 0.3);
        blurIn(9.65 + i * 0.3, $("#s5-cat" + i), 0.18);
      });
      // PAGE 3 — couverture du rapport, conforme à la norme
      blurOut(11.6, t2, 0.16, 0.02);
      blurOut(11.6, [$("#s5-chart"), $("#s5-lab-y"), $("#s5-cat0"), $("#s5-cat1")], 0.2, 0.02);
      pageOut(11.6, P2);
      pageIn(11.8, P3);
      blurIn(11.9, t3, 0.15, 0.067);
      draw(11.9, $("#s5-acc"), 0.4, "power2.out");
      blurIn(11.95, $("#s5-ct"), 0.2);
      blurIn(12.15, $("#s5-cs"), 0.2);
      draw(12.0, $$(".s5-ill"), 0.4, "power2.out", 0.05);
      fadeIn(12.4, $("#s5-hotc"), 0.3);
      fadeIn(12.5, $("#s5-mlogo"), 0.35);
      tl.fromTo($("#s5-stamp"), { opacity: 0, scale: 1.45, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: 0.32, ease: "back.out(1.8)" }, 12.8);
      //   ce que contient le rapport
      draw(13.0, $$(".s5-box"), 0.3, "power2.out", 0.1);
      blurIn(13.1, [$("#s5-i0"), $("#s5-i1"), $("#s5-i2"), $("#s5-i3")], 0.18, 0.15);
      S5_CHECKS.forEach((t, i) => draw(t, $("#s5-k" + i), 0.28, "power2.out"));
      //   le rapport contient le lien vers la plateforme en ligne
      tl.fromTo($("#s5-link"), { opacity: 0, scale: 0.9, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.6)" }, 13.0);
      // 4. toutes les cases cochées, le curseur arrive et clique sur le lien ; la fenêtre de la plateforme s'ouvre depuis le lien
      const cur = $("#s5-cur");
      tl.fromTo(cur, { x: __CUX0__, y: __CUY0__, opacity: 0 }, { x: __CUX__, y: __CUY__, opacity: 1, duration: 0.45, ease: "power2.out" }, 14.75);
      tl.to(cur, { scale: 0.82, duration: 0.07, ease: "power1.in", yoyo: true, repeat: 1 }, 15.25);
      tl.to($("#s5-link"), { backgroundColor: "#FFD2BC", duration: 0.08, yoyo: true, repeat: 1 }, 15.25);
      blurOut(15.4, [...t3, $("#s5-i0"), $("#s5-i1"), $("#s5-i2"), $("#s5-i3")], 0.2, 0.015);
      blurOut(15.42, [$("#s5-check")], 0.2, 0);
      tl.set($("#s5-open"), { opacity: 1 }, 15.48);
      // (le rectangle finit exactement sur le cadre de la fenêtre de la scène 6 : trait de 2,5 px centré, rayon 18 px à l'extérieur)
      tl.fromTo($("#s5-open"), { attr: { x: __LX__, y: __LY__, width: __LW__, height: __LH__, rx: __LR__, fill: "#FFF1E8", stroke: "#FF5700", "stroke-width": 2 } },
        { attr: { x: __WX__, y: __WY__, width: __WW__, height: __WH__, rx: 16.75, fill: "#FFFFFF", stroke: "#111111", "stroke-width": 2.5 }, duration: 0.6, ease: "power3.inOut", immediateRender: false }, 15.5);
      tl.to($("#s5-docw"), { opacity: 0, filter: "blur(6px)", duration: 0.3, ease: "power2.in" }, 15.55);"""
    js = (js.replace("__B2X__", n(BOX2[0])).replace("__B2Y__", n(BOX2[1])).replace("__B2W__", n(BOX2[2])).replace("__B2H__", n(BOX2[3])))
    cux, cuy = lx0 + (lx1 - lx0) * 0.66, (ly0 + ly1) / 2 + 4
    js = js.replace("__AY__", str(S5_AY)).replace("S5_CHECKS", str(S5_CHECKS))
    for k, v in dict(CUX0=W + 60, CUY0=cuy + H * 0.25, CUX=cux, CUY=cuy, WX=wx + 1.25, WY=wy + 1.25, WW=ww - 2.5, WH=wh - 2.5,
                     LX=lx0, LY=ly0, LW=lx1 - lx0, LH=ly1 - ly0, LR=(ly1 - ly0) / 2).items():
        js = js.replace(f"__{k}__", n(v))
    write_scene(
        "s5",
        "Scène 5 — Rapport d'inspection thermique : défauts, résultats, couverture conforme IEC TS 62446-3, lien vers la plateforme",
        [
            svar("s5-t1", "Scène 5 — titre page 1", "Chaque défaut est|localisé et *qualifié*."),
            svar("s5-t2", "Scène 5 — titre page 2", "Classés par *gravité*,|avec l’action à mener."),
            svar("s5-t3", "Scène 5 — titre page 3", "Un rapport *aux normes*,|pour agir rapidement."),
            svar("s5-i0", "Scène 5 — ligne 1", items[0]),
            svar("s5-i1", "Scène 5 — ligne 2", items[1]),
            svar("s5-i2", "Scène 5 — ligne 3", items[2]),
            svar("s5-i3", "Scène 5 — ligne 4", items[3]),
        ],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# S6 — Plateforme en ligne : liste des anomalies, vues IR / RVB du module sélectionné, carte de l'installation
# (aucun nom ni logo de logiciel ; couleurs et typographie Fly Scan'Air ; valeurs illustratives, cohérentes avec le rapport)
# --------------------------------------------------------------------------
S6_ROWS = [  # type, module (rangée, colonne), catégorie, ΔT, MaxT, indice de l'anomalie dans ANOM
    ("Diode by-pass", (1, 4), 5, "7,8", "54", 1),
    ("Point chaud", (1, 4), 4, "11,2", "58", 0),
    ("Module à vide", (2, 2), 4, "6,1", "49", 0),
    ("Boîte de jonction", (1, 4), 3, "9,4", "56", 2),
    ("Cellules échauffées", (2, 5), 2, "4,3", "47", 0),
    ("Point chaud", (0, 1), 2, "3,5", "45", 0),
    ("Point chaud", (0, 6), 1, "2,1", "43", 0),
]
S6_PICK = (1, 2)  # lignes cliquées par le curseur
CAT_COL = {k: col for k, _, col, _ in S5_CATS}
FW_, FH_ = COLS * PW + (COLS - 1) * GX, ROWS * PH + (ROWS - 1) * GY  # champ : 1542 x 536


def mod_name(r, c):
    return f"{'ABC'[r]}{c + 1}"


def anom_cells(kind, *a):
    """Cellules couvertes par une anomalie : (i0, j0, i1, j1, marge) — cadre de détection des vues IR."""
    if kind in ("spot", "crack"):
        return a[0], a[1], a[0], a[1], 0.35
    if kind == "band":
        return 0, a[0], CC - 1, a[0] + 1, 0.12
    if kind == "jbox":
        return CC - 1, 2, CC - 1, 3, 0.25
    if kind == "cell":
        return a[0], a[1], a[0], a[1] + 1, 0.3
    return 0, 0, CC - 1, CR - 1, 0.1


def s6_panel(view, r, c, x, y, s):
    """Module (r, c) à l'échelle s : vue thermique (IR) ou vue visible (RVB, le défaut ne se voit pas)."""
    w, h = PW * s, PH * s
    frame = f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="none" stroke="{INK}" stroke-width="2"/>'
    if view == "ir":
        return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="{th_fill(r, c)}"/>'
                + cell_tint(r, c, x, y, s) + anomalies_svg(r, c, x, y, s, "s6")
                + f'<path d="{cell_lines(x, y, w, h)}" stroke="{TH_CELL}" stroke-width="1" fill="none"/>' + frame)
    return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="{PANEL}"/>'
            f'<path d="{busbars(x, y, w, h)}" stroke="#E4E4E7" stroke-width="1" fill="none"/>'
            f'<path d="{cell_lines(x, y, w, h)}" stroke="{CELL}" stroke-width="1" fill="none"/>'
            f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="url(#s6-sheen)"/>' + frame)


def s6_layout():
    wx, wy, ww, wh = P6["win"]
    ui, rh = P6["ui"], P6["rh"]
    lx, ly, lw, lh = P6["list"]
    th, ch = ui * 2.3, ui * 1.9
    rows_y = [wy + ly + th + ch + i * rh for i in range(len(S6_ROWS))]
    return dict(th=th, ch=ch, rows_y=rows_y, row_x=wx + lx + lw * 0.3)


def s5_cursor_end():
    lx0, ly0 = doc_to_screen(S5_LINK[0], S5_LINK[1])
    lx1, ly1 = doc_to_screen(S5_LINK[0] + S5_LINK[2], S5_LINK[1] + S5_LINK[3])
    return lx0 + (lx1 - lx0) * 0.66, (ly0 + ly1) / 2 + 4


def build_s6():
    wx, wy, ww, wh = P6["win"]
    ui, rh, bar = P6["ui"], P6["rh"], P6["bar"]
    lay = s6_layout()
    th, ch = lay["th"], lay["ch"]

    def R(key):
        x, y, w, h = P6[key]
        return wx + x, wy + y, w, h

    lx, ly, lw, lh = R("list")
    dx_, dy_, dw, dh = R("detail")
    mx, my, mw, mh = R("map")
    out = []
    # ---- barre de l'application
    out.append(f'<line id="s6-bar" class="d" pathLength="1" x1="{wx}" y1="{wy + bar}" x2="{wx + ww}" y2="{wy + bar}" stroke="{INK}" stroke-width="2"/>')
    out.append(f'<g id="s6-dots" fill="none" stroke="{INK}" stroke-width="2">'
               + "".join(f'<circle cx="{wx + 32 + 24 * i}" cy="{n(wy + bar / 2)}" r="6.5"/>' for i in range(3)) + "</g>")
    crumb = "Centrale photovoltaïque · Inspection thermique" if ww > 1200 else "Centrale photovoltaïque"
    out.append(f'<text id="s6-app" class="ui" x="{wx + 130}" y="{n(wy + bar / 2 + ui * 0.38)}" font-size="{n(ui * 1.05)}">'
               f'<tspan class="b">Plateforme en ligne</tspan><tspan class="g" dx="{n(ui * 0.8)}">·  {crumb}</tspan></text>')
    bs = bar * 0.62
    btns = []
    for i, ic in enumerate(("chart-bar", "map-trifold", "download-simple")):
        bx = wx + ww - 24 - (3 - i) * bs - (2 - i) * 10
        by = wy + (bar - bs) / 2
        on = ic == "map-trifold"
        btns.append(f'<rect x="{n(bx)}" y="{n(by)}" width="{n(bs)}" height="{n(bs)}" rx="8" fill="{"#FFF1E8" if on else "#FFFFFF"}" stroke="{ACC if on else "#D4D4D8"}" stroke-width="1.5"/>'
                    f'<g transform="translate({n(bx + bs * 0.2)} {n(by + bs * 0.2)}) scale({bs * 0.6 / 256:.4f})"><path d="{ICONS[ic]}" fill="{ACC if on else INK}"/></g>')
    out.append(f'<g id="s6-btns">{"".join(btns)}</g>')
    # ---- volets (cadres tracés)
    for key in ("list", "detail", "map"):
        x, y, w, h = R(key)
        out.append(f'<rect class="s6-pfill" x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="10" fill="#FFFFFF"/>')
        out.append(f'<rect class="d s6-pane" pathLength="1" x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="10" fill="none" stroke="#C9CBD1" stroke-width="1.5"/>')
    # ---- liste des anomalies
    narrow = lw < 700
    cols = dict(num=lx + (14 if narrow else 18), typ=lx + (50 if narrow else lw * 0.085), mod=lx + lw * 0.56,
                cat=lx + lw * (0.73 if narrow else 0.72), dt=lx + lw - 20)
    out.append(f'<text class="ui b s6-lh" x="{n(lx + 18)}" y="{n(ly + th * 0.64)}" font-size="{n(ui * 1.1)}">Anomalies '
               f'<tspan class="acc">({len(S6_ROWS)})</tspan></text>')
    hy = ly + th + ch * 0.64
    for key, lab, anchor in (("num", "N°", "start"), ("typ", "Type", "start"), ("mod", "Module", "start"), ("cat", "Gravité", "start"), ("dt", "ΔT" if narrow else "ΔT (°C)", "end")):
        out.append(f'<text class="ui g s6-lh" x="{n(cols[key])}" y="{n(hy)}" font-size="{n(ui * 0.88)}" text-anchor="{anchor}">{lab}</text>')
    out.append(f'<g class="s6-sep" stroke="#E4E4E7" stroke-width="1.5"><line x1="{n(lx)}" y1="{n(ly + th)}" x2="{n(lx + lw)}" y2="{n(ly + th)}"/>'
               f'<line x1="{n(lx)}" y1="{n(ly + th + ch)}" x2="{n(lx + lw)}" y2="{n(ly + th + ch)}"/></g>')
    y0 = lay["rows_y"][0]
    out.append(f'<g id="s6-sel" transform="translate(0 0)"><rect x="{n(lx + 1.5)}" y="{n(y0)}" width="{n(lw - 3)}" height="{n(rh)}" fill="#FFF1E8"/>'
               f'<rect x="{n(lx + 1.5)}" y="{n(y0)}" width="5" height="{n(rh)}" fill="{ACC}"/></g>')
    bsz = ui * 1.3
    for i, (typ, (r, c), cat, dt, mxt, _) in enumerate(S6_ROWS):
        yy = lay["rows_y"][i]
        base = yy + rh / 2 + ui * 0.36
        ink = "#FFFFFF" if cat >= 5 else INK
        sep = "" if i == len(S6_ROWS) - 1 else f'<line x1="{n(lx + 12)}" y1="{n(yy + rh)}" x2="{n(lx + lw - 12)}" y2="{n(yy + rh)}" stroke="#F0F0F2" stroke-width="1.5"/>'
        out.append(f'<g class="s6-row">{sep}'
                   f'<text class="ui g" x="{n(cols["num"])}" y="{n(base)}" font-size="{ui}">{i + 1}</text>'
                   f'<text class="ui" x="{n(cols["typ"])}" y="{n(base)}" font-size="{ui}">{typ}</text>'
                   f'<text class="ui" x="{n(cols["mod"])}" y="{n(base)}" font-size="{ui}">{mod_name(r, c)}</text>'
                   f'<rect x="{n(cols["cat"])}" y="{n(yy + (rh - bsz) / 2)}" width="{n(bsz)}" height="{n(bsz)}" rx="6" fill="{CAT_COL[cat]}"/>'
                   f'<text class="ui b" x="{n(cols["cat"] + bsz / 2)}" y="{n(base)}" font-size="{n(ui * 0.95)}" text-anchor="middle" style="fill: {ink}">{cat}</text>'
                   f'<text class="ui" x="{n(cols["dt"])}" y="{n(base)}" font-size="{ui}" text-anchor="end">{dt}</text></g>')
    # ---- détail du module sélectionné : vues IR et RVB
    pad = 18
    wide = dw >= 700
    out.append(f'<text id="s6-empty" class="ui g" x="{n(dx_ + dw / 2)}" y="{n(dy_ + dh / 2)}" font-size="{ui}" text-anchor="middle">Sélectionnez une anomalie</text>')
    defs = [thermal_defs("s6"),
            '<linearGradient id="s6-sheen" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0.75"/>'
            '<stop offset="0.45" stop-color="#FFFFFF" stop-opacity="0"/><stop offset="1" stop-color="#D4D4D8" stop-opacity="0.35"/></linearGradient>',
            f'<linearGradient id="s6-tgrad" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{TH_PANEL}"/><stop offset="0.5" stop-color="#FFB48A"/>'
            f'<stop offset="1" stop-color="{ACC}"/></linearGradient>',
            f'<linearGradient id="s6-tgradh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{TH_PANEL}"/><stop offset="0.5" stop-color="#FFB48A"/>'
            f'<stop offset="1" stop-color="{ACC}"/></linearGradient>']
    bd = ui * 1.7
    for k, ri in enumerate(S6_PICK):
        typ, (r, c), cat, dt, mxt, ai = S6_ROWS[ri]
        kind, *aa = ANOM[(r, c)][ai]
        g = [f'<g id="s6-d{k}" class="s6-det">']
        ink = "#FFFFFF" if cat >= 5 else INK
        g.append(f'<g class="s6-badge"><rect x="{n(dx_ + pad)}" y="{n(dy_ + pad)}" width="{n(bd)}" height="{n(bd)}" rx="7" fill="{CAT_COL[cat]}"/>'
                 f'<text class="ui b" x="{n(dx_ + pad + bd / 2)}" y="{n(dy_ + pad + bd / 2 + ui * 0.38)}" font-size="{n(ui * 1.05)}" text-anchor="middle" style="fill: {ink}">{cat}</text></g>')
        tx = dx_ + pad + bd + 14
        info = [f"Rangée {'ABC'[r]} · module {c + 1}", f"ΔT {dt} °C · MaxT {mxt} °C"]
        if wide:  # type et informations sur la même ligne que la pastille de gravité
            g.append(f'<text class="ui s6-dt" x="{n(tx)}" y="{n(dy_ + pad + bd / 2 + ui * 0.42)}" font-size="{n(ui * 1.15)}">'
                     f'<tspan class="b">{typ}</tspan><tspan class="g" dx="{n(ui * 0.9)}" font-size="{n(ui * 0.92)}">'
                     f'{"   ·   ".join(info)}</tspan></text>')
            vy = dy_ + pad + bd + 14
        else:
            g.append(f'<text class="ui b s6-dt" x="{n(tx)}" y="{n(dy_ + pad + bd / 2 + ui * 0.42)}" font-size="{n(ui * 1.15)}">{typ}</text>')
            iy = dy_ + pad + bd + ui * 1.45
            for j, line in enumerate(info):
                g.append(f'<text class="ui g s6-dt" x="{n(dx_ + pad)}" y="{n(iy + j * ui * 1.3)}" font-size="{n(ui * 0.92)}">{line}</text>')
            vy = iy + ui * 1.3 + ui * 0.95
        cw = (dw - 3 * pad) / 2
        tabh = ui * 1.45
        ib_y = vy + tabh + 8
        ib_h = dy_ + dh - pad - ib_y
        for j, (view, lab) in enumerate((("ir", "IR"), ("rvb", "RVB"))):
            xc = dx_ + pad + j * (cw + pad)
            tw = ui * (2.2 if view == "ir" else 3.0)
            dark = view == "ir"
            g.append(f'<g class="s6-tab"><rect x="{n(xc)}" y="{n(vy)}" width="{n(tw)}" height="{n(tabh)}" rx="{n(tabh / 2)}" fill="{INK if dark else "#F3F3F4"}"/>'
                     f'<text class="ui b" x="{n(xc + tw / 2)}" y="{n(vy + tabh / 2 + ui * 0.33)}" font-size="{n(ui * 0.85)}" text-anchor="middle" style="fill: {"#FFFFFF" if dark else INK}">{lab}</text></g>')
            g.append(f'<rect class="s6-ibox" x="{n(xc)}" y="{n(ib_y)}" width="{n(cw)}" height="{n(ib_h)}" rx="8" fill="#FAFAFA" stroke="#E4E4E7" stroke-width="1.5"/>')
            hbar = cw < 300  # case étroite (1:1) : échelle horizontale sous l'image, sinon verticale à droite
            bar_w = 64 if (view == "ir" and not hbar) else 0
            bar_h = 46 if hbar else 0
            sc = min((cw - 24 - bar_w) / PW, (ib_h - 20 - bar_h) / PH)
            px, py = xc + (cw - bar_w - PW * sc) / 2, ib_y + (ib_h - bar_h - PH * sc) / 2
            i0, j0, i1, j1, m = anom_cells(kind, *aa)
            cwp, chp = CWU * sc, CHU * sc
            bb = (px + (i0 - m) * cwp, py + (j0 - m) * chp, (i1 - i0 + 1 + 2 * m) * cwp, (j1 - j0 + 1 + 2 * m) * chp)
            if view == "ir":
                defs.append(f'<clipPath id="s6-irc{k}"><rect id="s6-ircr{k}" x="{n(xc)}" y="{n(ib_y)}" width="0" height="{n(ib_h)}"/></clipPath>')
                # réticule sur le point le plus chaud, avec sa température (comme un logiciel de thermographie)
                ax_, ay_ = anom_center(kind, *aa)
                hx, hy = px + ax_ * sc, py + ay_ * sc
                arm, gap_ = 11, 4
                xh = "".join(f'<path d="M{n(hx - arm)} {n(hy)}H{n(hx - gap_)}M{n(hx + gap_)} {n(hy)}H{n(hx + arm)}M{n(hx)} {n(hy - arm)}V{n(hy - gap_)}M{n(hx)} {n(hy + gap_)}V{n(hy + arm)}" '
                             f'stroke="{col}" stroke-width="{wdt}" stroke-linecap="round" fill="none"/>' for col, wdt in (("#FFFFFF", 4.5), (INK, 1.8)))
                tlab = f'{mxt},0 °C'
                lx_ = hx + 14 if hx < px + PW * sc * 0.6 else hx - 14
                anchor = "start" if hx < px + PW * sc * 0.6 else "end"
                ty_ = hy - 12 if bb[3] > PH * sc * 0.8 else min(hy - 12, bb[1] - 7)  # au-dessus du cadre quand il est petit
                xh += (f'<text class="ui b" x="{n(lx_)}" y="{n(ty_)}" font-size="{n(ui * 0.8)}" text-anchor="{anchor}" '
                       f'style="paint-order: stroke; stroke: #FFFFFF; stroke-width: 4px; stroke-linejoin: round">{tlab}</text>')
                # échelle des températures, à droite de l'image
                tmin = int(mxt) - round(float(dt.replace(",", "."))) - 2
                if hbar:
                    sx0, sx1, sy = xc + 44, xc + cw - 44, py + PH * sc + 24
                    scale = (f'<g class="s6-tscale"><rect x="{n(sx0)}" y="{n(sy)}" width="{n(sx1 - sx0)}" height="10" rx="5" fill="url(#s6-tgradh)"/>'
                             f'<text class="ui g" x="{n(sx0 - 8)}" y="{n(sy + 5 + ui * 0.3)}" font-size="{n(ui * 0.7)}" text-anchor="end">{tmin}°</text>'
                             f'<text class="ui g" x="{n(sx1 + 8)}" y="{n(sy + 5 + ui * 0.3)}" font-size="{n(ui * 0.7)}">{mxt}°</text></g>')
                else:
                    sx, sy0, sy1 = xc + cw - 34, ib_y + 34, ib_y + ib_h - 30
                    scale = (f'<g class="s6-tscale"><rect x="{n(sx)}" y="{n(sy0)}" width="10" height="{n(sy1 - sy0)}" rx="5" fill="url(#s6-tgrad)"/>'
                             f'<text class="ui g" x="{n(sx + 5)}" y="{n(sy0 - 9)}" font-size="{n(ui * 0.7)}" text-anchor="middle">{mxt}°</text>'
                             f'<text class="ui g" x="{n(sx + 5)}" y="{n(sy1 + ui * 0.75 + 6)}" font-size="{n(ui * 0.7)}" text-anchor="middle">{tmin}°</text></g>')
                g.append(f'<g clip-path="url(#s6-irc{k})">{s6_panel("ir", r, c, px, py, sc)}</g>{scale}'
                         f'<line id="s6-irs{k}" x1="{n(xc)}" y1="{n(ib_y)}" x2="{n(xc)}" y2="{n(ib_y + ib_h)}" stroke="{ACC}" stroke-width="3" data-w="{n(cw)}"/>'
                         f'<rect id="s6-bb{k}" x="{n(bb[0])}" y="{n(bb[1])}" width="{n(bb[2])}" height="{n(bb[3])}" rx="4" fill="none" stroke="{ACC}" stroke-width="2.5"/>'
                         f'<g id="s6-xh{k}">{xh}</g>')
            else:  # même cadre, en pointillé : à l'œil nu, rien ne se voit
                g.append(f'<g id="s6-rvb{k}">{s6_panel("rvb", r, c, px, py, sc)}'
                         f'<rect x="{n(bb[0])}" y="{n(bb[1])}" width="{n(bb[2])}" height="{n(bb[3])}" rx="4" fill="none" stroke="{INK}" stroke-width="1.8" stroke-dasharray="5 4"/></g>')
        g.append("</g>")
        out.append("".join(g))
    # ---- carte de l'installation (vue du dessus, dessinée)
    fs_ = min((mw - (120 if mw >= 600 else 60)) / FW_, (mh - 140) / FH_)
    fx, fy = mx + (mw - FW_ * fs_) / 2, my + (mh - FH_ * fs_) / 2 - 10
    defs.append(f'<clipPath id="s6-mapclip"><rect x="{n(mx + 1.5)}" y="{n(my + 1.5)}" width="{n(mw - 3)}" height="{n(mh - 3)}" rx="9"/></clipPath>')

    def M(x, y):
        return fx + (x - FX0) * fs_, fy + (y - FY0) * fs_

    k_ = fs_ / 0.47
    terrain = [
        f'<rect x="{n(fx - 26 * k_)}" y="{n(fy - 26 * k_)}" width="{n(FW_ * fs_ + 52 * k_)}" height="{n(FH_ * fs_ + 52 * k_)}" rx="6" fill="#ECECEE" stroke="#D4D4D8" stroke-width="1.5" stroke-dasharray="6 6"/>',
    ]
    for j, (u, v, rr) in enumerate(((0.07, 0.12, 26), (0.15, 0.2, 18), (0.9, 0.1, 22), (0.95, 0.24, 16), (0.06, 0.78, 20), (0.93, 0.8, 24), (0.85, 0.9, 15))):
        terrain.append(f'<circle cx="{n(mx + u * mw)}" cy="{n(my + v * mh)}" r="{n(rr * k_)}" fill="#E4E4E7" stroke="#C9CBD1" stroke-width="1.5"/>')
    mods = []
    for r in range(ROWS):
        for c in range(COLS):
            x, y = M(*panel_xy(r, c))
            w, h = PW * fs_, PH * fs_
            mods.append(f'<g class="s6-mod"><rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="{th_fill(r, c)}"/>'
                        + cell_tint(r, c, x, y, fs_) + anomalies_svg(r, c, x, y, fs_, "s6")
                        + f'<path d="{cell_lines(x, y, w, h)}" stroke="{TH_CELL}" stroke-width="0.8" fill="none"/>'
                        f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="none" stroke="{INK}" stroke-width="1.3"/></g>')
    frame_col = {5: ACC, 4: "#FF8A4C", 3: "#E8853F", 2: "#6B6B70", 1: "#A1A1AA"}  # traits lisibles sur le fond thermique
    mks, rings, sel_rects = [], [], []
    for ri, (typ, (r, c), cat, dt, mxt, ai) in enumerate(S6_ROWS):
        kind, *aa = ANOM[(r, c)][ai]
        i0, j0, i1, j1, m = anom_cells(kind, *aa)
        x0, y0 = M(*panel_xy(r, c))
        cwm, chm = CWU * fs_, CHU * fs_
        fr = (x0 + (i0 - m) * cwm, y0 + (j0 - m) * chm, (i1 - i0 + 1 + 2 * m) * cwm, (j1 - j0 + 1 + 2 * m) * chm)
        mks.append(f'<rect class="s6-mk" x="{n(fr[0])}" y="{n(fr[1])}" width="{n(fr[2])}" height="{n(fr[3])}" rx="2" fill="none" '
                   f'stroke="{frame_col[cat]}" stroke-width="2"/>')
        if ri in S6_PICK:
            k = S6_PICK.index(ri)
            rings.append(f'<rect id="s6-ring{k}" x="{n(fr[0])}" y="{n(fr[1])}" width="{n(fr[2])}" height="{n(fr[3])}" rx="2" fill="none" stroke="{ACC}" stroke-width="2.5"/>')
            sel_rects.append((fr[0] - 4, fr[1] - 4, fr[2] + 8, fr[3] + 8))
    ctrl_x, ctrl_y, cs_ = mx + mw - 20 - 34 * k_ ** 0.5, my + mh - 20 - 70 * k_ ** 0.5, 34 * k_ ** 0.5
    ctrl = (f'<g id="s6-ctrl"><rect x="{n(ctrl_x)}" y="{n(ctrl_y)}" width="{n(cs_)}" height="{n(2 * cs_)}" rx="6" fill="#FFFFFF" stroke="#C9CBD1" stroke-width="1.5"/>'
            f'<line x1="{n(ctrl_x + 6)}" y1="{n(ctrl_y + cs_)}" x2="{n(ctrl_x + cs_ - 6)}" y2="{n(ctrl_y + cs_)}" stroke="#E4E4E7" stroke-width="1.5"/>'
            f'<path d="M{n(ctrl_x + cs_ * 0.3)} {n(ctrl_y + cs_ * 0.5)}H{n(ctrl_x + cs_ * 0.7)}M{n(ctrl_x + cs_ * 0.5)} {n(ctrl_y + cs_ * 0.3)}V{n(ctrl_y + cs_ * 0.7)}'
            f'M{n(ctrl_x + cs_ * 0.3)} {n(ctrl_y + cs_ * 1.5)}H{n(ctrl_x + cs_ * 0.7)}" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>'
            f'<line x1="{n(mx + 24)}" y1="{n(my + mh - 30)}" x2="{n(mx + 24 + 90 * k_)}" y2="{n(my + mh - 30)}" stroke="{INK}" stroke-width="2"/>'
            f'<path d="M{n(mx + 24)} {n(my + mh - 36)}V{n(my + mh - 24)}M{n(mx + 24 + 90 * k_)} {n(my + mh - 36)}V{n(my + mh - 24)}" stroke="{INK}" stroke-width="2"/>'
            f'<text class="ui g" x="{n(mx + 24 + 90 * k_ + 10)}" y="{n(my + mh - 30 + ui * 0.33)}" font-size="{n(ui * 0.85)}">10 m</text>'
            f'<path d="M{n(mx + mw - 34)} {n(my + 22)}l10 26l-10 -7l-10 7Z" fill="{INK}"/>'
            f'<text class="ui b" x="{n(mx + mw - 34)}" y="{n(my + 22 + 26 + ui * 1.05)}" font-size="{n(ui * 0.85)}" text-anchor="middle">N</text></g>')
    tg_h = ui * 1.35
    tg_x, tg_y = mx + 16, my + 16
    toggle = (f'<g id="s6-layer"><rect x="{n(tg_x)}" y="{n(tg_y)}" width="{n(ui * 5.4)}" height="{n(tg_h)}" rx="{n(tg_h / 2)}" fill="#FFFFFF" stroke="#C9CBD1" stroke-width="1.5"/>'
              f'<rect x="{n(tg_x + 3)}" y="{n(tg_y + 3)}" width="{n(ui * 2.4)}" height="{n(tg_h - 6)}" rx="{n((tg_h - 6) / 2)}" fill="{INK}"/>'
              f'<text class="ui b" x="{n(tg_x + 3 + ui * 1.2)}" y="{n(tg_y + tg_h / 2 + ui * 0.3)}" font-size="{n(ui * 0.8)}" text-anchor="middle" style="fill: #FFFFFF">IR</text>'
              f'<text class="ui b" x="{n(tg_x + ui * 3.95)}" y="{n(tg_y + tg_h / 2 + ui * 0.3)}" font-size="{n(ui * 0.8)}" text-anchor="middle">RVB</text></g>')
    ctrl = ctrl.replace('<g id="s6-ctrl">', '<g id="s6-ctrl">' + toggle, 1)
    s0r, s1r = sel_rects
    out.append(f'<g clip-path="url(#s6-mapclip)"><rect id="s6-mapbg" x="{n(mx)}" y="{n(my)}" width="{n(mw)}" height="{n(mh)}" fill="#F4F4F5"/>'
               f'<g id="s6-terrain">{"".join(terrain)}</g>{"".join(mods)}'
               f'<rect id="s6-msel" x="{n(s0r[0])}" y="{n(s0r[1])}" width="{n(s0r[2])}" height="{n(s0r[3])}" rx="5" fill="none" stroke="{ACC}" stroke-width="3"/>'
               f'{"".join(mks)}{"".join(rings)}{ctrl}</g>')
    # interface illustrée : textes de détail volontairement à la taille d'un vrai écran (data-layout-ignore)
    svg = (f'    <svg id="s6-svg" class="world" data-layout-ignore viewBox="0 0 {W} {H}" width="{W}" height="{H}"{CANVAS}><defs>{"".join(defs)}</defs>\n      '
           + "\n      ".join(out) + "\n    </svg>")
    tl_, tt_, ts_ = P6["title"]
    body = (f'    <div id="s6-win" class="win" style="left: {wx}px; top: {wy}px; width: {ww}px; height: {wh}px"></div>\n{svg}\n'
            f'    <div id="s6-title" class="title" style="left: {tl_}px; top: {tt_}px; font-size: {ts_}px">Suivez votre installation<br />sur notre plateforme en ligne.</div>\n'
            f'    {cursor_html("s6-cur")}')
    css = f"""
    #root .ui {{ font-family: "Comfortaa", sans-serif; font-weight: 600; fill: #111111; stroke: none; }}
    #root .ui.b, #root .ui .b {{ font-weight: 700; }}
    #root .ui.g, #root .ui .g {{ fill: #6B6B70; }}
    #root .ui .acc {{ fill: #FF5700; }}{CUR_CSS}
    #root #s6-dots, #root #s6-app, #root #s6-btns, #root .s6-pfill, #root .s6-lh, #root .s6-sep, #root .s6-row, #root #s6-sel, #root #s6-empty,
    #root .s6-det, #root #s6-mapbg, #root #s6-terrain, #root .s6-mod, #root .s6-mk, #root #s6-ctrl, #root #s6-msel, #root #s6-ring0, #root #s6-ring1,
    #root #s6-irs0, #root #s6-irs1, #root #s6-bb0, #root #s6-bb1, #root #s6-xh0, #root #s6-xh1, #root .s6-tscale {{ opacity: 0; }}"""
    cx0, cy0 = s5_cursor_end()
    rys = [lay["rows_y"][i] + rh / 2 + 4 for i in S6_PICK]
    js = f"""
      const title = words($("#s6-title"), txt("s6-title", "{P6["text"]}"));
      const cur = $("#s6-cur");
      tl.set(cur, {{ x: {n(cx0)}, y: {n(cy0)} }}, 0);
      // 1. la fenêtre (ouverte depuis le lien du rapport) se remplit : barre, volets, liste, carte
      draw(0.0, $("#s6-bar"), 0.45, "power2.out");
      fadeIn(0.15, $("#s6-dots"), 0.3);
      blurIn(0.2, [$("#s6-app"), $("#s6-btns")], 0.2, 0.1);
      fadeIn(0.1, $$(".s6-pfill"), 0.35, 0.08);
      draw(0.1, $$(".s6-pane"), 0.6, "power2.inOut", 0.1);
      blurIn(0.25, title, 0.15, 0.067);
      blurIn(0.45, $$(".s6-lh"), 0.18, 0.04);
      fadeIn(0.5, $$(".s6-sep"), 0.3);
      blurIn(0.6, $$(".s6-row"), 0.18, 0.06);
      fadeIn(0.35, $("#s6-mapbg"), 0.4);
      fadeIn(0.45, $("#s6-terrain"), 0.5);
      fadeIn(0.6, $$(".s6-mod"), 0.3, 0.012);
      tl.fromTo($$(".s6-mk"), {{ opacity: 0, scale: 0, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)", stagger: 0.07 }}, 1.0);
      fadeIn(0.9, $("#s6-ctrl"), 0.3);
      blurIn(0.9, $("#s6-empty"), 0.2);
      // 2. le curseur choisit une anomalie : ligne surlignée, module repéré sur la carte, vues IR et RVB
      const sel = $("#s6-sel"), ms = $("#s6-msel");
      const MS = {[[round(v, 2) for v in rr] for rr in sel_rects]};
      const detail = (k, t) => {{
        const D = $("#s6-d" + k);
        tl.set(D, {{ opacity: 1 }}, t);
        tl.fromTo(D.querySelector(".s6-badge"), {{ opacity: 0, scale: 0.6, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: "back.out(1.8)" }}, t);
        blurIn(t + 0.05, Array.from(D.querySelectorAll(".s6-dt")), 0.18, 0.06);
        fadeIn(t + 0.1, Array.from(D.querySelectorAll(".s6-tab, .s6-ibox, .s6-tscale")), 0.25, 0.05);
        const scan = $("#s6-irs" + k), w = parseFloat(scan.getAttribute("data-w"));
        tl.fromTo($("#s6-ircr" + k), {{ attr: {{ width: 0 }} }}, {{ attr: {{ width: w }}, duration: 0.6, ease: "power1.inOut" }}, t + 0.15);
        tl.fromTo(scan, {{ opacity: 1, x: 0 }}, {{ x: w, duration: 0.6, ease: "power1.inOut" }}, t + 0.15);
        fadeOut(t + 0.75, scan, 0.12);
        fadeIn(t + 0.3, $("#s6-rvb" + k), 0.45);
        tl.fromTo($("#s6-bb" + k), {{ opacity: 0, scale: 1.4, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.6)" }}, t + 0.8);
        tl.fromTo($("#s6-xh" + k), {{ opacity: 0, scale: 0.5, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: "back.out(1.8)" }}, t + 0.95);
      }};
      const click = (t) => tl.to(cur, {{ scale: 0.82, duration: 0.07, ease: "power1.in", yoyo: true, repeat: 1 }}, t);
      const pulse = (k, t) => tl.fromTo($("#s6-ring" + k), {{ opacity: 0.9, scale: 1, transformOrigin: "50% 50%" }}, {{ opacity: 0, scale: 1.9, duration: 0.9, ease: "power2.out", immediateRender: false }}, t);
      tl.to(cur, {{ x: {n(lay["row_x"])}, y: {n(rys[0])}, duration: 0.6, ease: "power2.inOut" }}, 1.6);
      click(2.25);
      tl.fromTo(sel, {{ opacity: 0, y: {n(S6_PICK[0] * rh)} }}, {{ opacity: 1, y: {n(S6_PICK[0] * rh)}, duration: 0.2 }}, 2.3);
      blurOut(2.3, $("#s6-empty"), 0.15);
      tl.fromTo(ms, {{ opacity: 0, scale: 1.25, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.6)" }}, 2.32);
      [2.35, 3.35].forEach((t) => pulse(0, t));
      detail(0, 2.4);
      tl.to(cur, {{ x: {n(lay["row_x"])}, y: {n(rys[1])}, duration: 0.5, ease: "power2.inOut" }}, 4.3);
      click(4.85);
      tl.to(sel, {{ y: {n(S6_PICK[1] * rh)}, duration: 0.25, ease: "power2.inOut" }}, 4.9);
      tl.to(ms, {{ attr: {{ x: MS[1][0], y: MS[1][1], width: MS[1][2], height: MS[1][3] }}, duration: 0.4, ease: "power2.inOut" }}, 4.9);
      [5.0, 6.0].forEach((t) => pulse(1, t));
      blurOut(4.9, $("#s6-d0"), 0.18, 0);
      detail(1, 5.05);
      tl.to(cur, {{ x: "+=" + {n(70 * CUR_K)}, y: "+=" + {n(90 * CUR_K)}, duration: 0.7, ease: "power2.inOut" }}, 6.1);
      // 3. sortie : tout se floute
      blurOut(7.7, title, 0.18, 0.02);
      tl.to([$("#s6-win"), $("#s6-svg"), cur], {{ opacity: 0, filter: "blur(8px)", duration: 0.32, ease: "power2.in" }}, 7.75);"""
    write_scene(
        "s6",
        "Scène 6 — Plateforme en ligne : liste des anomalies, vues IR et RVB, carte de l'installation",
        [svar("s6-title", "Scène 6 — titre", P6["text"])],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# S7 — « Retrouvez-nous sur… » : barre de recherche (générique), site web puis page LinkedIn
# --------------------------------------------------------------------------
SITE_IMG = (1989, 993)  # capture du site (assets/images/site-flyscanair.jpg : page seule, sans le navigateur)
LI_IMG = (1220, 874)  # page LinkedIn (assets/images/linkedin-flyscanair.jpg, tools/linkedin_image.cjs : barre LinkedIn comprise, sans pastilles ni données personnelles)
TYPE_DT = 0.09  # une touche toutes les 90 ms (tools/sfx.py génère le bruit de clavier sur la même cadence)
S7_Q = [  # texte tapé, début de la frappe (s, scène), adresse affichée par le navigateur, image, taille
    ("www.flyscanair.com", 0.9, "flyscanair.com", "assets/images/site-flyscanair.jpg", SITE_IMG),
    ("Fly Scan'Air", 6.05, "linkedin.com/company/fly-scan-air", "assets/images/linkedin-flyscanair.jpg", LI_IMG),
]
S7_DUR = 10.2


def build_s7():
    bw, bh, yc0, yc1 = P7["bar"]
    top_res, maxw, maxh = P7["res"]
    chrome, fs = P7["chrome"], P7["fs"]
    hy, hs = P7["head"]
    mag = bh * 0.42
    queries = "".join(f'<span id="s7-q{i}" class="q">' + "".join(f'<span class="k">{html.escape(ch_) if ch_ != " " else "&nbsp;"}</span>' for ch_ in q)
                      + "</span>" for i, (q, *_rest) in enumerate(S7_Q))
    results = []
    for i, (q, t0, url, img, (iw, ih)) in enumerate(S7_Q):
        sc = min(maxw / iw, maxh / ih)
        w, h = iw * sc, ih * sc
        x = (W - w) / 2
        dots = "".join(f'<i style="left: {18 + 22 * j}px; top: {n(chrome / 2 - 6)}px"></i>' for j in range(3))
        results.append(
            f'<div id="s7-r{i}" class="res" style="left: {n(x)}px; top: {top_res}px; width: {n(w)}px; height: {n(h + chrome)}px">'
            f'<div class="chrome" style="height: {chrome}px">{dots}<div class="addr" data-layout-ignore style="height: {n(chrome - 14)}px; font-size: {n(chrome * 0.42)}px">{url}</div></div>'
            f'<div class="shot" style="top: {chrome}px; width: {n(w)}px; height: {n(h)}px"><img id="s7-img{i}" src="{img}" width="{n(w)}" height="{n(h)}" alt="" /></div>'
            f'<div id="s7-scan{i}" class="scan7" style="top: {chrome}px; height: {n(h)}px"></div></div>')
    body = f"""    <div id="s7-head" class="title s7h" style="top: {hy}px; font-size: {hs}px">Retrouvez-nous sur…</div>
    <div id="s7-bar" class="sbar" style="left: {n((W - bw) / 2)}px; top: {n(yc0 - bh / 2)}px; width: {bw}px; height: {bh}px">
      <svg id="s7-mag" viewBox="0 0 256 256" width="{n(mag)}" height="{n(mag)}" style="margin: 0 {n(bh * 0.28)}px 0 {n(bh * 0.4)}px"><path d="{ICONS["magnifying-glass"]}" fill="{INK}"/></svg>
      <div id="s7-text" class="stext" style="font-size: {fs}px">{queries}<span id="s7-caret" class="caret" style="height: {n(fs * 1.15)}px"></span></div>
    </div>
    {"".join(results)}"""
    css = f"""
    #root .s7h {{ left: 0; width: {W}px; text-align: center; }}
    #root .sbar {{ position: absolute; box-sizing: border-box; display: flex; align-items: center; background: #FFFFFF; border: 2.5px solid #111111; border-radius: {n(bh / 2)}px; box-shadow: 0 10px 28px rgba(17, 17, 17, 0.08); opacity: 0; }}
    #root .stext {{ display: flex; align-items: center; font-family: "Comfortaa", sans-serif; font-weight: 600; color: #111111; white-space: pre; }}
    #root .q {{ display: inline-flex; border-radius: 6px; }}
    #root .k {{ display: none; }}
    #root .caret {{ display: inline-block; width: 3px; margin-left: 3px; background: #FF5700; opacity: 0; }}
    #root .res {{ position: absolute; box-sizing: border-box; background: #FFFFFF; border: 2.5px solid #111111; border-radius: 12px; overflow: hidden; opacity: 0; }}
    #root .chrome {{ position: absolute; left: 0; top: 0; right: 0; border-bottom: 2px solid #111111; }}
    #root .chrome i {{ position: absolute; width: 12px; height: 12px; box-sizing: border-box; border: 2px solid #111111; border-radius: 50%; }}
    #root .addr {{ position: absolute; left: 96px; right: 24px; top: 7px; display: flex; align-items: center; padding-left: 18px; box-sizing: border-box; border-radius: 999px; background: #F3F3F4; font-family: "Comfortaa", sans-serif; font-weight: 600; color: #3F3F46; white-space: nowrap; }}
    #root .shot {{ position: absolute; left: 0; overflow: hidden; }}
    #root .shot img {{ display: block; transform-origin: 50% 40%; }}
    #root .scan7 {{ position: absolute; left: 0; width: 4px; background: #FF5700; opacity: 0; }}"""
    js = f"""
      $("#s7-head").textContent = txt("s7-head", "Retrouvez-nous sur…");
      const bar = $("#s7-bar"), caret = $("#s7-caret");
      const keys = (i) => Array.from($("#s7-q" + i).querySelectorAll(".k"));
      const DT = {TYPE_DT};
      // 1. titre, barre de recherche, loupe ; le curseur de saisie clignote
      blurIn(0.05, $("#s7-head"), 0.2, 0);
      tl.fromTo(bar, {{ opacity: 0, scale: 0.94, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.4, ease: "back.out(1.6)" }}, 0.15);
      tl.fromTo($("#s7-mag"), {{ opacity: 0, scale: 0.5, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)" }}, 0.35);
      [0.45, 0.7, 0.95].forEach((t, i) => tl.set(caret, {{ opacity: i % 2 ? 0 : 1 }}, t));
      const type = (i, t0) => {{
        tl.set(caret, {{ opacity: 1 }}, t0);
        keys(i).forEach((k, j) => tl.set(k, {{ display: "inline" }}, t0 + j * DT));
      }};
      const result = (i, t) => {{
        const r = $("#s7-r" + i), img = $("#s7-img" + i), scan = $("#s7-scan" + i), w = r.offsetWidth;
        tl.fromTo(r, {{ opacity: 0, y: 40 }}, {{ opacity: 1, y: 0, duration: 0.4, ease: "power3.out" }}, t);
        tl.fromTo(img, {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 0.6, ease: "power1.inOut" }}, t + 0.2);
        tl.fromTo(scan, {{ opacity: 1, x: 0 }}, {{ x: w - 4, duration: 0.6, ease: "power1.inOut" }}, t + 0.2);
        fadeOut(t + 0.8, scan, 0.12);
      }};
      // 2. « www.flyscanair.com », Entrée : la barre monte, le site s'affiche
      type(0, {S7_Q[0][1]});
      tl.to(bar, {{ y: {n(yc1 - yc0)}, duration: 0.5, ease: "power3.inOut" }}, 2.8);
      blurOut(2.75, $("#s7-head"), 0.2, 0);
      result(0, 3.1);
      // 3. tout sélectionner, effacer, « Fly Scan'Air », Entrée : la page LinkedIn
      tl.set($("#s7-q0"), {{ backgroundColor: "rgba(255, 87, 0, 0.22)" }}, 5.55);
      tl.set(keys(0), {{ display: "none" }}, 5.8);
      tl.set($("#s7-q0"), {{ backgroundColor: "rgba(255, 87, 0, 0)" }}, 5.8);
      blurOut(5.6, $("#s7-r0"), 0.3, 0);
      type(1, {S7_Q[1][1]});
      result(1, 7.4);
      [7.6, 8.1, 8.6, 9.1, 9.6].forEach((t, i) => tl.set(caret, {{ opacity: i % 2 ? 1 : 0 }}, t));
      // 4. sortie vers le carton final
      blurOut(9.85, [bar, $("#s7-r1")], 0.3, 0.04);"""
    write_scene(
        "s7",
        "Scène 7 — Retrouvez-nous : recherche du site web, puis de la page LinkedIn",
        [svar("s7-head", "Scène 7 — titre", "Retrouvez-nous sur…")],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# S8 — Logo : le serpentin se trace (bruit de drone), le nom apparaît, le logo remonte, slogan et coordonnées
# --------------------------------------------------------------------------
S8_DUR = 8.4


def build_s8():
    lift = LOGO_Y0 - LOGO_Y
    st_, ss_ = P8["slogan"]
    body = f"""    <svg class="world" viewBox="0 0 {W} {H}" width="{W}" height="{H}"{CANVAS}>
      <defs>
        <radialGradient id="s8-ball" cx="0.36" cy="0.34" r="0.7">
          <stop offset="0" stop-color="#FF9C84"/>
          <stop offset="0.35" stop-color="#E0402F"/>
          <stop offset="1" stop-color="#A51F17"/>
        </radialGradient>
        <linearGradient id="s8-wordgrad" gradientUnits="userSpaceOnUse" x1="140" y1="0" x2="1198" y2="0">
          <stop offset="0" stop-color="#E2392D"/>
          <stop offset="0.47" stop-color="#E9862A"/>
          <stop offset="0.6" stop-color="#E8842A"/>
          <stop offset="1" stop-color="#DC382D"/>
        </linearGradient>
        <clipPath id="s8-clip"><rect id="s8-wordclip" x="120" y="100" width="0" height="260"/></clipPath>
      </defs>
      <g id="s8-lift">
      <g id="s8-logo" transform="translate({n(LOGO_X)} {n(LOGO_Y)}) scale({LOGO_S})">
        <path id="s8-coil" class="d" pathLength="1" d="{logo_coil_path()}" fill="none" stroke="#6D6C74" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
        <g clip-path="url(#s8-clip)">
          <path id="s8-word" d="{LOGO_LETTERS}" fill="url(#s8-wordgrad)"/>
        </g>
        <line id="s8-lscan" x1="0" y1="118" x2="0" y2="336" stroke="{ACC}" stroke-width="4"/>
        <circle id="s8-ballr" cx="{BALL_R[0]}" cy="{BALL_R[1]}" r="{BALL_RAD}" fill="url(#s8-ball)"/>
        <circle id="s8-balll" cx="{BALL_L[0]}" cy="{BALL_L[1]}" r="{BALL_RAD}" fill="url(#s8-ball)"/>
      </g>
      </g>
    </svg>
    <div id="s8-slogan" class="title cta1"></div>"""
    css = f"""
    #root .cta1 {{ left: 0; width: {W}px; top: {st_}px; text-align: center; font-size: {ss_}px; line-height: 1.18; }}
    #root #s8-lscan, #root #s8-ballr, #root #s8-balll {{ opacity: 0; }}"""
    js = f"""
      const slogan = words($("#s8-slogan"), txt("s8-slogan", "{P8["text"]}"));
      const lift = $("#s8-lift");
      tl.set(lift, {{ y: {n(lift)} }}, 0);
      // 1. le trajet du drone : la bille de départ, puis le serpentin se trace (bruit de drone)
      tl.fromTo($("#s8-balll"), {{ opacity: 0, scale: 0, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: "back.out(1.8)" }}, 0.05);
      draw(0.2, $("#s8-coil"), 2.1, "power1.inOut");
      tl.fromTo($("#s8-ballr"), {{ opacity: 0, scale: 0, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.6)" }}, 2.25);
      // 2. le serpentin tracé, le nom apparaît (balayage), au centre de l'écran
      tl.fromTo($("#s8-lscan"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.1 }}, 2.4);
      tl.fromTo($("#s8-lscan"), {{ x: 120 }}, {{ x: 1230, duration: 0.85, ease: "power1.inOut" }}, 2.4);
      tl.fromTo($("#s8-wordclip"), {{ attr: {{ width: 0 }} }}, {{ attr: {{ width: 1110 }}, duration: 0.85, ease: "power1.inOut" }}, 2.4);
      tl.to($("#s8-lscan"), {{ opacity: 0, duration: 0.15 }}, 3.2);
      // 3. le logo remonte en douceur ; le slogan s'installe dessous
      tl.to(lift, {{ y: 0, duration: 0.85, ease: "power2.inOut" }}, 3.6);
      blurIn(4.25, slogan, 0.16, 0.07);
      // 4. fin : logo et slogan restent affichés jusqu'à la dernière image
      tl.set({{}}, {{}}, {n(S8_DUR)});"""
    write_scene(
        "s8",
        "Scène 8 — Logo et slogan",
        [
            svar("s8-slogan", "Scène 8 — slogan (| = retour ligne, *mots* = orange)", P8["text"]),
        ],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# index.html
# --------------------------------------------------------------------------
SCENES = [("s0", 0, 3.6), ("s1", 3.6, 7.2), ("s2", 10.8, 6.6), ("s3", 17.4, 6.6), ("s4", 24.0, 7.2), ("s5", 31.2, 16.2),
          ("s6", 47.4, 8.4), ("s7", 55.8, S7_DUR), ("s8", 66.0, S8_DUR)]
TOTAL = 74.4
T_ = {sid: t for sid, t, _ in SCENES}

# (id, fichier, instant dans le film, volume) : le pic mesuré du fichier tombe une image après l'événement
SFX = [
    *[(f"sfx-pk{i}", "pop.mp3", T_["s2"] + 0.95 + i * 0.4, 0.12) for i in range(6)],
    ("sfx-cam", "whoosh-low.mp3", T_["s2"] + 5.6, 0.22),
    ("sfx-drone", "whoosh-short.mp3", T_["s3"] + 0.72, 0.5),
    ("sfx-scan", "whoosh-cinematic.mp3", T_["s3"] + 3.95, 0.3),
    ("sfx-zoom", "whoosh-high.mp3", T_["s3"] + 6.55, 0.45),
    ("sfx-tick1", "key-press.mp3", T_["s4"] + 1.4, 0.5),
    ("sfx-tick2", "key-press.mp3", T_["s4"] + 2.15, 0.45),
    ("sfx-tick3", "key-press.mp3", T_["s4"] + 3.9, 0.5),
    ("sfx-carry", "whoosh-low.mp3", T_["s4"] + 6.8, 0.35),
    ("sfx-box1", "key-press.mp3", T_["s5"] + 1.5, 0.3),
    ("sfx-box2", "key-press.mp3", T_["s5"] + 5.72, 0.3),
    ("sfx-plan", "pop.mp3", T_["s5"] + 3.55, 0.25),
    ("sfx-page2", "whoosh-high.mp3", T_["s5"] + 8.2, 0.18),
    ("sfx-page3", "whoosh-high.mp3", T_["s5"] + 11.75, 0.18),
    ("sfx-stamp", "pop.mp3", T_["s5"] + 12.88, 0.45),
    *[(f"sfx-check{i + 1}", f"validation-{i + 1}.wav", T_["s5"] + t + 0.1, 0.2) for i, t in enumerate(S5_CHECKS)],
    ("sfx-link", "click-soft.mp3", T_["s5"] + 15.25, 0.75),
    ("sfx-open", "whoosh-short.mp3", T_["s5"] + 15.7, 0.3),
    ("sfx-row1", "click-soft.mp3", T_["s6"] + 2.25, 0.75),
    ("sfx-row2", "click-soft.mp3", T_["s6"] + 4.85, 0.75),
    ("sfx-type1", "typing-18.wav", T_["s7"] + S7_Q[0][1], 0.75),
    ("sfx-enter1", "key-enter.wav", T_["s7"] + 2.7, 0.8),
    ("sfx-res1", "whoosh-short.mp3", T_["s7"] + 3.2, 0.22),
    ("sfx-del", "key-enter.wav", T_["s7"] + 5.8, 0.6),
    ("sfx-type2", "typing-12.wav", T_["s7"] + S7_Q[1][1], 0.75),
    ("sfx-enter2", "key-enter.wav", T_["s7"] + 7.3, 0.8),
    ("sfx-res2", "whoosh-short.mp3", T_["s7"] + 7.5, 0.22),
    ("sfx-buzz", "drone-buzz.wav", T_["s8"] + 0.05, 0.22),
    ("sfx-logo", "impact-bass-1.mp3", T_["s8"] + 2.45, 0.22),
    ("sfx-lift", "whoosh-low.mp3", T_["s8"] + 3.75, 0.18),
]
# musique encore plus basse pendant la frappe au clavier (scène 7)
DUCK_EXTRA = [(T_["s7"] + 0.7, T_["s7"] + 3.05, 0.3), (T_["s7"] + 5.5, T_["s7"] + 7.65, 0.3)]


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
    # voix off (tools/voiceover.py) : une piste par phrase, et la musique s'efface sous la voix
    vo_path = os.path.join(ROOT, "assets", "audio", "vo", "vo.json")
    vo = json.load(open(vo_path, encoding="utf-8")) if os.path.exists(vo_path) else []
    duck, base = 0.15, 0.5  # musique de fond : -6 dB partout, -16,5 dB sous la voix (la voix reste claire)
    segs = []
    for v in vo:
        s0, s1 = v["start"] - 0.3, v["start"] + v["dur"] + 0.45
        if segs and s0 <= segs[-1][1] + 0.5:  # pas de remontée de la musique dans les petits silences
            segs[-1][1] = s1
        else:
            segs.append([s0, s1, duck])
    segs = sorted(segs + [list(d) for d in DUCK_EXTRA])
    pts_ = [{"t": 0, "v": base}]
    for s0, s1, lv in segs:
        pts_ += [{"t": round(max(s0, 0), 3), "v": base}, {"t": round(s0 + 0.3, 3), "v": lv},
                 {"t": round(s1 - 0.45, 3), "v": lv}, {"t": round(min(s1, TOTAL), 3), "v": base}]
    lane = {"version": 1, "lanes": [{"target": "volume", "points": pts_}]}
    music_attr = f' data-automation="{attr_json(lane)}"'
    audio = [
        f'      <audio id="music" class="clip" src="assets/audio/music.wav" data-start="0" data-duration="{n(TOTAL)}" data-track-index="2" data-volume="1"{music_attr}></audio>'
    ]
    for v in vo:
        audio.append(
            f'      <audio id="vo-{v["id"]}" class="clip" src="{v["file"]}" data-start="{n(v["start"])}" data-duration="{n(v["dur"] - 0.005)}" data-track-index="6" data-volume="1"></audio>'
        )
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
    <meta name="viewport" content="width={W}, height={H}" />
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
        width: {W}px;
        height: {H}px;
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
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(doc)
    print("wrote index.html")


if __name__ == "__main__":
    offsets = {}
    p = os.path.join(ROOT, "assets", "audio", "sfx", "peaks.json")
    if os.path.exists(p):
        offsets = json.load(open(p))
    if not WIDE:  # projet autonome de la déclinaison : mêmes médias, mêmes polices
        os.makedirs(os.path.join(OUT, "compositions"), exist_ok=True)
        shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(OUT, "assets"), dirs_exist_ok=True)
        shutil.copy(os.path.join(ROOT, "hyperframes.json"), OUT)
        pkg = json.load(open(os.path.join(ROOT, "package.json")))
        pkg["name"] = f"video-thermographie-{FMT}"
        json.dump(pkg, open(os.path.join(OUT, "package.json"), "w"), indent=2)
        json.dump({"id": f"video-thermographie-{FMT}", "name": f"video-thermographie-{FMT}"},
                  open(os.path.join(OUT, "meta.json"), "w"), indent=2)
    build_s0()
    build_s1()
    build_s2()
    build_s3()
    build_s4()
    build_s5()
    build_s6()
    build_s7()
    build_s8()
    build_index(offsets)
