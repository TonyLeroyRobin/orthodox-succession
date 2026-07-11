/* Shared data loading + rendering helpers for the prototype dashboard.
   Reads the JSON exported by scripts/export_graph.py into build/site-data/.
   Serve the repo root over HTTP (python -m http.server) — file:// will not
   allow fetch. */

const DATA_BASE = "../build/site-data/";

/* ---- i18n (ROADMAP_ADDENDUM A3): all UI strings live in locales/*.json;
   code references keys via t(); static HTML is filled via [data-i18n]. ---- */

let LOCALE = {};

async function initLocale() {
  try {
    const resp = await fetch("locales/en.json");
    if (resp.ok) LOCALE = await resp.json();
  } catch (e) { /* fall back to keys */ }
  for (const el of document.querySelectorAll("[data-i18n]")) {
    const k = el.getAttribute("data-i18n");
    if (LOCALE[k] !== undefined) el.innerHTML = LOCALE[k];
  }
  const titleKey = document.documentElement.getAttribute("data-i18n-title");
  if (titleKey && LOCALE[titleKey]) document.title = LOCALE[titleKey];
}

function t(key, vars) {
  let s = LOCALE[key];
  if (s === undefined) return key;
  for (const [k, v] of Object.entries(vars || {})) {
    s = s.split(`{${k}}`).join(v);
  }
  return s;
}

async function loadData(names) {
  const out = {};
  await Promise.all(
    names.map(async (n) => {
      const resp = await fetch(DATA_BASE + n + ".json");
      if (!resp.ok) throw new Error(`failed to load ${n}.json (${resp.status})`);
      out[n] = await resp.json();
    })
  );
  return out;
}

function byId(list) {
  const m = new Map();
  for (const r of list) m.set(r.id, r);
  return m;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/* ---- dates ---------------------------------------------------------- */

function dateYearNum(d) {
  if (!d || !d.value) return null;
  const m = String(d.value).match(/^(-?)(\d{4})/);
  if (!m) return null;
  return (m[1] ? -1 : 1) * parseInt(m[2], 10);
}

function fmtDate(d) {
  if (!d || !d.value) return "—";
  let v = d.value.replace(/^0+(\d)/, "$1");
  let s;
  switch (d.precision) {
    case "circa": s = t("fmt.circa") + v.split("-")[0]; break;
    case "decade": s = v.split("-")[0] + "s"; break;
    case "century": s = (Math.floor(parseInt(v, 10) / 100) + 1) + t("fmt.centuryApprox"); break;
    case "disputed": s = v + t("fmt.disputed"); break;
    case "year": s = v.split("-")[0]; break;
    default: s = v;
  }
  if (d.calendar === "julian") s += t("fmt.julian");
  if (d.calendar === "anno-mundi") s += t("fmt.annoMundi");
  return s;
}

function fmtRange(from, to, openLabel) {
  const a = fmtDate(from);
  const b = to ? fmtDate(to) : (openLabel || t("fmt.endUnrecorded"));
  return `${a} → ${b}`;
}

/* ---- record display -------------------------------------------------- */

function statusBadge(status) {
  const label = LOCALE[`status.${status}`] || status;
  return `<span class="badge ${esc(status)}">${esc(label)}</span>`;
}

function personName(p) {
  if (!p) return t("person.unknown");
  const n = p.names || {};
  let s = n.monastic || p.id;
  if (n.family) s += ` (${n.family})`;
  return s;
}

function personLink(p) {
  if (!p) return t("person.unknown");
  return `<a href="person.html?id=${encodeURIComponent(p.id)}">${esc(personName(p))}</a>`;
}

function citationsHtml(cits, sourcesMap) {
  if (!cits || !cits.length) return `<div class="citation">${t("citation.none")}</div>`;
  return cits
    .map((c) => {
      const src = sourcesMap.get(c.ref);
      const title = src ? src.title : c.ref;
      const link = src && src.url ? ` <a href="${esc(src.url)}">${t("citation.link")}</a>` : "";
      const arch = c.archived_url || (src && src.archived_url);
      const archLink = arch ? ` <a href="${esc(arch)}">${t("citation.archived")}</a>` : "";
      const loc = c.locator ? `, ${esc(c.locator)}` : "";
      return `<div class="citation"><span class="badge grade">${esc(c.reliability)}</span> ` +
             `${esc(title)}${loc}${link}${archLink}` +
             (c.note ? ` <span class="note">— ${esc(c.note)}</span>` : "") +
             `</div>`;
    })
    .join("");
}
