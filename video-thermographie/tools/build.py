#!/usr/bin/env python3
"""Génère index.html et compositions/s1..s6.html.

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
        s2_head=(108, 330, 50), s2_chart=(0.83, -90.8, 395.9), s2_icons=(1.0, -1030, 820),
        s2_fs=dict(tick=34, label=38, ilabel=32),
        s3_cam=(-35, 832, -245.9, 1000), s3_hud=(556, 597), s3_title=(108, 330, 58),
        handoff=(220, 641, 640),
        s4_settle=(60, 560, 960), s4_title=(108, 330, 56), s4_title_text="Chaque anomalie est|détectée et localisée.",
        s4_rows=(1380, 1490, 1600), s4_order=(2, 0, 1), s4_fs=(34, 28), s4_band_col=0.8,
        s4_lab=(("r", 1020, 480), ("l", 300, 520), ("l", 108, 560)),
        s5_title=(108, 300, 64), s5_doc=(0.8, 124, 423.2), s5_chart=(0.8, -556, 975.6), s5_stamp=36, s5_pfs=35,
        s5_fs=dict(item=35, head=36, tick=36, label=38, cat=36, catlh=44),
    ),
    "1x1": dict(
        s1_box=(0.98, -817.3, 87.6), s1_title=(108, 120, 56), s1_sun=(1640, 230),
        s2_head=(108, 100, 40), s2_chart=(0.8, -68, 144), s2_icons=(0.72, -317.6, -238.4),
        s2_fs=dict(tick=35, label=38, ilabel=40),
        s3_cam=(-35, 832, 87.4, 1000), s3_hud=(556, 236), s3_title=(108, 108, 52),
        handoff=(270, 380, 540),
        s4_settle=(204, 170, 672), s4_title=(108, 90, 40), s4_title_text="Chaque anomalie est détectée et localisée.",
        s4_rows=(750, 825, 900), s4_order=(2, 0, 1), s4_fs=(30, 28), s4_band_col=0.8,
        s4_lab=(("r", 1000, 420), ("l", 380, 480), ("l", 108, 560)),
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
    (1, 4): [("module",), ("spot", 0, 0), ("cell", 0, 2), ("spot", 0, 4)],  # module zoomé : comme sur la photo réelle (S4)
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
# Photo thermique réelle (assets/images/thermo-panneau.jpg, 640 x 512, fournie par Fly Scan'Air). Son module central
# (x 133–512, y 160–386 dans la photo) est calé sur le panneau zoomé ; les défauts sont relevés sur la photo.
PHOTO = "assets/images/thermo-panneau.jpg"
PHOTO_W, PHOTO_H = 640, 512
PH_K = 0.86 * S4PW / (512 - 133)
PH_C = ((133 + 512) / 2, (160 + 386) / 2)


def photo_xy(px, py):
    """Pixel de la photo -> monde S4."""
    return S4X + S4PW / 2 + (px - PH_C[0]) * PH_K, S4Y + S4PH / 2 + (py - PH_C[1]) * PH_K


def photo_box(px0, py0, px1, py1):
    (x0, y0), (x1, y1) = photo_xy(px0, py0), photo_xy(px1, py1)
    return (x0, y0, x1 - x0, y1 - y0)


def photo_svg(prefix):
    """La photo, recadrée sur le panneau zoomé (mêmes coordonnées que le panneau dessiné : raccords S3 -> S4 -> S5)."""
    x, y = photo_xy(0, 0)
    return (f'<clipPath id="{prefix}-pclip"><rect x="{n(S4X)}" y="{n(S4Y)}" width="{n(S4PW)}" height="{n(S4PH)}"/></clipPath>'
            f'<g id="{prefix}-photo"><image href="{PHOTO}" x="{n(x)}" y="{n(y)}" width="{n(PHOTO_W * PH_K)}" height="{n(PHOTO_H * PH_K)}" '
            f'preserveAspectRatio="none" clip-path="url(#{prefix}-pclip)"/>'
            f'<rect x="{n(S4X)}" y="{n(S4Y)}" width="{n(S4PW)}" height="{n(S4PH)}" fill="none" stroke="{INK}" stroke-width="2"/></g>')


# points d'ancrage des lignes de rappel, relevés sur la photo : points chauds, cellules échauffées, microfissures
PHOTO_ANCH = [(201, 187), (177, 328), (400, 246)]
HERO_ANCH = [photo_xy(*q) for q in PHOTO_ANCH]  # monde S4
S4_LABELS = [  # texte principal | précision (défauts visibles sur la photo, vocabulaire de la note technique)
    "Points chauds|échauffement localisé",
    "Cellules échauffées|en bordure de module",
    "Microfissures|réseau dans les cellules",
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


BOX1 = photo_box(134, 154, 210, 204)  # défaut #1 : les points chauds (photo)
BOX2 = photo_box(232, 202, 488, 352)  # défaut #2 : le réseau de microfissures (photo)


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
P7 = {  # carton final : logo + slogan (temps A), puis site web + LinkedIn (temps B)
    "16x9": dict(s=0.72, y=196, slogan=(552, 56), msg=(722, 38), top=(0.55, -37.8), web=None, inb=None,
                 contacts=(924, 32), url=28, capw=34, capi=34, capn=40, inurl="linkedin.com/company/fly-scan-air",
                 slogan_text="Inspections techniques aériennes,|révélez *l’invisible*."),
    "9x16": dict(s=0.7, y=600, slogan=(970, 60), msg=(1230, 38), top=(0.6, -210), web=(1.15, -242, 88.5),
                 inb=(1.0, -880, 700), contacts=(1520, 34), url=28, capw=34, capi=34, capn=40, inurl="linkedin.com/company/fly-scan-air",
                 slogan_text="Inspections techniques|aériennes,|révélez *l’invisible*."),
    "1x1": dict(s=0.6, y=200, slogan=(495, 50), msg=(705, 34), top=(0.56, -62), web=(0.72, -156, 54.8),
                inb=(0.8, -296, 24), contacts=(760, 30), url=40, capw=40, capi=36, capn=36, inurl="linkedin.com/company/|fly-scan-air",
                slogan_text="Inspections techniques|aériennes,|révélez *l’invisible*."),
}[FMT]
P6 = {  # plateforme en ligne
    "16x9": dict(title=(140, 330, 52), text="Suivez vos installations|sur notre *plateforme*|en ligne.",
                 tag=(140, 545), win=(0.9, 826, 243), ui=32),
    "9x16": dict(title=(108, 360, 60), text="Suivez vos installations|sur notre *plateforme*|en ligne.",
                 tag=(108, 600), win=(0.88, 73.6, 700), ui=32),
    "1x1": dict(title=(108, 96, 44), text="Suivez vos installations sur|notre *plateforme* en ligne.",
                tag=(108, 214), win=(0.78, 126.5, 300), ui=36),
}[FMT]
LOGO_S = P7["s"]
LOGO_X = (W - 1270 * LOGO_S) / 2
LOGO_Y = P7["y"]
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


# Icônes Phosphor (phosphoricons.com, licence MIT, assets/images/LICENSE-phosphor.txt), graisse « regular »,
# repère 256 x 256 ; « fire » et « shield-check », découpées en sous-tracés pour animer l'intérieur et la coche.
PH_FIRE_BG = "M208,144a80,80,0,0,1-160,0c0-30.57,14.42-58.26,31-80l33,32,26.27-72C159.86,41.92,208,88.15,208,144Z"  # duotone
PH_FIRE_CURL = "M183.89,153.34a57.6,57.6,0,0,1-46.56,46.55A8.75,8.75,0,0,1,136,200a8,8,0,0,1-1.32-15.89c16.57-2.79,30.63-16.85,33.44-33.45a8,8,0,0,1,15.78,2.68Z"
PH_FIRE = ("M216,144a88,88,0,0,1-176,0c0-27.92,11-56.47,32.66-84.85a8,8,0,0,1,11.93-.89l24.12,23.41,22-60.41a8,8,0,0,1,12.63-3.41"
           "C165.21,36,216,84.55,216,144Zm-16,0c0-46.09-35.79-85.92-58.21-106.33L119.52,98.74a8,8,0,0,1-13.09,3L80.06,76.16"
           "C64.09,99.21,56,122,56,144a72,72,0,0,0,144,0Z")
PH_SHIELD_BG = "M216,56v56c0,96-88,120-88,120S40,208,40,112V56a8,8,0,0,1,8-8H208A8,8,0,0,1,216,56Z"  # duotone
PH_SHIELD = ("M208,40H48A16,16,0,0,0,32,56v56c0,52.72,25.52,84.67,46.93,102.19,23.06,18.86,46,25.26,47,25.53a8,8,0,0,0,4.2,0"
             "c1-.27,23.91-6.67,47-25.53C198.48,196.67,224,164.72,224,112V56A16,16,0,0,0,208,40Zm0,72c0,37.07-13.66,67.16-40.6,89.42"
             "A129.3,129.3,0,0,1,128,223.62a128.25,128.25,0,0,1-38.92-21.81C61.82,179.51,48,149.3,48,112l0-56,160,0Z")
PH_CHECK = "M82.34,141.66a8,8,0,0,1,11.32-11.32L112,148.69l50.34-50.35a8,8,0,0,1,11.32,11.32l-56,56a8,8,0,0,1-11.32,0Z"
PH_S = 0.9  # 256 -> 230 px


def s2_icons(FX, SX, IY):
    """Incendie (flamme Phosphor) et assurance (bouclier Phosphor) : tracé orange, intérieur transparent."""
    fx, fy = FX - 128 * PH_S, IY - 125 * PH_S
    sx, sy = SX - 128 * PH_S, IY - 140 * PH_S
    return (
        f'<g transform="translate({n(fx)} {n(fy)}) scale({PH_S})" stroke="none">'
        '<clipPath id="s2-fclip"><rect id="s2-fclipr" x="0" y="256" width="256" height="0"/></clipPath>'
        '<g clip-path="url(#s2-fclip)">'
        f'<path id="s2-flame" d="{PH_FIRE}" fill="{ACC}"/>'
        f'<path id="s2-flamec" d="{PH_FIRE_CURL}" fill="{ACC}"/></g></g>'
        f'<g transform="translate({n(sx)} {n(sy)}) scale({PH_S})" stroke="none"><g id="s2-shieldg">'
        f'<path id="s2-shield" d="{PH_SHIELD}" fill="{ACC}"/>'
        '<clipPath id="s2-cclip"><rect id="s2-cclipr" x="78" y="90" width="0" height="84"/></clipPath>'
        f'<path id="s2-check" d="{PH_CHECK}" fill="{ACC}" clip-path="url(#s2-cclip)"/></g></g>'
    )


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
        {s2_icons(FX, SX, IY)}
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
    g0 = dict(x1=120, x2=1800, y=880)  # position de départ de l'axe = ligne de sol de S1
    if L:
        # la ligne de sol de S1 (à l'écran) exprimée dans la boîte du graphique
        s1s, s1tx, s1ty = L["s1_box"]
        c_s, c_x, c_y = L["s2_chart"]
        gx1, gx2 = s1_ground()
        g0 = dict(
            x1=(s1s * gx1 + s1tx - c_x) / c_s,
            x2=(s1s * gx2 + s1tx - c_x) / c_s,
            y=(s1s * 880 + s1ty - c_y) / c_s,
        )
        chart = f"""    <svg class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">
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
        <line id="s2-x" x1="{n(g0["x1"])}" y1="{n(g0["y"])}" x2="{n(g0["x2"])}" y2="{n(g0["y"])}"/>
        <polyline id="s2-xa" class="d" pathLength="1" points="{ax_x1 - 12},{S2_Y0 - 9} {ax_x1},{S2_Y0} {ax_x1 - 12},{S2_Y0 + 9}"/>
        <line id="s2-y" class="d" pathLength="1" x1="{S2_X0}" y1="{S2_Y0}" x2="{S2_X0}" y2="{ax_y1}"/>
        <polyline id="s2-ya" class="d" pathLength="1" points="{S2_X0 - 9},{ax_y1 + 12} {S2_X0},{ax_y1} {S2_X0 + 9},{ax_y1 + 12}"/>
        <path id="s2-saine" class="d" pathLength="1" d="{p_saine}" stroke="#A1A1AA" stroke-width="4"/>
        <path id="s2-defaut" class="d" pathLength="1" d="{p_defaut}" stroke="{ACC}" stroke-width="4.5"/>
      </g>
      <circle id="s2-end0" cx="{n(gs[0])}" cy="{n(gs[1])}" r="9" fill="#FFFFFF" stroke="#A1A1AA" stroke-width="3.5"/>
      <circle id="s2-end1" cx="{n(gd[0])}" cy="{n(gd[1])}" r="9" fill="#FFFFFF" stroke="{ACC}" stroke-width="3.5"/>
    </svg>
    <div id="s2-lab-y" class="label" style="left: 200px; top: 266px">Rendement (%)</div>
    <div id="s2-lab-x" class="label" style="left: 820px; top: 918px; width: 300px; text-align: right">Temps (mois)</div>
    <div id="s2-lab-s0" class="label" style="left: {n(xend + 22)}px; top: {n(gs[1] - 24)}px">Saine</div>
    <div id="s2-lab-s1" class="label" style="left: {n(xend + 22)}px; top: {n(gd[1] - 24)}px; color: #111111">Avec défauts</div>"""
        icons = f"""    <svg class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">
      <g fill="none" stroke="{INK}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        {s2_icons(FX, SX, IY)}
      </g>
    </svg>
    <div id="s2-lab-f" class="label ilab" style="left: {FX - 130}px; top: 735px; width: 260px; text-align: center">Incendie</div>
    <div id="s2-lab-s" class="label ilab" style="left: {SX - 140}px; top: 735px; width: 280px; text-align: center">Assurance</div>"""
        hl, ht, hs = L["s2_head"]
        body = (
            box(chart, L["s2_chart"]) + "\n" + box(icons, L["s2_icons"]) + f"""
    <div id="s2-head" class="head" style="left: {hl}px; top: {ht}px; font-size: {hs}px">
      <div class="hrow"><i class="sq"></i><span id="s2-t1" class="term">Perte de rendement</span></div>
      <div class="hrow"><i class="sq"></i><span id="s2-t2" class="term">Risque incendie</span></div>
      <div class="hrow"><i class="sq"></i><span id="s2-t3" class="term">Défauts invisibles</span></div>
    </div>"""
        )
    css = """
    #root .head { position: absolute; left: 140px; top: 150px; font-weight: 700; font-size: 46px; letter-spacing: -0.01em; white-space: nowrap; display: flex; align-items: center; }
    #root .term { color: #D4D4D8; }
    #root .sq { display: inline-block; width: 14px; height: 14px; background: #FF5700; margin: 0 28px; }
    #root .tick text { font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 28px; fill: #6B6B70; }
    #root #s2-end0, #root #s2-end1, #root #s2-grid, #root #s2-yt, #root #s2-xt { opacity: 0; }"""
    if L:
        fs = L["s2_fs"]
        css += f"""
    #root .head {{ flex-direction: column; align-items: flex-start; }}
    #root .hrow {{ display: flex; align-items: center; line-height: 1.45; }}
    #root .hrow .sq {{ margin: 0 22px 0 0; }}
    #root .tick text {{ font-size: {fs["tick"]}px; }}
    #root .label {{ font-size: {fs["label"]}px; }}
    #root .label.ilab {{ font-size: {fs["ilabel"]}px; }}"""
    js = """
      $("#s2-t1").textContent = txt("s2-t1", "Perte de rendement");
      $("#s2-t2").textContent = txt("s2-t2", "Risque incendie");
      $("#s2-t3").textContent = txt("s2-t3", "Défauts invisibles");
      const head = $("#s2-head");
      // 1. la ligne de sol devient l'axe des temps, l'axe du rendement se dessine
      tl.fromTo($("#s2-x"), { attr: { x1: __GX1__, x2: __GX2__, y1: __GY__, y2: __GY__ } }, { attr: { x1: __X0__, x2: __AX1__, y1: __Y0__, y2: __Y0__ }, duration: 0.7, ease: "power2.inOut" }, 0);
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
      tl.fromTo($("#s2-fclipr"), { attr: { y: 256, height: 0 } }, { attr: { y: 0, height: 256 }, duration: 0.7, ease: "power2.out" }, 2.6);
      tl.fromTo($("#s2-flamec"), { opacity: 0 }, { opacity: 1, duration: 0.3 }, 3.1);
      blurIn(3.1, $("#s2-lab-f"), 0.2);
      tl.fromTo($("#s2-t2"), { color: "#D4D4D8" }, { color: "#111111", duration: 0.3 }, 3.0);
      // 4. icône assurance
      tl.fromTo($("#s2-shieldg"), { opacity: 0, scale: 0.8, transformOrigin: "50% 50%" }, { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.6)" }, 3.4);
      tl.fromTo($("#s2-cclipr"), { attr: { width: 0 } }, { attr: { width: 100 }, duration: 0.35, ease: "power2.out" }, 4.05);
      blurIn(3.9, $("#s2-lab-s"), 0.2);
      tl.fromTo($("#s2-t3"), { color: "#D4D4D8" }, { color: "#111111", duration: 0.3 }, 3.85);
      // 5. sortie : flou + fondu
      blurOut(6.05, [head, ...$$(".label")], 0.2, 0.02);
      blurOut(6.1, __SVGS__, 0.25, 0, 8);"""
    js = (js.replace("__GX1__", n(g0["x1"])).replace("__GX2__", n(g0["x2"])).replace("__GY__", n(g0["y"]))
          .replace("__SVGS__", '$$("svg.world")' if L else 'R.querySelector("svg.world")')
          .replace("__X0__", str(S2_X0)).replace("__AX1__", str(ax_x1)).replace("__Y0__", str(S2_Y0))
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


S3_DUR = 19.2  # survol : drone, caméra, puis deux repères pédagogiques (note technique Fly Scan'Air, § 2.1 et 3.2)
S3_FACTS = [  # (début, fin, chiffre, légende) — en temps local de la scène 3, calés sur les phrases 11 et 12 de la voix
    (6.55, 12.3, "≈ 600 W/m²", "d’ensoleillement suffisent<br />pour révéler chaque défaut."),
    (12.45, 18.45, "−0,5 % par degré", "de rendement perdu :<br />+10 °C, c’est déjà −5 %."),
]


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
    if L:  # caméra : cadre vertical / carré qui suit le drone
        cx0, cx1, cy, cvw = L["s3_cam"]
        S3_VB0 = (cx0, cy, cvw, cvw * H / W)
        S3_VB1 = (cx1, cy, cvw, cvw * H / W)
    else:
        S3_VB0 = (0, 0, W, H)
    body = f"""    <svg id="s3-svg" class="world zoom" data-dash="{dash_k(S3_VB0)}" viewBox="{vb(S3_VB0)}" width="{W}" height="{H}"{CANVAS}>
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
      <polyline id="s3-leader" class="d" pathLength="1" points="{HOVER_X},{DRONE_Y - 34} {HOVER_X},331 470,331" fill="none" stroke="{INK}" stroke-width="1.5"/>
      <circle id="s3-leaddot" cx="{HOVER_X}" cy="{DRONE_Y - 34}" r="5" fill="{INK}"/>
    </svg>
    <div id="s3-hud">
      <div id="s3-tag" class="tag">Caméra infrarouge</div>
      <div id="s3-scale" class="scale"><span>Froid</span><i></i><span>Chaud</span></div>
    </div>
    <div id="s3-title" class="title" style="{tstyle(L and L["s3_title"], "left: 140px; top: 120px")}">Le scan infrarouge révèle<br />chaque échauffement.</div>
    {"".join(f'<div id="s3-f{i}" class="fact" style="{tstyle(L and L["s3_title"], "left: 140px; top: 120px; font-size: 64px")}"><div class="fk">Le saviez-vous ?</div><div class="ff">{fig}</div><div class="fc">{cap}</div></div>' for i, (_, _, fig, cap) in enumerate(S3_FACTS))}"""
    css = """
    #root #s3-hud { position: absolute; left: 480px; top: 306px; display: flex; align-items: center; gap: 36px; }
    #root .tag { font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 30px; line-height: 1; padding: 10px 16px; background: #FFFFFF; border: 1.5px solid #111111; color: #111111; white-space: nowrap; }
    #root .scale { display: flex; align-items: center; gap: 14px; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: 30px; color: #6B6B70; }
    #root .scale i { display: block; width: 200px; height: 12px; background: linear-gradient(90deg, #E4E4E7 0%, #FFD2BC 55%, #FF5700 100%); }
    #root #s3-tag, #root #s3-scale, #root #s3-leaddot, #root #s3-scan, #root .s3-ring { opacity: 0; }
    #root .s3-pfill, #root .s3-cells { opacity: 0; }
    #root .fact { position: absolute; font-family: "Comfortaa", sans-serif; white-space: nowrap; }
    #root .fact .fk { font-weight: 700; font-size: 28px; line-height: 1; color: #FF5700; margin-bottom: 0.25em; }
    #root .fact .ff { font-weight: 700; font-size: 1em; line-height: 1.12; letter-spacing: -0.01em; color: #111111; }
    #root .fact .fc { font-weight: 600; font-size: 0.56em; line-height: 1.3; color: #111111; margin-top: 0.12em; }
    #root .fact > div { opacity: 0; }"""
    if L:
        css += f"""
    #root #s3-hud {{ left: {L["s3_hud"][0]}px; top: {L["s3_hud"][1]}px; flex-direction: column; align-items: flex-start; gap: 12px; }}"""
    js = f"""
      const title = words($("#s3-title"), txt("s3-title", "Le scan infrarouge révèle|chaque *échauffement*."));
      const HOVER = {HOVER_X}, END = {SCAN_END_X}, Y = {DRONE_Y};
      const T0 = 3.2, TD = 14.2; // survol lent : le temps d'expliquer
      // 1. le champ de panneaux se dessine (vue de dessus)
      draw(0.1, $$(".s3-pline"), 0.5, "power2.inOut", 0.03);
      fadeIn(0.3, $$(".s3-pfill"), 0.4, 0.03);
      fadeIn(0.6, $$(".s3-cells"), 0.5, 0.02);
      solid(1.6, $$(".s3-pline"));
      // 2. le drone entre ; les rotors tournent en continu
      tl.fromTo($("#s3-drone"), {{ x: -260, y: Y }}, {{ x: HOVER, y: Y, duration: 0.85, ease: "expo.out" }}, 0.7);
      tl.fromTo($$(".s3-blade"), {{ rotation: 0, transformOrigin: "50% 50%" }}, {{ rotation: 360 * 35, duration: {S3_DUR}, ease: "none" }}, 0);
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
      blurOut(6.35, title, 0.16, 0.02);
      // 4 bis. « Le saviez-vous ? » : deux repères de la note technique, pendant que la voix les explique
      {"".join(f'blurIn({a}, $$("#s3-f{i} > div"), 0.2, 0.12); blurOut({b}, $$("#s3-f{i} > div"), 0.16, 0.03);' + chr(10) + "      " for i, (a, b, _, _) in enumerate(S3_FACTS))}
      tl.to($("#s3-svg"), {{ attr: {{ viewBox: "{vb(S3_END_VB)}" }}, duration: 0.62, ease: "power3.in" }}, {n(S3_DUR - 0.62)});"""
    if L:
        marker = '      tl.fromTo($("#s3-cliprect"),'
        cam = (f'      tl.fromTo($("#s3-svg"), {{ attr: {{ viewBox: "{vb(S3_VB0)}" }} }}, '
               f'{{ attr: {{ viewBox: "{vb(S3_VB1)}" }}, duration: TD, ease: "power1.inOut" }}, T0);\n')
        js = js.replace(marker, cam + marker, 1)
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
      {photo_svg("s4")}
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
      tl.fromTo($("#s4-photo"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.6, ease: "power1.inOut" }}, 0.3);  // la vraie image thermique
      fadeOut(0.9, $("#s4-panel"), 0.1);  // le panneau dessiné (et ses halos) s'efface sous la photo
      // 2. titre : du gris à l'encre, mot à mot
      tl.fromTo(title, {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2 }}, 0.75);
      tl.fromTo(title, {{ color: "#D4D4D8" }}, {{ color: "#111111", duration: 0.25, stagger: 0.08 }}, 0.95);
      // 3. chaque défaut est désigné : point sur l'anomalie, ligne de rappel, étiquette (calé sur la voix off)
      [[0.2, 0], [1.05, 1], [2.55, 2]].forEach(([t, i]) => {{  // « Points chauds », « cellules échauffées », « microfissures »
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


# plateforme : position de l'icône « nouveau rapport » dans la fenêtre (coordonnées fenêtre)
P6_DOC = (661, 185, 34)  # centre x, centre y, hauteur


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
    dict(num="Défaut #1", cat=4, cat_fill="#FF8A4C", cat_ink="#111111", statut="À traiter", type="Points chauds",
         dt="11,2 °C", mx="58 °C", origine="Cellule dégradée", action="Contrôle électrique", note="Échauffement localisé"),
    dict(num="Défaut #2", cat=3, cat_fill="#FFBE9A", cat_ink="#111111", statut="À surveiller", type="Microfissures",
         dt="4,6 °C", mx="51 °C", origine="Contrainte mécanique", action="Suivi du module", note="Réseau de fissures"),
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
        {photo_svg("s5")}
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
        <g id="s5-mlogo">{mini_logo(520 - 1270 * 0.33 / 2, 742, 0.33, "s5m")}</g>
      </svg>
      <svg class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">{stamp}</svg>
      <div id="s5-ct" class="covt" style="left: 260px; top: 200px">Rapport d’inspection<br />thermique</div>
      <div id="s5-cs" class="pgt grey" style="left: 260px; top: 340px">Centrale photovoltaïque</div>
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
      <defs><clipPath id="s5-clip"><rect x="{-4000 if L else 0}" y="{-4000 if L else 0}" width="{SW + 8000 if L else SW}" height="{S5_AY + 4000 if L else S5_AY}"/></clipPath></defs>
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
      <g clip-path="url(#s5-clip)">{"".join(gbars)}</g>
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
    body = (box(doc_part, L["s5_doc"] if L else None) + "\n" + box(chart_part, L["s5_chart"] if L else None) + "\n" + titles
            + "\n    " + cards_html)
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
    #root #s5-grid, #root #s5-yt, #root #s5-stamp, #root .s5-foot, #root #s5-hotc, #root #s5-mlogo, #root .s5-sw, #root #s5-badge1, #root #s5-badge2, #root #s5-bbox, #root #s5-plan-lab, #root #s5-plan-cap, #root #s5-pticks, #root .s5-pm, #root #s5-ph {{ opacity: 0; }}"""
    if L:
        fs = L["s5_fs"]
        css += f"""
    #root .item {{ font-size: {fs["item"]}px; }}
    #root .tick text {{ font-size: {fs["tick"]}px; }}
    #root .label {{ font-size: {fs["label"]}px; }}
    #root .cat {{ font-size: {fs["cat"]}px; line-height: {fs["catlh"]}px; }}"""
    # le rapport rejoint la ligne « Nouveau rapport » de la plateforme (raccord S5 -> S6)
    ws, wtx, wty = P6["win"]
    icx, icy, ich = ws * P6_DOC[0] + wtx, ws * P6_DOC[1] + wty, ws * P6_DOC[2]
    bs, btx, bty = L["s5_doc"] if L else (1, 0, 0)
    dcx, dcy = dx + dw / 2, dy + dh / 2
    carry = dict(x=(icx - btx) / bs - dcx, y=(icy - bty) / bs - dcy, scale=ich / (dh * bs))
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
      [13.6, 14.2, 14.8, 15.4].forEach((t, i) => draw(t, $("#s5-k" + i), 0.22, "power2.out"));
      // 4. sortie : le rapport file dans la plateforme
      blurOut(16.55, [...t3, $("#s5-i0"), $("#s5-i1"), $("#s5-i2"), $("#s5-i3")], 0.2, 0.015);
      blurOut(16.6, [$("#s5-check")], 0.2, 0);
      fadeOut(16.63, [$("#s5-ct"), $("#s5-cs"), $("#s5-stamp"), $("#s5-mlogo")], 0.1);
      tl.to($("#s5-docw"), { x: __CX__, y: __CY__, scale: __CS__, transformOrigin: "__OX__px __OY__px", duration: 0.48, ease: "power2.inOut" }, 16.65);"""
    js = (js.replace("__B2X__", n(BOX2[0])).replace("__B2Y__", n(BOX2[1])).replace("__B2W__", n(BOX2[2])).replace("__B2H__", n(BOX2[3])))
    js = (js.replace("__AY__", str(S5_AY)).replace("__CX__", n(carry["x"])).replace("__CY__", n(carry["y"]))
          .replace("__CS__", f'{carry["scale"]:.5f}').replace("__OX__", n(dcx)).replace("__OY__", n(dcy)))
    write_scene(
        "s5",
        "Scène 5 — Rapport d'inspection thermique : défauts, résultats, couverture conforme IEC TS 62446-3",
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
# S6 — Plateforme en ligne (en cours de développement : mention « Bientôt disponible »)
# --------------------------------------------------------------------------
LINKEDIN_PATH = (  # Font Awesome Free 6.5.2 « linkedin » (CC BY 4.0), viewBox 0 0 448 512
    "M416 32H31.9C14.3 32 0 46.5 0 64.3v383.4C0 465.5 14.3 480 31.9 480H416c17.6 0 32-14.5 32-32.3V64.3c0-17.8-14.4-32.3-32-32.3z"
    "M135.4 416H69V202.2h66.5V416zm-33.2-243c-21.3 0-38.5-17.3-38.5-38.5S80.9 96 102.2 96c21.2 0 38.5 17.3 38.5 38.5 0 21.3-17.2 38.5-38.5 38.5z"
    "m282.1 243h-66.4V312c0-24.8-.5-56.7-34.5-56.7-34.6 0-39.9 27-39.9 54.9V416h-66.4V202.2h63.7v29.2h.9c8.9-16.8 30.6-34.5 62.9-34.5 67.2 0 79.7 44.3 79.7 101.9V416z"
)


def build_s6():
    ws, wtx, wty = P6["win"]
    ui = P6["ui"]
    # plan thermique : 5 x 3 modules
    field, markers = [], []
    mx0, my0, mw, mh, mgx, mgy = 140, 168, 80, 56, 10, 14
    hot = {(1, 1): 0, (0, 3): 1, (2, 4): 2}
    for r in range(3):
        for c in range(5):
            x, y = mx0 + c * (mw + mgx), my0 + r * (mh + mgy)
            warm = (r, c) == (2, 1)
            field.append(
                f'<g class="s6-mod"><rect x="{x}" y="{y}" width="{mw}" height="{mh}" fill="{"#FFD9C6" if warm else th_fill(r, c)}" stroke="{INK}" stroke-width="1.5"/>'
                f'<path d="M{x + mw / 3:.1f} {y}V{y + mh}M{x + 2 * mw / 3:.1f} {y}V{y + mh}M{x} {y + mh / 2}H{x + mw}" stroke="{TH_CELL}" stroke-width="1"/></g>'
            )
            if (r, c) in hot:
                k = hot[(r, c)]
                markers.append((k, x + mw / 2, y + mh / 2))
    rings = "".join(f'<circle class="s6-ring" cx="{n(x)}" cy="{n(y)}" r="10" fill="none" stroke="{ACC}" stroke-width="2"/>' for _, x, y in markers)
    mks = "".join(f'<circle id="s6-mk{k}" class="s6-mk" cx="{n(x)}" cy="{n(y)}" r="10" fill="{ACC}"/>' for k, x, y in markers)
    rows = []
    for i, y in enumerate((150, 238, 326)):
        hl = i == 0
        icon = (f'<g class="{"s6-doc" if hl else "s6-doc2"}"><rect x="648" y="{y + 18}" width="26" height="34" rx="3" fill="#FFFFFF" stroke="{INK if hl else "#A1A1AA"}" stroke-width="2"/>'
                f'<path d="M653 {y + 28}h16M653 {y + 35}h16M653 {y + 42}h10" stroke="{INK if hl else "#A1A1AA"}" stroke-width="1.5"/></g>')
        rows.append(f'<rect class="d s6-row" pathLength="1" x="630" y="{y}" width="400" height="70" rx="10" fill="none" stroke="{INK if hl else "#C9CBD1"}" stroke-width="2"/>')
        rows.append(icon)
        if hl:
            rows.append(f'<text id="s6-new" class="ui" x="686" y="{y + 46}">Nouveau rapport</text>')
            rows.append(f'<circle id="s6-st0" cx="1030" cy="{y}" r="9" fill="{ACC}" stroke="#FFFFFF" stroke-width="3"/>')
        else:
            rows.append(f'<g class="s6-bars"><line x1="692" y1="{y + 28}" x2="900" y2="{y + 28}" stroke="#E4E4E7" stroke-width="9" stroke-linecap="round"/>'
                        f'<line x1="692" y1="{y + 47}" x2="830" y2="{y + 47}" stroke="#E4E4E7" stroke-width="9" stroke-linecap="round"/>'
                        f'<circle cx="1012" cy="{y + 35}" r="7" fill="#C9CBD1"/></g>')
    icons = (
        '<path class="d s6-ic" pathLength="1" d="M36 108h11v11h-11zM51 108h11v11h-11zM36 123h11v11h-11zM51 123h11v11h-11z"/>'
        '<path class="d s6-ic" pathLength="1" d="M38 186h16l6 6v24h-22zM43 199h12M43 206h12"/>'
        '<path class="d s6-ic" pathLength="1" d="M37 290h24M40 290v-10a9 9 0 0 1 18 0v10M46 296h6"/>'
        '<path class="d s6-ic" pathLength="1" d="M36 372l9-11 8 6 10-13M36 376h26"/>'
    )
    svg = f"""    <svg id="s6-svg" class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">
      <g id="s6-ui" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <rect id="s6-fill" x="0" y="0" width="1060" height="660" rx="18" fill="#FFFFFF" stroke="none"/>
        <rect id="s6-frame" class="d" pathLength="1" x="0" y="0" width="1060" height="660" rx="18" stroke="{INK}" stroke-width="2.5"/>
        <line id="s6-bar" class="d" pathLength="1" x1="0" y1="60" x2="1060" y2="60" stroke="{INK}" stroke-width="2"/>
        <g id="s6-dots" stroke="{INK}" stroke-width="2"><circle cx="32" cy="30" r="7"/><circle cx="58" cy="30" r="7"/><circle cx="84" cy="30" r="7"/></g>
        <line id="s6-side" class="d" pathLength="1" x1="96" y1="60" x2="96" y2="660" stroke="{INK}" stroke-width="1.5"/>
        <g stroke="{INK}" stroke-width="2">{icons}</g>
        <text id="s6-h1" class="ui" x="130" y="118">Centrale photovoltaïque</text>
        <text id="s6-h2" class="ui" x="630" y="118">Rapports</text>
        <g id="s6-field">{"".join(field)}</g>
        <text id="s6-cap" class="ui sm" x="140" y="412">Plan thermique</text>
        <circle id="s6-adot" cx="148" cy="{470 - ui * 0.34:.1f}" r="7" fill="{ACC}"/>
        <text id="s6-anom" class="ui" x="166" y="470">3 anomalies à traiter</text>
        {"".join(rows)}
        <text id="s6-plan" class="ui" x="630" y="470">Inspections à venir</text>
        <line id="s6-tline" class="d" pathLength="1" x1="640" y1="548" x2="1020" y2="548" stroke="{INK}" stroke-width="2"/>
        {"".join(f'<line class="s6-tick" x1="{x}" y1="538" x2="{x}" y2="558" stroke="{INK}" stroke-width="2"/>' for x in (660, 780, 900, 1010))}
        {"".join(f'<text class="ui sm s6-mon" x="{x}" y="612" text-anchor="middle">{m}</text>' for x, m in zip((660, 780, 900, 1010), ("Jan", "Avr", "Juil", "Oct")))}
        <circle class="s6-pm" cx="660" cy="548" r="9" fill="{INK}"/>
        <circle class="s6-pm" cx="780" cy="548" r="9" fill="{INK}"/>
        <circle id="s6-nring" cx="900" cy="548" r="12" fill="none" stroke="{ACC}" stroke-width="2"/>
        <circle id="s6-next" cx="900" cy="548" r="11" fill="#FFFFFF" stroke="{ACC}" stroke-width="4"/>
        <circle id="s6-pm2" cx="1010" cy="548" r="9" fill="#FFFFFF" stroke="#A1A1AA" stroke-width="3"/>
        {rings}
      </g>
      {mks}
    </svg>"""
    title_spec = P6["title"]
    body = box(svg, (ws, wtx, wty)) + f"""
    <div id="s6-title" class="title" style="left: {title_spec[0]}px; top: {title_spec[1]}px; font-size: {title_spec[2]}px">Suivez vos installations<br />sur notre plateforme<br />en ligne.</div>
    <div id="s6-tag" class="tag6" style="left: {P6["tag"][0]}px; top: {P6["tag"][1]}px">Bientôt disponible</div>"""
    css = f"""
    #root .ui {{ font-family: "Comfortaa", sans-serif; font-weight: 700; font-size: {ui}px; fill: #111111; stroke: none; }}
    #root .ui.sm {{ font-weight: 600; fill: #6B6B70; }}
    #root .tag6 {{ position: absolute; font-family: "Comfortaa", sans-serif; font-weight: 700; font-size: 30px; line-height: 1; padding: 10px 16px; border: 2px solid #FF5700; border-radius: 8px; color: #FF5700; background: #FFFFFF; white-space: nowrap; }}
    #root #s6-fill, #root #s6-dots, #root .s6-mod, #root .s6-mk, #root .s6-ring, #root .s6-doc2, #root .s6-bars, #root #s6-st0, #root .ui, #root #s6-adot, #root .s6-tick, #root .s6-pm, #root #s6-next, #root #s6-pm2, #root #s6-nring {{ opacity: 0; }}"""
    # le point orange du plan devient la bille du logo (raccord S6 -> S7)
    bx_, by_ = logo_screen(*BALL_L)
    tgt = ((bx_ - wtx) / ws, (by_ - wty) / ws, 12 * LOGO_S / ws)
    js = f"""
      const title = words($("#s6-title"), txt("s6-title", "{P6["text"]}"));
      // 1. la fenêtre de la plateforme se dessine autour du rapport qui arrive
      fadeIn(0.0, $("#s6-fill"), 0.4);
      draw(0.0, $("#s6-frame"), 0.8, "power2.inOut");
      draw(0.3, $("#s6-bar"), 0.45, "power2.out");
      fadeIn(0.4, $("#s6-dots"), 0.3);
      draw(0.45, $("#s6-side"), 0.45, "power2.out");
      draw(0.6, $$(".s6-ic"), 0.35, "power2.out", 0.08);
      blurIn(0.25, title, 0.15, 0.067);
      blurIn(0.95, $("#s6-tag"), 0.2);
      // 2. plan thermique, anomalies localisées
      blurIn(0.6, [$("#s6-h1"), $("#s6-h2")], 0.2, 0.12);
      fadeIn(0.7, $$(".s6-mod"), 0.3, 0.03);
      tl.fromTo($$(".s6-mk"), {{ opacity: 0, scale: 0, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)", stagger: 0.12 }}, 1.3);
      [1.7, 2.7, 3.7, 4.7].forEach((t) => {{
        tl.fromTo($$(".s6-ring"), {{ opacity: 0.85, scale: 1, transformOrigin: "50% 50%" }}, {{ opacity: 0, scale: 2.8, duration: 0.9, ease: "power2.out", immediateRender: false }}, t);
      }});
      blurIn(1.5, $("#s6-cap"), 0.18);
      fadeIn(1.75, $("#s6-adot"), 0.15);
      blurIn(1.75, $("#s6-anom"), 0.18);
      // 3. rapports et suivi
      draw(0.8, $$(".s6-row"), 0.4, "power2.out", 0.12);
      blurIn(1.15, $("#s6-new"), 0.18);
      fadeIn(1.25, $("#s6-st0"), 0.15);
      fadeIn(1.1, [...$$(".s6-doc2"), ...$$(".s6-bars")], 0.3, 0.1);
      blurIn(1.9, $("#s6-plan"), 0.18);
      draw(2.0, $("#s6-tline"), 0.6, "power2.inOut");
      fadeIn(2.25, [...$$(".s6-tick"), ...$$(".s6-mon")], 0.25, 0.05);
      tl.fromTo([...$$(".s6-pm"), $("#s6-next"), $("#s6-pm2")], {{ opacity: 0, scale: 0, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)", stagger: 0.14 }}, 2.45);
      [3.1, 4.1, 5.1].forEach((t) => {{
        tl.fromTo($("#s6-nring"), {{ opacity: 0.9, scale: 1, transformOrigin: "50% 50%" }}, {{ opacity: 0, scale: 2.4, duration: 0.9, ease: "power2.out", immediateRender: false }}, t);
      }});
      // 4. sortie : tout se floute ; un point du plan file vers le logo
      blurOut(5.8, [...title, $("#s6-tag")], 0.18, 0.02);
      tl.to([$("#s6-ui"), $("#s6-mk1"), $("#s6-mk2")], {{ opacity: 0, filter: "blur(8px)", duration: 0.22, ease: "power2.in" }}, 5.82);
      tl.to($("#s6-mk0"), {{ attr: {{ cx: {n(tgt[0])}, cy: {n(tgt[1])}, r: {n(tgt[2])} }}, duration: 0.6, ease: "power2.inOut" }}, 5.95);"""
    write_scene(
        "s6",
        "Scène 6 — Plateforme en ligne (bientôt disponible)",
        [svar("s6-title", "Scène 6 — titre", P6["text"])],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# S7 — Logo, slogan, puis site web + LinkedIn
# --------------------------------------------------------------------------
S7_DUR = 10.2  # logo (0–3,9 s), puis site web + LinkedIn tenus ~4,8 s jusqu'à la fin (plus de bouclage)
SITE_IMG = (1360, 649)  # capture du site (assets/images/site-flyscanair.jpg)


def build_s7():
    bx, by = logo_screen(*BALL_L)
    dot_r = 12 * LOGO_S
    # navigateur (repère de la scène de référence)
    BX, BY, BW = 300, 410, 760
    bar_h = P7["url"] + 24
    img_h = BW * SITE_IMG[1] / SITE_IMG[0]
    fh = bar_h + img_h
    web_svg = f"""    <svg class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">
      <defs><clipPath id="s7-imgclip"><rect id="s7-cliprect" x="{BX}" y="{n(BY + bar_h)}" width="0" height="{n(img_h)}"/></clipPath></defs>
      <rect id="s7-wfill" x="{BX}" y="{BY}" width="{BW}" height="{n(fh)}" rx="10" fill="#FFFFFF"/>
      <image href="assets/images/site-flyscanair.jpg" x="{BX}" y="{n(BY + bar_h)}" width="{BW}" height="{n(img_h)}" preserveAspectRatio="xMidYMid slice" clip-path="url(#s7-imgclip)"/>
      <g fill="none" stroke="{INK}" stroke-linecap="round" stroke-linejoin="round">
        <rect id="s7-frame" class="d" pathLength="1" x="{BX}" y="{BY}" width="{BW}" height="{n(fh)}" rx="10" stroke-width="2.5"/>
        <line id="s7-bar" class="d" pathLength="1" x1="{BX}" y1="{n(BY + bar_h)}" x2="{BX + BW}" y2="{n(BY + bar_h)}" stroke-width="2"/>
        <g id="s7-dots" stroke-width="2"><circle cx="{BX + 24}" cy="{n(BY + bar_h / 2)}" r="6"/><circle cx="{BX + 46}" cy="{n(BY + bar_h / 2)}" r="6"/><circle cx="{BX + 68}" cy="{n(BY + bar_h / 2)}" r="6"/></g>
      </g>
      <rect id="s7-pill" x="{BX + 110}" y="{BY + 8}" width="{BW - 170}" height="{bar_h - 16}" rx="{(bar_h - 16) / 2}" fill="#F3F3F4" stroke="#C9CBD1" stroke-width="1.5"/>
      <line id="s7-scan" x1="0" y1="{n(BY + bar_h)}" x2="0" y2="{n(BY + fh)}" stroke="{ACC}" stroke-width="4"/>
    </svg>
    <div id="s7-url" class="url" style="left: {BX + 136}px; top: {BY + 8}px; height: {bar_h - 16}px; font-size: {P7["url"]}px"></div>
    <div id="s7-capw" class="cap7" style="left: {BX}px; width: {BW}px; top: {n(BY + fh + 22)}px; font-size: {P7["capw"]}px">Découvrez notre site</div>"""
    sc = 160 / 448
    in_svg = f"""    <svg class="world" viewBox="0 0 {SW} {SH}" width="{SW}" height="{SH}">
      <g transform="translate(1340 {n(470 - 32 * sc)})"><g id="s7-in">
        <rect x="6" y="{n(32 * sc + 6)}" width="148" height="148" rx="10" fill="#FFFFFF"/>
        <path d="{LINKEDIN_PATH}" transform="scale({sc:.5f})" fill="#0A66C2"/>
      </g></g>
    </svg>
    <div id="s7-inname" class="cap7" style="left: 1020px; width: 800px; top: 664px; font-size: {P7["capn"]}px">Suivez-nous sur LinkedIn</div>
    <div id="s7-capi" class="cap7 grey" style="left: 1020px; width: 800px; top: {664 + round(P7["capn"] * 1.35)}px; font-size: {P7["capi"]}px; line-height: 1.25">{P7["inurl"].replace("|", "<br />")}</div>"""
    top = f"""    <div id="s7-top" data-layout-allow-overflow style="position: absolute; left: 0; top: 0; width: {W}px; height: {H}px">
    <svg class="world" viewBox="0 0 {W} {H}" width="{W}" height="{H}"{CANVAS}>
      <defs>
        <radialGradient id="s7-ball" cx="0.36" cy="0.34" r="0.7">
          <stop offset="0" stop-color="#FF9C84"/>
          <stop offset="0.35" stop-color="#E0402F"/>
          <stop offset="1" stop-color="#A51F17"/>
        </radialGradient>
        <linearGradient id="s7-wordgrad" gradientUnits="userSpaceOnUse" x1="140" y1="0" x2="1198" y2="0">
          <stop offset="0" stop-color="#E2392D"/>
          <stop offset="0.47" stop-color="#E9862A"/>
          <stop offset="0.6" stop-color="#E8842A"/>
          <stop offset="1" stop-color="#DC382D"/>
        </linearGradient>
        <clipPath id="s7-clip"><rect id="s7-wordclip" x="120" y="100" width="0" height="260"/></clipPath>
      </defs>
      <g id="s7-logo" transform="translate({n(LOGO_X)} {LOGO_Y}) scale({LOGO_S})">
        <path id="s7-coil" class="d" pathLength="1" d="{logo_coil_path()}" fill="none" stroke="#6D6C74" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
        <g clip-path="url(#s7-clip)">
          <path id="s7-word" d="{LOGO_LETTERS}" fill="url(#s7-wordgrad)"/>
        </g>
        <line id="s7-lscan" x1="0" y1="118" x2="0" y2="336" stroke="{ACC}" stroke-width="4"/>
        <circle id="s7-ballr" cx="{BALL_R[0]}" cy="{BALL_R[1]}" r="{BALL_RAD}" fill="url(#s7-ball)"/>
        <circle id="s7-balll" cx="{BALL_L[0]}" cy="{BALL_L[1]}" r="{BALL_RAD}" fill="url(#s7-ball)"/>
      </g>
      <circle id="s7-dot" cx="{n(bx)}" cy="{n(by)}" r="{n(dot_r)}" fill="{ACC}"/>
    </svg>
    <div id="s7-slogan" class="title cta1">Inspections techniques aériennes,<br />révélez l’invisible.</div>
    <div id="s7-msg" class="cta2">Faites contrôler votre installation.</div>
    </div>"""
    body = (top + "\n" + box(web_svg, P7["web"]) + "\n" + box(in_svg, P7["inb"]) + f"""
    <div id="s7-contact" class="cta3"></div>""")
    ct, cs = P7["contacts"]
    css = f"""
    #root .cta1 {{ left: 0; width: {W}px; top: {P7["slogan"][0]}px; text-align: center; font-size: {P7["slogan"][1]}px; line-height: 1.18; }}
    #root .cta2 {{ position: absolute; left: 0; width: {W}px; top: {P7["msg"][0]}px; text-align: center; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: {P7["msg"][1]}px; color: #111111; }}
    #root .cta3 {{ position: absolute; left: 0; width: {W}px; top: {ct}px; text-align: center; font-family: "Comfortaa", sans-serif; font-weight: 600; font-size: {cs}px; color: #6B6B70; display: flex; justify-content: center; align-items: center; }}
    #root .cta3 .sq {{ display: inline-block; width: 10px; height: 10px; background: #FF5700; margin: 0 24px; }}
    #root .url {{ position: absolute; display: flex; align-items: center; font-family: "Comfortaa", sans-serif; font-weight: 600; color: #111111; white-space: pre; }}
    #root .cap7 {{ position: absolute; text-align: center; font-family: "Comfortaa", sans-serif; font-weight: 700; color: #111111; white-space: nowrap; }}
    #root .cap7.grey {{ font-weight: 600; color: #6B6B70; }}
    #root #s7-lscan, #root #s7-ballr, #root #s7-balll, #root #s7-scan, #root #s7-wfill, #root #s7-dots, #root #s7-pill, #root #s7-in {{ opacity: 0; }}"""
    tsc, tty = P7["top"]
    js = f"""
      const slogan = words($("#s7-slogan"), txt("s7-slogan", "{P7["slogan_text"]}"));
      const msg = words($("#s7-msg"), txt("s7-msg", "Faites contrôler votre installation."));
      const contact = txt("s7-contact", "06 22 80 57 69|contact@flyscanair.com");
      const inName = txt("s7-inname", "");
      if (inName) $("#s7-inname").textContent = inName;
      const inUrl = txt("s7-inurl", "");
      if (inUrl) $("#s7-capi").innerHTML = inUrl.split("|").map((x) => x.replace(/[<>&]/g, "")).join("<br />");
      const cEl = $("#s7-contact");
      cEl.textContent = "";
      contact.split("|").forEach((part, i) => {{
        if (i) {{ const q = document.createElement("i"); q.className = "sq"; cEl.appendChild(q); }}
        const sp = document.createElement("span"); sp.textContent = part.trim(); cEl.appendChild(sp);
      }});
      const uEl = $("#s7-url");
      const letters = txt("s7-url", "www.flyscanair.com").split("").map((ch) => {{
        const sp = document.createElement("span"); sp.textContent = ch; uEl.appendChild(sp); return sp;
      }});
      // A. le point orange devient la bille du logo, le serpentin se trace, le scan révèle le nom
      tl.fromTo($("#s7-balll"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3, ease: "power1.inOut" }}, 0.0);
      tl.to($("#s7-dot"), {{ opacity: 0, duration: 0.3, ease: "power1.inOut" }}, 0.0);
      draw(0.15, $("#s7-coil"), 1.4, "power1.inOut");
      tl.fromTo($("#s7-lscan"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.1 }}, 0.35);
      tl.fromTo($("#s7-lscan"), {{ x: 120 }}, {{ x: 1230, duration: 1.1, ease: "power1.inOut" }}, 0.35);
      tl.fromTo($("#s7-wordclip"), {{ attr: {{ width: 0 }} }}, {{ attr: {{ width: 1110 }}, duration: 1.1, ease: "power1.inOut" }}, 0.35);
      tl.to($("#s7-lscan"), {{ opacity: 0, duration: 0.15 }}, 1.4);
      tl.fromTo($("#s7-ballr"), {{ opacity: 0, scale: 0, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.35, ease: "back.out(1.6)" }}, 1.5);
      blurIn(1.6, slogan, 0.15, 0.067);
      tl.fromTo(msg, {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2 }}, 1.9);
      tl.fromTo(msg, {{ color: "#D4D4D8" }}, {{ color: "#111111", duration: 0.25, stagger: 0.08 }}, 2.0);
      // B. le logo monte ; site web et LinkedIn apparaissent
      blurOut(4.15, msg, 0.16, 0.02); // le message reste lisible pendant que la voix le prononce
      tl.to($("#s7-top"), {{ scale: {tsc}, y: {tty}, transformOrigin: "{n(W / 2)}px 0px", duration: 0.55, ease: "power2.inOut" }}, 4.18);
      fadeIn(4.3, $("#s7-wfill"), 0.3);
      draw(4.3, $("#s7-frame"), 0.6, "power2.inOut");
      draw(4.55, $("#s7-bar"), 0.35, "power2.out");
      fadeIn(4.6, [$("#s7-dots"), $("#s7-pill")], 0.25, 0.05);
      tl.fromTo(letters, {{ opacity: 0 }}, {{ opacity: 1, duration: 0.05, stagger: 0.03 }}, 4.72);
      tl.fromTo($("#s7-scan"), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.1 }}, 4.9);
      tl.fromTo($("#s7-scan"), {{ x: {BX} }}, {{ x: {BX + BW}, duration: 0.65, ease: "power1.inOut" }}, 4.9);
      tl.fromTo($("#s7-cliprect"), {{ attr: {{ width: 0 }} }}, {{ attr: {{ width: {BW} }}, duration: 0.65, ease: "power1.inOut" }}, 4.9);
      tl.to($("#s7-scan"), {{ opacity: 0, duration: 0.15 }}, 5.55);
      blurIn(5.2, $("#s7-capw"), 0.2);
      tl.fromTo($("#s7-in"), {{ opacity: 0, scale: 0.6, transformOrigin: "50% 50%" }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.6)" }}, 4.8);
      blurIn(5.15, [$("#s7-inname"), $("#s7-capi")], 0.2, 0.1);
      blurIn(5.35, $("#s7-contact"), 0.2);
      // C. fin : le carton (site web, LinkedIn, coordonnées) reste affiché jusqu'à la dernière image
      tl.set({{}}, {{}}, {n(S7_DUR)});"""
    write_scene(
        "s7",
        "Scène 7 — Logo, slogan, site web et LinkedIn",
        [
            svar("s7-slogan", "Scène 7 — slogan", P7["slogan_text"]),
            svar("s7-msg", "Scène 7 — message", "Faites contrôler votre installation."),
            svar("s7-url", "Scène 7 — adresse du site", "www.flyscanair.com"),
            svar("s7-inname", "Scène 7 — appel LinkedIn", "Suivez-nous sur LinkedIn"),
            svar("s7-inurl", "Scène 7 — adresse de la page LinkedIn (| = retour ligne)", P7["inurl"]),
            svar("s7-contact", "Scène 7 — contact (| sépare les éléments)", "06 22 80 57 69|contact@flyscanair.com"),
        ],
        css,
        body,
        js,
    )


# --------------------------------------------------------------------------
# index.html
# --------------------------------------------------------------------------
SCENES = [("s1", 0, 7.2), ("s2", 7.2, 6.6), ("s3", 13.8, S3_DUR), ("s4", 33.0, 7.2), ("s5", 40.2, 17.4),
          ("s6", 57.6, 6.6), ("s7", 64.2, S7_DUR)]
TOTAL = 74.4

# (id, file, hit time in the film, volume): the file's measured peak lands one frame after its picture
SFX = [
    ("sfx-drone", "whoosh-short.mp3", 13.8 + 0.72, 0.5),
    ("sfx-scan", "whoosh-cinematic.mp3", 13.8 + 3.95, 0.3),
    ("sfx-zoom", "whoosh-high.mp3", 13.8 + S3_DUR - 0.05, 0.45),
    ("sfx-tick1", "key-press.mp3", 33.0 + 0.8, 0.5),
    ("sfx-tick2", "key-press.mp3", 33.0 + 1.65, 0.45),
    ("sfx-tick3", "key-press.mp3", 33.0 + 3.15, 0.5),
    ("sfx-carry", "whoosh-low.mp3", 33.0 + 6.8, 0.35),
    ("sfx-box1", "key-press.mp3", 40.2 + 1.5, 0.3),
    ("sfx-box2", "key-press.mp3", 40.2 + 5.72, 0.3),
    ("sfx-plan", "pop.mp3", 40.2 + 3.55, 0.25),
    ("sfx-page2", "whoosh-high.mp3", 40.2 + 8.2, 0.18),
    ("sfx-page3", "whoosh-high.mp3", 40.2 + 11.75, 0.18),
    ("sfx-stamp", "pop.mp3", 40.2 + 12.88, 0.45),
    ("sfx-check1", "click-soft.mp3", 40.2 + 13.72, 0.6),
    ("sfx-check2", "click-soft.mp3", 40.2 + 14.32, 0.55),
    ("sfx-check3", "click-soft.mp3", 40.2 + 14.92, 0.6),
    ("sfx-check4", "click-soft.mp3", 40.2 + 15.52, 0.55),
    ("sfx-doc", "whoosh-short.mp3", 40.2 + 16.89, 0.3),
    ("sfx-logo", "impact-bass-1.mp3", 64.2 + 1.55, 0.22),
    ("sfx-top", "whoosh-low.mp3", 64.2 + 4.43, 0.22),
    ("sfx-type", "typing.mp3", 64.2 + 4.72, 0.35),
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
    # voix off (tools/voiceover.py) : une piste par phrase, et la musique s'efface sous la voix
    vo_path = os.path.join(ROOT, "assets", "audio", "vo", "vo.json")
    vo = json.load(open(vo_path, encoding="utf-8")) if os.path.exists(vo_path) else []
    music_attr = ""
    if vo:
        duck, base = 0.28, 0.85  # musique -1,4 dB partout, -11 dB sous la voix
        pts_ = [{"t": 0, "v": base}]
        segs = []
        for v in vo:
            s0, s1 = v["start"] - 0.3, v["start"] + v["dur"] + 0.45
            if segs and s0 <= segs[-1][1] + 0.5:  # pas de remontée de la musique dans les petits silences
                segs[-1][1] = s1
            else:
                segs.append([s0, s1])
        for s0, s1 in segs:
            pts_ += [{"t": round(max(s0, 0), 3), "v": base}, {"t": round(s0 + 0.3, 3), "v": duck},
                     {"t": round(s1 - 0.45, 3), "v": duck}, {"t": round(min(s1, TOTAL), 3), "v": base}]
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
    build_s1()
    build_s2()
    build_s3()
    build_s4()
    build_s5()
    build_s6()
    build_s7()
    build_index(offsets)
