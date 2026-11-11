#!/usr/bin/env node
// Prépare la page LinkedIn de la scène 7 à partir de la capture d'écran fournie (non versionnée : elle contient des
// données personnelles) -> assets/images/linkedin-flyscanair.jpg
//   - garde la vraie page : barre LinkedIn (logo, recherche, menus), bannière, carte de la page entreprise, onglets ;
//   - retire les pastilles de notification (point rouge d'Accueil, « 6 » de Réseau, « 12 » de Notifications) :
//     les trois icônes concernées sont redessinées sans pastille (icônes au trait Phosphor « regular », MIT) ;
//   - masque la ligne « … et 5 autres relations suivent cette page » et la photo de la relation ;
//   - recadre sous la barre d'adresse du navigateur, jusqu'aux onglets de la page.
//
//     node tools/linkedin_image.cjs chemin/vers/capture-linkedin.png
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const ROOT = path.dirname(__dirname);
const src = path.resolve(process.argv[2] || "");
if (!fs.existsSync(src)) {
  console.error("usage : node tools/linkedin_image.cjs capture-linkedin.png");
  process.exit(1);
}
const ICONS = { // Phosphor Icons 2.1.1, graisse regular, repère 256 x 256
  house: "M219.31,108.68l-80-80a16,16,0,0,0-22.62,0l-80,80A15.87,15.87,0,0,0,32,120v96a8,8,0,0,0,8,8h64a8,8,0,0,0,8-8V160h32v56a8,8,0,0,0,8,8h64a8,8,0,0,0,8-8V120A15.87,15.87,0,0,0,219.31,108.68ZM208,208H160V152a8,8,0,0,0-8-8H104a8,8,0,0,0-8,8v56H48V120l80-80,80,80Z",
  users: "M117.25,157.92a60,60,0,1,0-66.5,0A95.83,95.83,0,0,0,3.53,195.63a8,8,0,1,0,13.4,8.74,80,80,0,0,1,134.14,0,8,8,0,0,0,13.4-8.74A95.83,95.83,0,0,0,117.25,157.92ZM40,108a44,44,0,1,1,44,44A44.05,44.05,0,0,1,40,108Zm210.14,98.7a8,8,0,0,1-11.07-2.33A79.83,79.83,0,0,0,172,168a8,8,0,0,1,0-16,44,44,0,1,0-16.34-84.87,8,8,0,1,1-5.94-14.85,60,60,0,0,1,55.53,105.64,95.83,95.830,0,0,1,47.22,37.71A8,8,0,0,1,250.14,206.7Z",
  bell: "M221.8,175.94C216.25,166.38,208,139.33,208,104a80,80,0,1,0-160,0c0,35.34-8.26,62.38-13.81,71.94A16,16,0,0,0,48,200H88.81a40,40,0,0,0,78.38,0H208a16,16,0,0,0,13.8-24.06ZM128,216a24,24,0,0,1-22.62-16h45.24A24,24,0,0,1,128,216ZM48,184c7.7-13.24,16-43.92,16-80a64,64,0,1,1,128,0c0,36.05,8.28,66.73,16,80Z",
};
// icônes de la barre : centres tous les 120 px (Accueil, Réseau, Emplois, Messagerie, Notifications)
const NAV = [["house", 670.5], ["users", 790.5], ["bell", 1150.5]];
const NAV_Y = 31.5, SIZE = 30;
const CROP = { x: 0, y: 6, width: 1220, height: 874 };

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1220, height: 1255 }, deviceScaleFactor: 1 });
  const img = "data:image/png;base64," + fs.readFileSync(src).toString("base64");
  const cover = (x, y, w, h) => `<div style="position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${h}px;background:#fff"></div>`;
  const icon = ([name, cx]) =>
    `<svg style="position:absolute;left:${cx - SIZE / 2}px;top:${NAV_Y - SIZE / 2}px" width="${SIZE}" height="${SIZE}" viewBox="0 0 256 256"><path d="${ICONS[name]}" fill="#474747" stroke="#474747" stroke-width="5" stroke-linejoin="round"/></svg>`;
  await p.setContent(`<!doctype html><body style="margin:0"><div style="position:relative;width:1220px;height:1255px">
    <img src="${img}" style="position:absolute;left:0;top:0;width:1220px;height:1255px">
    ${NAV.map(([, cx]) => cover(cx - 22, 6, 62, 44)).join("")}
    ${NAV.map(icon).join("")}
    ${cover(40, 645, 580, 57)}
  </div></body>`);
  await p.waitForTimeout(100);
  const out = path.join(ROOT, "assets", "images", "linkedin-flyscanair.jpg");
  await p.screenshot({ path: out, type: "jpeg", quality: 92, clip: CROP });
  await b.close();
  console.log("wrote", path.relative(ROOT, out), `${CROP.width} x ${CROP.height}`);
})();
