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

/* ---- corroboration tier (ROADMAP C4, maintainer-approved 2026-07-15):
   >=2 citations from DISTINCT sources, neither tradition- nor database-grade.
   Computed client-side from the record's own citations; purely visual. ---- */

function isCorroborated(record) {
  const cits = (record && record.sources) || [];
  const refs = new Set(
    cits
      .filter((c) => c.reliability && !["tradition", "database"].includes(c.reliability))
      .map((c) => c.ref)
  );
  return refs.size >= 2;
}

function corroborationBadge(record) {
  return isCorroborated(record)
    ? ` <span class="badge corroborated" title="${esc(t("badge.corroborated.tip"))}">${t("badge.corroborated")}</span>`
    : "";
}

/* ---- liturgical calendar helpers (ROADMAP C2) ------------------------- */

/* Julian -> Gregorian civil offset is +13 days for 1900-03-14..2100-02-28. */
function julianFeastCivilDate(monthDay, year) {
  const [m, d] = monthDay.split("-").map(Number);
  const dt = new Date(Date.UTC(year, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + 13);
  return dt;
}

function mmdd(dt) {
  return String(dt.getUTCMonth() + 1).padStart(2, "0") + "-" +
         String(dt.getUTCDate()).padStart(2, "0");
}

/* All commemorations falling on the given civil date: a gregorian-recorded
   feast falls on its own month-day; a julian-recorded feast falls 13 days
   later on the civil calendar. */
function commemorationsOn(civilDate, people) {
  const todayMd = mmdd(civilDate);
  const year = civilDate.getUTCFullYear();
  const out = [];
  for (const p of people) {
    const ven = p.veneration;
    if (!ven || ven.status !== "saint") continue;
    for (const f of ven.feast_days || []) {
      if (!f.month_day) continue;
      const civil = f.calendar === "julian"
        ? mmdd(julianFeastCivilDate(f.month_day, year))
        : f.month_day;
      if (civil === todayMd) out.push({ person: p, feast: f });
    }
  }
  return out;
}

/* ---- schema.org JSON-LD (ROADMAP C3) --------------------------------- */

function jsonLdForPerson(p, myTenures, seesMap) {
  const n = p.names || {};
  const alternates = [
    ...(n.variants || []),
    ...((n.native || []).map((x) => x.value)),
  ];
  const sameAs = [];
  const ids = p.identifiers || {};
  if (ids.wikidata) sameAs.push("https://www.wikidata.org/wiki/" + ids.wikidata);
  if (ids.viaf) sameAs.push("https://viaf.org/viaf/" + ids.viaf);
  const born = p.born && p.born.date ? String(dateYearNum(p.born.date)) : undefined;
  const died = p.died && p.died.date ? String(dateYearNum(p.died.date)) : undefined;
  const roles = myTenures.map((tn) => {
    const see = seesMap.get(tn.see);
    return {
      "@type": "Role",
      "roleName": "Bishop",
      "location": see ? see.name : tn.see,
      "startDate": tn.from ? String(dateYearNum(tn.from)) : undefined,
      "endDate": tn.to ? String(dateYearNum(tn.to)) : undefined,
    };
  });
  const ld = {
    "@context": "https://schema.org",
    "@type": "Person",
    "name": personName(p),
    "identifier": p.id,
  };
  if (alternates.length) ld.alternateName = alternates;
  if (born) ld.birthDate = born;
  if (died) ld.deathDate = died;
  if (sameAs.length) ld.sameAs = sameAs;
  if (roles.length) ld.hasOccupation = roles;
  return ld;
}

function injectJsonLd(obj) {
  const s = document.createElement("script");
  s.type = "application/ld+json";
  s.textContent = JSON.stringify(obj, null, 1);
  document.head.appendChild(s);
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
